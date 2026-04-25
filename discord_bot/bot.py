import re
import asyncio
import discord
from discord.ext import commands, tasks
from formatters import format_job_summary, format_thread_details, get_thread_title
from discord_bot.handlers import ensure_job_channel, post_job_to_channels, create_job_thread, post_thread_details
from upwork.scraper import UpworkScraper
from config import save_config
from database import JobDatabase
from auth import AuthManager
from utils.logger import logger

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

scraper = UpworkScraper()
config_data = {}
job_db = JobDatabase()
auth_manager: AuthManager = None

def setup_bot(cfg):
    """Provides configuration to the bot instance."""
    global config_data
    config_data = cfg
    return bot

@bot.event
async def on_ready():
    logger.info("="*40)
    logger.info("      UPWORK BOT - DYNAMIC TRACKER V2.0")
    logger.info("="*40)
    logger.info(f"Logged in as {bot.user}")
    db_keywords = [e['keyword'] for e in job_db.get_all_tracking()]
    logger.info(f"Tracking keywords (from DB): {db_keywords}")

    # Step 1: Only refresh tokens if they are actually expired
    global auth_manager
    auth_manager = AuthManager(scraper)
    if auth_manager.should_refresh():
        logger.info("[AUTH] Tokens expired or first run — refreshing (~20s)...")
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, auth_manager.refresh)
    else:
        logger.info("[AUTH] Tokens still valid — skipping refresh.")
    auth_manager.start_background_refresh()

    # Step 2: Migrate any keywords still in config.json into the DB
    config_keywords = config_data.get('tracked_keywords', [])
    if config_keywords:
        logger.info(f"[MIGRATE] Moving {len(config_keywords)} keyword(s) from config.json -> DB...")
        for kw in config_keywords:
            channel_name = re.sub(r'[^a-z0-9]+', '-', kw).strip('-')
            for guild in bot.guilds:
                channel = await ensure_job_channel(guild, channel_name, create=False)
                ch_id = channel.id if channel else 0
                job_db.add_tracking(kw, ch_id, kw)
                break
        config_data['tracked_keywords'] = []
        save_config(config_data)
        logger.info("[MIGRATE] Migration complete. config.json keywords cleared.")

    # Step 2b: Repair any NULL/0 channel_ids from previous bad migrations
    all_entries = job_db.get_all_tracking()
    needs_repair = [e for e in all_entries if not e.get('channel_id')]
    if needs_repair:
        logger.info(f"[REPAIR] Fixing NULL channel_ids for {len(needs_repair)} keyword(s)...")
        for entry in needs_repair:
            kw = entry['keyword']
            channel_name = re.sub(r'[^a-z0-9]+', '-', kw).strip('-')
            for guild in bot.guilds:
                channel = await ensure_job_channel(guild, channel_name, create=True)
                if channel:
                    job_db.add_tracking(kw, channel.id, kw)
                    logger.info(f"  [REPAIR] '{kw}' -> #{channel.name} (id: {channel.id})")
                break
        logger.info("[REPAIR] Channel ID repair complete.")

    # Step 3: Startup — post all recent jobs for each tracked keyword in DB
    try:
        tracked_entries = job_db.get_all_tracking()
        if tracked_entries:
            logger.info(f"Fetching latest jobs for {len(tracked_entries)} keyword(s)...")
            for entry in tracked_entries:
                kw = entry['keyword']
                ch_id = entry['channel_id']
                count = job_db.get_job_count(kw)
                logger.info(f"  Fetching for '{kw}' (Present in DB: {count})...")
                all_jobs = await asyncio.to_thread(scraper.fetch_jobs_summary, offset=0, count=50, keyword=kw)

                # FIX 1: Safe sort — handles jobTile=None or job=None
                all_jobs = sorted(
                    all_jobs,
                    key=lambda x: ((x.get('jobTile') or {}).get('job') or {}).get('publishTime') or
                                  ((x.get('jobTile') or {}).get('job') or {}).get('createTime') or "",
                    reverse=True
                )
                
                # Take only the 20 latest from the 50 fetched
                jobs = all_jobs[:20]

                posted_count = 0
                for job in jobs:
                    if not job:
                        continue
                    job_id = job.get('id')
                    description = job.get('description')
                    if not job_id:
                        continue
                        
                    status = job_db.get_job_status(job, kw)

                    if status == 'SEEN':
                        continue

                    # Resolve channel
                    channel = bot.get_channel(ch_id) if ch_id else None
                    if not channel:
                        channel_name = re.sub(r'[^a-z0-9]+', '-', kw).strip('-')
                        for guild in bot.guilds:
                            channel = await ensure_job_channel(guild, channel_name, create=True)
                            break

                    if not channel:
                        continue

                    if status == 'UPDATE':
                        logger.info(f"  [{kw}] 🔄 Job Updated -> {job.get('title')}")
                        job_db.mark_job_updated(job, kw)
                        update_msg = format_job_summary(job, is_update=True)
                        await post_job_to_channels(channel, update_msg)
                    else: # NEW
                        summary_msg = format_job_summary(job)
                        await post_job_to_channels(channel, summary_msg)
                        _save_to_db(job, kw)
                    
                    await asyncio.sleep(1.2)
                    posted_count += 1

                logger.info(f"  '{kw}': Posted {posted_count} job(s) on startup.")
        else:
            logger.info("No keywords tracked yet. Use !track <keyword> to start.")
    except Exception as e:
        logger.error(f"Failed startup fetch: {e}")

    if not job_scraper_loop.is_running():
        job_scraper_loop.start()


