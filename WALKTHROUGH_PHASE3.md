# Upwork Discord Bot — Phase 3 Walkthrough

We have successfully completed **Phase 3**, transforming the bot from a manual script into a self-sustaining, professional-grade monitoring system.

## 1. Zero-Intervention Auth Engine
The bot now handles its own authentication without any manual token pasting.
- **SeleniumBase Integration**: Uses a headless, undetected browser to visit Upwork as a "visitor."
- **Subprocess Isolation**: To avoid `asyncio` conflicts, the browser runs in a separate process (`auth/fetch_cookies.py`).
- **Disk Persistence**: Tokens and cookies are saved to `auth/saved_cookies.json` and reused. The bot only opens a browser once every 11 hours or if it hits a 403 error.

## 2. Niche-Specific Search Architecture
The bot no longer fetches a "Global Feed." It performs targeted searches for your specific keywords.
- **`userQuery` Logic**: Passed directly into Upwork's GraphQL API.
- **Per-Keyword Polling**: Every minute, the bot searches for "seo", "graphic designer", etc., individually.
- **Accuracy**: This ensures that even low-volume niches are tracked perfectly, even if they wouldn't appear in the top 100 global results.

## 3. Persistent Storage (SQLite)
Replaced the fragile `seen_jobs` set with a robust database (`database/jobs.db`).
- **Memory Recovery**: If the bot restarts, it still remembers every job it has ever posted.
- **Composite Deduping**: Jobs are tracked by `(job_id, keyword)`. This allows a job to match multiple keywords (being posted in multiple channels) but never duplicate within the same channel.
- **Analytics**: New `!stats` command provides real-time tracking data.

## 4. Enhanced User Experience
- **Historical Catch-up**: On startup or when using `!track`, the bot instantly pulls the **last 5 matching jobs** for that niche, so you see activity immediately.
- **Threaded Details**: Every job post automatically creates a Discord thread containing the full description, client history, and budget details.
- **Safe Truncation**: Intelligently handles Discord's 2000-character limit to prevent "Bad Request" errors.

---

## Detailed File Changes

### `upwork/scraper.py`
- **Hot-Swapping**: Added `update_credentials()` to update cookies/headers without restart.
- **Niche variables**: Refactored `fetch_jobs_summary` to use `userQuery` and `sort: relevance+desc`.
- **Clean Output**: Disabled `highlight` to remove search-engine artifacts (like `H^`).

### `discord_bot/bot.py`
- **Search Loop**: Rewritten to perform dedicated per-keyword searches.
- **Startup Sync**: Added historical catch-up (last 5 jobs) for all keywords on `on_ready`.
- **Async Guards**: Added `is_running()` and `run_in_executor` to prevent event loop crashes.
- **Command Updates**: Refactored `!track` for instant results and added `!stats`.

### `auth/visitor_auth.py` & `auth/fetch_cookies.py`
- **Process Isolation**: Split auth into a separate process to solve the `asyncio` loop conflict.
- **State Logic**: Added disk persistence for tokens so the browser only opens when necessary.

### `database/db.py`
- **Schema**: Implemented a `jobs` table with a composite primary key `(job_id, keyword)`.
- **Analytics**: Added `get_stats()` for the `!stats` command.

### `formatters/discord_formatter.py`
- **Length Safety**: Lowered truncation to 1400 chars + 1990 char hard cap to stay within Discord limits.

---

## How to Run
1.  Ensure `DISCORD_TOKEN` is in `.env`.
2.  Install dependencies: `pip install -r requirements.txt`.
3.  Install browsers: `sbase install chromedriver`.
4.  Run: `python main.py`.
