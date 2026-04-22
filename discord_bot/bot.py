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
    print("="*40)
    print("      UPWORK BOT - DYNAMIC TRACKER V2.0")
    print("="*40)
    print(f"Logged in as {bot.user}")
    print(f"Tracking keywords: {config_data.get('tracked_keywords', [])}")

    # Step 1: Only refresh tokens if they are actually expired
    global auth_manager
    auth_manager = AuthManager(scraper)
    if auth_manager.should_refresh():
        print("[AUTH] Tokens expired or first run — refreshing (~20s)...")
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, auth_manager.refresh)
    else:
        print("[AUTH] Tokens still valid — skipping refresh.")
    auth_manager.start_background_refresh()

    # Step 2: Startup — post all recent jobs for each keyword, mark them seen
    try:
        tracked = config_data.get('tracked_keywords', [])
        if tracked:
            print(f"Fetching latest jobs for {len(tracked)} keyword(s)...")
            for kw in tracked:
                print(f"  Fetching for '{kw}'...")
                jobs = scraper.fetch_jobs_summary(count=20, keyword=kw)

                # Sort newest-first
                jobs = sorted(
                    jobs,
                    key=lambda x: x.get('jobTile', {}).get('job', {}).get('publishTime') or
                                  x.get('jobTile', {}).get('job', {}).get('createTime') or 0,
                    reverse=True
                )

                channel_name = re.sub(r'[^a-z0-9]+', '-', kw).strip('-')
                posted_count = 0

                for job in jobs:
                    job_id = job.get('id')
                    if not job_id or job_db.is_seen(job_id, kw):
                        continue

                    # Post all unseen jobs
                    for guild in bot.guilds:
                        channel = await ensure_job_channel(guild, channel_name, create=True)
                        if channel:
                            summary_msg = format_job_summary(job)
                            await post_job_to_channels(channel, summary_msg)

                    _save_to_db(job, kw)
                    posted_count += 1

                print(f"  '{kw}': Posted {posted_count} job(s) on startup.")
        else:
            print("No keywords tracked yet. Use !track <keyword> to start.")
    except Exception as e:
        print(f"Failed startup fetch: {e}")

    if not job_scraper_loop.is_running():
        job_scraper_loop.start()


@bot.command()
async def track(ctx, *, keyword: str):
    """Tracks a new keyword, saves it, and creates a channel for it."""
    keyword_lower = keyword.strip().lower()
    if not keyword_lower:
        await ctx.send("Please provide a valid keyword to track.")
        return

    tracked = config_data.get('tracked_keywords', [])
    if keyword_lower in tracked:
        await ctx.send(f"Already tracking '{keyword_lower}'.")
        return

    # Process into valid Discord channel name
    channel_name = re.sub(r'[^a-z0-9]+', '-', keyword_lower).strip('-')
    
    # Save it persistently
    tracked.append(keyword_lower)
    config_data['tracked_keywords'] = tracked
    save_config(config_data)

    guild = ctx.guild
    if guild:
        channel = await ensure_job_channel(guild, channel_name, create=True)
        if channel:
            await ctx.send(f"Now tracking **{keyword_lower}**! Fetching latest jobs for {channel.mention}...")
            try:
                jobs = scraper.fetch_jobs_summary(count=20, keyword=keyword_lower)

                # Sort newest-first
                jobs = sorted(
                    jobs,
                    key=lambda x: x.get('jobTile', {}).get('job', {}).get('publishTime') or
                                  x.get('jobTile', {}).get('job', {}).get('createTime') or 0,
                    reverse=True
                )

                posted_count = 0
                for job in jobs:
                    job_id = job.get('id')
                    if not job_id or job_db.is_seen(job_id, keyword_lower):
                        continue

                    summary_msg = format_job_summary(job)
                    await post_job_to_channels(channel, summary_msg)
                    _save_to_db(job, keyword_lower)
                    posted_count += 1

                if posted_count > 0:
                    await ctx.send(f"✅ Posted **{posted_count}** recent jobs for **{keyword_lower}**. Live tracking is now active!")
                else:
                    await ctx.send(f"✅ Tracking **{keyword_lower}**. No new jobs right now — watching for new ones!")

            except Exception as e:
                print(f"Error during !track fetch: {e}")
                await ctx.send(f"⚠️ Error fetching jobs for **{keyword_lower}**: {e}")
        else:
            await ctx.send(f"Added **{keyword_lower}** to tracking list, but failed to create channel #{channel_name}.")
    else:
        await ctx.send(f"Now tracking **{keyword_lower}**! Run in a server next time to auto-create channels.")