@bot.command()
async def track(ctx, *, keyword: str):
    """Tracks a new keyword, saves to DB, and creates a channel for it."""
    keyword_lower = keyword.strip().lower()
    if not keyword_lower:
        await ctx.send("Please provide a valid keyword to track.")
        return

    # Check DB — not config.json
    existing = [e['keyword'] for e in job_db.get_all_tracking()]
    if keyword_lower in existing:
        await ctx.send(f"Already tracking **{keyword_lower}**.")
        return

    channel_name = re.sub(r'[^a-z0-9]+', '-', keyword_lower).strip('-')

    guild = ctx.guild
    if guild:
        channel = await ensure_job_channel(guild, channel_name, create=True)
        if channel:
            # Save to DB with the real channel ID
            job_db.add_tracking(keyword_lower, channel.id, keyword_lower)
            await ctx.send(f"Now tracking **{keyword_lower}**! Fetching latest jobs for {channel.mention}...")
            try:
                all_jobs = await asyncio.to_thread(scraper.fetch_jobs_summary, offset=0, count=50, keyword=keyword_lower)

                # FIX 2: Safe sort — handles jobTile=None or job=None
                all_jobs = sorted(
                    all_jobs,
                    key=lambda x: ((x.get('jobTile') or {}).get('job') or {}).get('publishTime') or
                                  ((x.get('jobTile') or {}).get('job') or {}).get('createTime') or "",
                    reverse=True
                )
                
                # Take only the 20 latest from the 50 fetched
                jobs = all_jobs[:20]

                posted_count = 0
                for job in jobs:
                    if not job:
                        continue
                    job_id = job.get('id')
                    description = job.get('description')
                    if not job_id:
                        continue
                        
                    status = job_db.get_job_status(job, keyword_lower)

                    if status == 'SEEN':
                        continue

                    if status == 'UPDATE':
                        logger.info(f"  [{keyword_lower}] 🔄 Job Updated -> {job.get('title')}")
                        job_db.mark_job_updated(job, keyword_lower)
                        update_msg = format_job_summary(job, is_update=True)
                        await post_job_to_channels(channel, update_msg)
                    else: # NEW
                        summary_msg = format_job_summary(job)
                        await post_job_to_channels(channel, summary_msg)
                        _save_to_db(job, keyword_lower)

                    await asyncio.sleep(1.2)
                    posted_count += 1

                if posted_count > 0:
                    await ctx.send(f"✅ Posted **{posted_count}** recent jobs for **{keyword_lower}**. Live tracking is now active!")
                else:
                    await ctx.send(f"✅ Tracking **{keyword_lower}**. No new jobs right now — watching for new ones!")

            except Exception as e:
                print(f"Error during !track fetch: {e}")
                await ctx.send(f"⚠️ Error fetching jobs for **{keyword_lower}**: {e}")
        else:
            await ctx.send(f"Could not create channel #{channel_name}.")
    else:
        await ctx.send("Run this command inside a server.")

@bot.command()
async def list(ctx):
    """Lists all keywords currently being tracked (from DB)."""
    entries = job_db.get_all_tracking()
    if not entries:
        await ctx.send("No keywords are being tracked. Use `!track <keyword>` to add one.")
    else:
        lines = []
        for e in entries:
            ch = bot.get_channel(e['channel_id'])
            count = job_db.get_job_count(e['keyword'])
            ch_str = ch.mention if ch else f"(channel id: {e['channel_id']})"
            lines.append(f"- **{e['keyword']}** -> {ch_str} (Total: {count})")
        await ctx.send(f"**Currently tracking:**\n" + "\n".join(lines))

