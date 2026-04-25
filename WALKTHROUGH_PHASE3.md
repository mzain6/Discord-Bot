# Upwork Discord Bot — Complete Phase 3 Walkthrough

## Project Goal
Build a **zero-intervention, self-sustaining** Upwork job alert bot that:
- Authenticates itself automatically using a headless browser
- Searches Upwork for specific keywords using the real GraphQL API
- Posts all recent matching jobs to dedicated Discord channels on startup
- Continuously monitors and posts brand-new jobs in real-time, 24/7

---

## Full Execution Flow

```
python main.py
    │
    ├── [DB]     Opens database/jobs.db (SQLite — persistent job memory)
    ├── [CONFIG] Loads config.json (tracked_keywords, poll interval, etc.)
    │
    ├── [AUTH]   Checks auth/token_state.json
    │       ├── Tokens < 11h old? → Use saved cookies instantly (fast start)
    │       └── Tokens expired?   → Launch auth/fetch_cookies.py (subprocess)
    │               └── Headless Chrome bypasses Cloudflare, visits Upwork
    │               └── Extracts 40+ cookies + visitor_gql_token
    │               └── Saves to auth/saved_cookies.json + token_state.json
    │
    ├── [STARTUP] For each tracked keyword:
    │       ├── Fetch 20 most recent jobs (keyword-specific GraphQL search)
    │       ├── Sort newest → oldest by publishTime / createTime
    │       ├── Post ALL unseen jobs to the keyword's Discord channel
    │       └── Save all to DB (won't be reposted even after restart)
    │
    └── [LOOP]   Every 60 seconds, for each keyword:
            ├── Fetch latest 20 jobs from Upwork
            ├── Sort newest → oldest
            ├── For each job: check DB → if new, post + save; if seen, skip
            └── Each post gets a Discord thread with full job details
```

---

## File-by-File Changes

---

### `upwork/scraper.py` — The GraphQL API Client

**Role:** Makes all HTTP requests to Upwork's GraphQL endpoint using stealth TLS fingerprinting.

#### Changes Made:

**1. `fetch_jobs_summary(count, keyword)` — Niche-Specific Search**

| Before | After |
|---|---|
| Global feed fetch, no keyword passed | Keyword passed via `userQuery` in GraphQL variables |
| `sort: relevance+desc` (returned old jobs) | `sort: recency` (always returns freshest jobs) |
| `highlight: true` (caused `H^Django^H` garbage) | `highlight: false` (clean plain text) |
| `count` hardcoded to `5` at one point | Dynamic `count` parameter restored |
| Keyword only influenced referer URL | Keyword sent to Upwork's search engine via `userQuery` |

The correct field name `userQuery` was confirmed by intercepting a live browser request on Upwork. Previously tried field names `q`, `query`, and `searchExpression` all caused `ValidationError` from Upwork's API.

**Final GraphQL `requestVariables` structure:**
```json
{
  "userQuery": "seo",
  "sort": "recency",
  "highlight": false,
  "paging": { "offset": 0, "count": 20 }
}
```

**2. `update_credentials(new_cookies, auth_token)` — Added**
- Allows `AuthManager` to hot-swap session tokens into the running scraper without a restart.
- Thread-safe via CPython's atomic `dict.update()`.

---

### `discord_bot/bot.py` — The Main Orchestrator

**Role:** Runs the Discord bot, manages all commands, and drives the job-posting lifecycle.

#### Changes Made:

**1. `on_ready()` — Startup Sequence Rewritten**
- Auth is only re-triggered if tokens are actually expired (not on every startup).
- Added `if not job_scraper_loop.is_running()` guard to prevent `RuntimeError: Task is already launched` crash on Discord reconnects.
- **Startup Job Fetch**: For each keyword, fetches 20 latest jobs, sorts newest-first, posts ALL unseen ones to Discord, marks all as seen in DB.

**2. `!track <keyword>` Command — Rewritten**
- Immediately fetches 20 recent jobs for the new keyword.
- Posts all of them to the new Discord channel in real-time.
- Responds: `✅ Posted 20 recent jobs for seo. Live tracking is now active!`

**3. `job_scraper_loop` — Completely Rewritten**

| Before | After |
|---|---|
| One global Upwork fetch for all keywords | One dedicated search per keyword |
| Used `reversed(jobs)` (unreliable API order) | Sorted by `publishTime`/`createTime` (real timestamps) |
| Secondary title/desc keyword filter blocked valid jobs | Filter removed — Upwork's `userQuery` handles relevance |
| No visibility into what was blocked | Per-poll stats: `Fetched: 20, Already seen: 19, New: 1` |

**4. Removed `last_fetched_jobs` global cache** — made obsolete by per-keyword live fetching.

---

### `auth/visitor_auth.py` — The Auth Manager

**Role:** Manages the lifecycle of Upwork session tokens automatically.

#### Changes Made:

**1. Subprocess Isolation — Critical Bug Fix**
- **Problem:** Discord's bot uses `asyncio`. SeleniumBase also runs its own internal event loop. Running both in the same process caused: `RuntimeError: This event loop is already running`.
- **Solution:** `AuthManager.refresh()` now calls `subprocess.run(['python', 'auth/fetch_cookies.py'])`. This gives the browser its own isolated Python process with a clean event loop. If the browser crashes, the bot is completely unaffected.

**2. Disk Persistence**
- After every successful refresh, tokens are written to `auth/saved_cookies.json` and `auth/token_state.json`.
- On the next startup, the bot reads these files. If tokens are under 11 hours old, the browser is never opened — the bot starts in under 1 second.

**3. Background Refresh Thread**
- A daemon thread checks every 30 minutes if 11 hours have passed.
- If yes, a silent background refresh runs without pausing the bot.