@bot.command()
async def list(ctx):
    """Lists all keywords currently being tracked."""
    tracked = config_data.get('tracked_keywords', [])
    if not tracked:
        await ctx.send("No keywords are currently being tracked. Use `!track <keyword>` to add one.")
    else:
        keywords_str = "\n".join([f"- {kw}" for kw in tracked])
        await ctx.send(f"**Currently tracking:**\n{keywords_str}")

@bot.command()
async def untrack(ctx, *, keyword: str):
    """Stops tracking a specific keyword."""
    keyword_lower = keyword.strip().lower()
    tracked = config_data.get('tracked_keywords', [])
    
    if keyword_lower not in tracked:
        await ctx.send(f"Not currently tracking '{keyword_lower}'.")
        return

    tracked.remove(keyword_lower)
    config_data['tracked_keywords'] = tracked
    save_config(config_data)
    await ctx.send(f"Stopped tracking **{keyword_lower}**. I will no longer post new matching jobs.")

@bot.command()
async def test(ctx):
    """Fetches the latest job and posts it here immediately."""
    await ctx.send("Fetching latest job from Upwork...")
    try:
        jobs = scraper.fetch_jobs_summary(count=1)
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
    tracked_keywords = config_data.get('tracked_keywords', [])
    if not tracked_keywords:
        return

    print(f"Loop: Checking activity for {len(tracked_keywords)} keyword(s)...")

    for kw in tracked_keywords:
        try:
            # Niche-specific search for this keyword
            jobs = scraper.fetch_jobs_summary(count=20, keyword=kw)
        except Exception as e:
            error_str = str(e)
            if '403' in error_str or '401' in error_str:
                print(f'[BOT] Auth error during "{kw}" search — triggering emergency token refresh...')
                if auth_manager:
                    loop = asyncio.get_event_loop()
                    asyncio.ensure_future(loop.run_in_executor(None, auth_manager.refresh))
            else:
                print(f'[BOT] Fetch error for "{kw}": {e}')
            continue

        matched_count = 0
        # Sort newest-first by publish/create time so new jobs are processed in order
        jobs = sorted(
            jobs,
            key=lambda x: x.get('jobTile', {}).get('job', {}).get('publishTime') or
                          x.get('jobTile', {}).get('job', {}).get('createTime') or 0,
            reverse=True
        )
        for job in jobs:
            job_id = job.get('id')
            if not job_id or job_db.is_seen(job_id, kw):
                continue

            print(f"  [{kw}] New Job -> {job.get('title')}")
            channel_name = re.sub(r'[^a-z0-9]+', '-', kw).strip('-')

            for guild in bot.guilds:
                channel = await ensure_job_channel(guild, channel_name, create=True)
                if not channel:
                    continue

                summary_msg = format_job_summary(job)
                try:
                    message = await post_job_to_channels(channel, summary_msg)
                except Exception as e:
                    print(f"  Post failed: {e}")
                    continue

                try:
                    thread_title = get_thread_title(job.get('title', 'New Job'))
                    archive_dur = config_data.get('thread_auto_archive', 60)
                    thread = await create_job_thread(message, thread_title, archive_dur)
                    details_msg = format_thread_details(job, None)
                    await post_thread_details(thread, details_msg)
                except Exception as e:
                    print(f"  Thread failed: {e}")

            _save_to_db(job, kw)
            matched_count += 1
        
        if matched_count > 0:
            print(f"  '{kw}': Posted {matched_count} new job(s).")


def _save_to_db(job: dict, keyword: str):
    """Helper: extract budget + URL from a raw job dict and persist to SQLite."""
    job_inner = job.get('jobTile', {}).get('job', {}) or {}
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