@bot.command()
async def untrack(ctx, *, keyword: str):
    """Stops tracking a keyword and removes it from the DB."""
    keyword_lower = keyword.strip().lower()
    existing = [e['keyword'] for e in job_db.get_all_tracking()]

    if keyword_lower not in existing:
        await ctx.send(f"Not currently tracking **{keyword_lower}**.")
        return

    job_db.remove_tracking(keyword_lower)
    await ctx.send(f"✅ Stopped tracking **{keyword_lower}**. No more alerts for this keyword.")

@bot.command()
async def delete(ctx, *, keyword: str):
    """Stops tracking, deletes the channel, and wipes all history for a keyword."""
    # Remove quotes if the user wrapped the keyword in them
    keyword_clean = keyword.strip().strip('"').strip("'").lower()
    
    logger.info(f"[BOT] Received !delete command for keyword: '{keyword_clean}'")
    
    # Find the entry to get the channel ID before we delete it
    tracked = job_db.get_all_tracking()
    entry = next((e for e in tracked if e['keyword'] == keyword_clean), None)

    channel = None
    ch_id = entry['channel_id'] if entry else None

    # 1. Try to find the channel
    if ch_id:
        # Best way: Use the stored ID
        channel = bot.get_channel(ch_id)
        if not channel:
            try:
                channel = await bot.fetch_channel(ch_id)
            except Exception:
                channel = None
    
    # 2. Fallback: Search by name if ID failed or not tracked
    if not channel:
        channel_name_target = re.sub(r'[^a-z0-9]+', '-', keyword_clean).strip('-')
        logger.info(f"[BOT] Falling back to name search for channel: #{channel_name_target}")
        for guild in bot.guilds:
            channel = discord.utils.get(guild.channels, name=channel_name_target)
            if channel:
                break

    if not entry and not channel:
        logger.warning(f"[BOT] !delete failed: '{keyword_clean}' not in DB and no matching channel found.")
        await ctx.send(f"Could not find any tracking info or channel for **{keyword_clean}**.")
        return

    # 3. Delete the Discord channel if found
    if channel:
        try:
            channel_name = channel.name
            await channel.delete(reason=f"Keyword '{keyword_clean}' deleted by {ctx.author}")
            logger.info(f"[BOT] Successfully deleted channel #{channel_name} for '{keyword_clean}'")
        except Exception as e:
            logger.error(f"[BOT] Failed to delete channel {channel.id}: {e}")
            await ctx.send(f"⚠️ Could not delete the Discord channel: {e}")
    else:
        logger.warning(f"[BOT] No channel found on Discord to delete.")

    # 4. Wipe all data from Database
    job_db.delete_keyword_data(keyword_clean)
    logger.info(f"[BOT] Wiped all database records for keyword '{keyword_clean}'")
    
    await ctx.send(f"🗑️ **{keyword_clean}** has been completely removed (Tracking stopped, Channel deleted, History wiped).")

@bot.command()
async def test(ctx):
    """Fetches the latest job and posts it here immediately."""
    await ctx.send("Fetching latest job from Upwork...")
    try:
        jobs = await asyncio.to_thread(scraper.fetch_jobs_summary, offset=0, count=1)
        if jobs:
            job = jobs[0]
            summary_msg = format_job_summary(job)
            await ctx.send(summary_msg)
        else:
            await ctx.send("No jobs found.")
    except Exception as e:
        await ctx.send(f"Error fetching jobs: {e}")

@bot.command()
async def stats(ctx):
    """Shows how many jobs have been tracked per keyword."""
    data = job_db.get_stats()
    total = data['total_unique_jobs']
    by_kw = data['by_keyword']
    if not by_kw:
        await ctx.send("No jobs tracked yet. Use `!track <keyword>` to start.")
        return
    lines = [f"- **{kw}**: {cnt} job(s)" for kw, cnt in by_kw.items()]
    msg = f"**Bot Statistics**\nUnique jobs tracked: **{total}**\n\n" + "\n".join(lines)
    await ctx.send(msg)