**4. Emergency Reactive Refresh**
- If the polling loop catches a `401` or `403` error, it immediately triggers `auth_manager.refresh()` without waiting for the 11-hour timer.

---

### `auth/fetch_cookies.py` — The Browser Worker *(New File)*

**Role:** A standalone, single-purpose script run as a subprocess to extract Upwork session tokens.

- Uses **SeleniumBase in UC Mode** (Undetected-Chromedriver) to bypass Cloudflare's bot detection.
- Visits `https://www.upwork.com/nx/search/jobs/` as an anonymous visitor.
- Waits for full page load, extracts all cookies and the `visitor_gql_token`.
- Outputs result as a single line of JSON to stdout so the parent process can read it.
- On failure: exits with non-zero code so `AuthManager` knows to retry.

---

### `database/db.py` — The Persistent Memory

**Role:** SQLite wrapper that prevents duplicate posts and enables analytics.

#### Schema:
```sql
CREATE TABLE jobs (
    job_id           VARCHAR(255),
    keyword          VARCHAR(255),
    title            TEXT,
    description      TEXT,
    job_type         VARCHAR(20),      -- HOURLY or FIXED
    budget           VARCHAR(50),      -- e.g. "$25-$45/hr" or "$500 Fixed"
    experience_level VARCHAR(20),      -- EntryLevel / Intermediate / Expert
    posted_at        TIMESTAMP,        -- Upwork's createTime
    detected_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    job_url          TEXT,
    raw_json         TEXT,             -- Full API response for debugging
    PRIMARY KEY (job_id, keyword)      -- Composite key!
);
```

**Why a Composite Primary Key `(job_id, keyword)`?**
A job titled "Python/Django Developer Needed" can match both the `python` and `django` keywords. The composite key allows one row per job-keyword pair, so the job posts to both channels exactly once each — never duplicated.

**Key Methods:**
| Method | Purpose |
|---|---|
| `is_seen(job_id, keyword)` | Deduplication check before every single post |
| `save_job(job_data, keyword, budget, url)` | Called immediately after posting |
| `get_stats()` | Powers the `!stats` Discord command |

---

### `formatters/discord_formatter.py` — The Message Designer

**Role:** Converts raw Upwork API JSON into clean, readable Discord messages.

#### Changes Made:

**1. `format_job_summary()` — Complete Visual Redesign**

Removed permanently:
- `Proposals: N/A (Search API limitation)` — always N/A, added noise
- `Client Info: N/A (Search API limitation)` — always N/A, added noise
- `Time: HH:MM` — redundant with Posted field

Added:
- Visual separator lines (`━━━━━━━━━━━━━━━━━━━━━━━`) for a card-like look
- Color-coded experience levels: `🟢 Entry` / `🟡 Intermediate` / `🔴 Expert`
- Job type icon: `⏱ Hourly` / `💰 Fixed Price`
- Improved budget formatting: `$25 – $45/hr` (with em-dash)
- 1990-char hard safety cap on the entire message

**New format:**
```
━━━━━━━━━━━━━━━━━━━━━━━
🆕 New Job Alert
━━━━━━━━━━━━━━━━━━━━━━━
📌 SEO Expert Needed for E-Commerce Brand

💵 Budget: $25 – $45/hr
🎯 Level: 🟡 Intermediate
📁 Type: ⏱ Hourly
🕒 Posted: 8 minutes ago

📝 Description:
We're looking for an experienced SEO specialist to...

🔗 Apply on Upwork
━━━━━━━━━━━━━━━━━━━━━━━
```

**2. `format_thread_details()` — 400 Bad Request Fix**

| Before | After |
|---|---|
| Description capped at 1800 chars | Description capped at 1200 chars |
| No total message cap | 1990-char hard cap on full message |
| Frequent `400 Bad Request` errors | Zero Discord limit errors |

The metadata block (client details + job type + URL) adds ~300 chars. Capping the description alone at 1800 was not enough — the total was consistently exceeding Discord's 2000-char limit.

---

## Discord Commands

| Command | Description |
|---|---|
| `!track <keyword>` | Creates a channel, fetches & posts 20 recent jobs, starts live tracking |
| `!untrack <keyword>` | Stops tracking. Channel stays but no new posts |
| `!list` | Lists all actively tracked keywords |
| `!stats` | Shows jobs tracked total and per keyword (from SQLite) |
| `!test` | Fetches 1 job immediately and posts to current channel |

---

## Project Structure

```
Upwork_Bot/
├── auth/
│   ├── fetch_cookies.py      ← Standalone browser subprocess
│   ├── visitor_auth.py       ← Auth lifecycle manager
│   ├── saved_cookies.json    ← Persisted session cookies
│   └── token_state.json      ← Last refresh timestamp
├── database/
│   ├── db.py                 ← SQLite wrapper
│   └── jobs.db               ← Persistent job history
├── discord_bot/
│   ├── bot.py                ← Main bot orchestrator
│   └── handlers.py           ← Channel/thread helpers
├── upwork/
│   └── scraper.py            ← GraphQL API client
├── formatters/
│   └── discord_formatter.py  ← Message formatter
├── config/
│   └── __init__.py           ← Config load/save
├── config.json               ← Tracked keywords + settings
├── main.py                   ← Entry point
├── requirements.txt
└── .env                      ← DISCORD_TOKEN (git-ignored)
```

---

## How to Run

```bash
# 1. Set your Discord token
echo DISCORD_TOKEN=your_token_here > .env

# 2. Install dependencies
pip install -r requirements.txt

# 3. Install browser driver (first time only)
sbase install chromedriver

# 4. Start the bot
python main.py
```

The bot will handle **everything else** — auth, searching, posting, and refreshing — automatically.