@tasks.loop(seconds=60)
async def job_scraper_loop():
    # Read from DB — not config.json
    tracked_entries = job_db.get_all_tracking()
    if not tracked_entries:
        return

    logger.info(f"Loop: Checking {len(tracked_entries)} keyword(s)...")

    # Ensure cookies haven't been manually deleted by the user
    if auth_manager and auth_manager.is_file_missing_or_empty():
        logger.warning("[BOT] saved_cookies.json was manually removed! Pausing loop to fetch new cookies...")
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, auth_manager.refresh)

    for entry in tracked_entries:
        kw = entry['keyword']
        ch_id = entry['channel_id']
        count = job_db.get_job_count(kw)
        logger.info(f"  Fetching for '{kw}' (Present in DB: {count})...")

        try:
            all_jobs = await asyncio.to_thread(scraper.fetch_jobs_summary, offset=0, count=50, keyword=kw)
        except Exception as e:
            error_str = str(e)
            if '403' in error_str or '401' in error_str:
                if auth_manager and not auth_manager.is_refreshing():
                    logger.warning(f'[BOT] Auth error for "{kw}" — triggering token refresh...')
                    loop = asyncio.get_event_loop()
                    asyncio.ensure_future(loop.run_in_executor(None, auth_manager.refresh))
                elif auth_manager and auth_manager.is_refreshing():
                    logger.warning(f'[BOT] Auth error for "{kw}" — waiting for background token refresh...')
                else:
                    logger.warning(f'[BOT] Auth error for "{kw}" — refreshing tokens...')
            else:
                logger.error(f'[BOT] Fetch error for "{kw}": {e}')
            await asyncio.sleep(2)
            continue

        matched_count = 0

        # FIX 3: Safe sort — handles jobTile=None or job=None
        all_jobs = sorted(
            all_jobs,
            key=lambda x: ((x.get('jobTile') or {}).get('job') or {}).get('publishTime') or
                          ((x.get('jobTile') or {}).get('job') or {}).get('createTime') or "",
            reverse=True
        )
        
        # Take only the 20 latest
        jobs = all_jobs[:20]

        for job in jobs:
            if not job:
                continue
            job_id = job.get('id')
            description = job.get('description')
            if not job_id:
                continue

            status = job_db.get_job_status(job, kw)

            if status == 'SEEN':
                continue

            # Resolve channel
            channel = bot.get_channel(ch_id) if ch_id else None
            if not channel:
                channel_name = re.sub(r'[^a-z0-9]+', '-', kw).strip('-')
                for guild in bot.guilds:
                    channel = await ensure_job_channel(guild, channel_name, create=True)
                    if channel:
                        break

            if not channel:
                continue

            # --- Post the job and get the message object for threading ---
            try:
                if status == 'UPDATE':
                    logger.info(f"  [{kw}] 🔄 Job Updated -> {job.get('title')}")
                    job_db.mark_job_updated(job, kw)
                    msg_content = format_job_summary(job, is_update=True)
                else:  # NEW
                    logger.info(f"  [{kw}] ✅ New Job -> {job.get('title')}")
                    msg_content = format_job_summary(job)

                # Single post — capture the message for thread creation
                message = await post_job_to_channels(channel, msg_content)

                # Save to DB (only once)
                _save_to_db(job, kw)

                # Create thread with job details
                if message:
                    thread_title = get_thread_title(job.get('title', 'New Job'))
                    archive_dur = config_data.get('thread_auto_archive', 60)
                    thread = await create_job_thread(message, thread_title, archive_dur)
                    if thread:
                        details_msg = format_thread_details(job, None)
                        await post_thread_details(thread, details_msg)

            except Exception as e:
                logger.error(f"  [{kw}] Failed to post/thread job {job_id}: {e}")
                continue

            await asyncio.sleep(1.2)
            matched_count += 1

        if matched_count > 0:
            logger.info(f"  '{kw}': Posted {matched_count} new job(s).")

        # 2-second safety delay between keywords to avoid API hammering
        await asyncio.sleep(2)


def _save_to_db(job: dict, keyword: str):
    """Helper: extract budget + URL from a raw job dict and persist to SQLite."""
    # FIX 4: Safe extraction — handles jobTile=None or job=None
    job_inner = (job.get('jobTile') or {}).get('job') or {}

    ciphertext = job_inner.get('ciphertext', '')
    job_url = f"https://www.upwork.com/jobs/{ciphertext}" if ciphertext else ''

    job_type = job_inner.get('jobType', '')
    if job_type == 'HOURLY':
        lo = job_inner.get('hourlyBudgetMin')
        hi = job_inner.get('hourlyBudgetMax')
        if lo and hi:
            budget = f"${lo}-${hi}/hr"
        elif lo:
            budget = f"From ${lo}/hr"
        elif hi:
            budget = f"Up to ${hi}/hr"
        else:
            budget = 'N/A'
    elif job_type == 'FIXED':
        amt = (job_inner.get('fixedPriceAmount') or {}).get('amount')
        budget = f"${amt}" if amt else 'N/A'
    else:
        budget = 'N/A'

    job_db.save_job(job, keyword=keyword, budget=budget, job_url=job_url)