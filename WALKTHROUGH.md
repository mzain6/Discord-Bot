# Upwork Discord Bot — Professional Project Walkthrough
**Date:** April 20, 2026  
**Version:** V2.0 — Dynamic Keyword Tracking  
**Status:** Fully Operational

---

## Overview

This bot automates Upwork job monitoring and delivers targeted job alerts directly to your Discord server. It works by periodically scraping Upwork's GraphQL API, filtering results against your personally configured keywords, and posting matching jobs into automatically created dedicated channels — complete with threaded full details.

---

## Project Folder Structure

```
Upwork_Bot/
│
├── main.py                         ← Application entry point
├── config.json                     ← Persistent bot settings & keywords
├── .env                            ← Secret token (not committed to git)
├── .env.example                    ← Template for .env setup
├── requirements.txt                ← Python dependencies
├── WALKTHROUGH.md                  ← This file
│
├── config/
│   ├── __init__.py
│   └── config.py                   ← Config loader & saver
│
├── upwork/
│   ├── __init__.py
│   └── scraper.py                  ← Upwork GraphQL scraper engine
│
├── discord_bot/
│   ├── __init__.py
│   ├── bot.py                      ← Core bot logic, commands & loop
│   └── handlers.py                 ← Discord channel & message helpers
│
└── formatters/
    ├── __init__.py
    └── discord_formatter.py        ← Message formatting & templates
```

---

## File-by-File Breakdown

---

### 📄 `main.py` — Application Entry Point

**Purpose:** The single command you run (`python main.py`) to start the entire system.

**What it does:**
1. Loads the bot configuration and Discord token from `config.json` and `.env`.
2. Passes the config into the bot instance via `setup_bot()`.
3. Reads `scrape_interval` from config and dynamically sets how often the bot checks Upwork (default: every 30 seconds).
4. Starts the Discord bot with `bot.run(token)`.

**Key design decision:** The scrape interval is **not hardcoded** — changing `scrape_interval` in `config.json` changes the polling speed without touching any code.

---

### 📄 `config/config.py` — Configuration Manager

**Purpose:** Handles reading and writing persistent application settings.

**What it does:**
- `load_config()` — Reads `DISCORD_TOKEN` from your `.env` file securely via `python-dotenv`. Reads `config.json` for all bot settings.
- `save_config()` — Writes updated settings back to `config.json`. This is called every time you use `!track` or `!untrack` in Discord, ensuring your keywords survive restarts.

**Key fields in `config.json`:**

| Field | Purpose |
|---|---|
| `tracked_keywords` | List of keywords you are monitoring on Upwork |
| `scrape_interval` | How often (seconds) the bot checks Upwork |
| `thread_auto_archive` | How many minutes before a job thread auto-archives |
| `max_fetch_count` | How many jobs to fetch per Upwork API call |

---

### 📄 `upwork/scraper.py` — Upwork API Engine

**Purpose:** The core intelligence of the bot — responsible for bypassing Upwork's bot protection and fetching live job data.

**How Upwork's Security Was Bypassed:**
Upwork uses Cloudflare, which analyzes the TLS fingerprint of every connection. Standard Python `requests` is immediately detected and blocked with a `403 Forbidden` error.

**Solution:** We use `curl_cffi` with `impersonate="chrome124"`. This library mimics a real Google Chrome browser at the TLS level, making the connection indistinguishable from a human browsing on Chrome 124.

**What it fetches via GraphQL:**
- Job ID, Title, Description
- Job Type (Hourly vs. Fixed)
- Hourly budget range or fixed price amount
- Experience level required (`contractorTier`)
- Encrypted job cipher (used to construct the direct Upwork URL)
- `createTime` — the exact timestamp when the job was posted

**Key method:**
```python
scraper.fetch_jobs_summary(count=100)
```
Returns a list of raw job dictionaries ready for processing.

---

### 📄 `discord_bot/bot.py` — Core Bot Brain

**Purpose:** Orchestrates everything — the Discord connection, all user commands, and the automated background scraping loop.

**On Startup (`on_ready`):**
1. Prints the V2.0 banner and currently tracked keywords.
2. Fetches the latest jobs immediately from Upwork.
3. Scans them against your existing tracked keywords and posts any matches right away — so you get results the moment the bot starts, not just when new jobs appear.
4. Starts the periodic `job_scraper_loop`.

**Discord Commands:**

| Command | What it does |
|---|---|
| `!track <keyword>` | Adds keyword, auto-creates a `#channel-name` in your server, scans existing jobs immediately, saves to config |
| `!untrack <keyword>` | Removes keyword from tracking list, saves to config |
| `!list` | Shows all currently tracked keywords |
| `!test` | Fetches and posts 1 job immediately for testing |

**The Scraping Loop (`job_scraper_loop`):**
- Runs on a configurable interval (default 30 seconds).
- Fetches the latest batch of Upwork jobs.
- Iterates through each job and checks if any tracked keyword appears in the **title or description**.
- For each match, it routes the job to the correct keyword channel and creates an auto-thread.
- Uses a `seen_jobs` set to **guarantee no duplicate posts**.

**Smart Channel Routing:**
The keyword `"python developer"` automatically becomes the channel name `#python-developer` — spaces and special characters are replaced with hyphens using a regex sanitizer.

---

### 📄 `discord_bot/handlers.py` — Discord Action Helpers

**Purpose:** Clean, reusable async functions for all Discord-specific operations.

**Functions:**

| Function | Purpose |
|---|---|
| `ensure_job_channel(guild, name, create)` | Finds a channel by name; optionally creates it if it doesn't exist. Handles `Forbidden` errors if the bot lacks permissions. |
| `post_job_to_channels(channel, msg)` | Sends the formatted job summary message to a channel. Returns the message object for thread creation. |
| `create_job_thread(message, title, duration)` | Attaches a discussion thread to a job post message. |
| `post_thread_details(thread, msg)` | Posts the full job details inside the thread. |

---

### 📄 `formatters/discord_formatter.py` — Message Formatter

**Purpose:** Transforms raw Upwork API JSON into professional, readable Discord Markdown messages.

**`format_job_summary(job_data)`** — The main channel post:
- Reconstructs the direct Upwork job URL from the encrypted `ciphertext` ID.
- Converts the raw ISO `createTime` timestamp into a human-friendly offset like `"14 minutes ago"`.
- Parses hourly/fixed budget into readable format (`$20-$35/hr` or `$500`).
- Translates experience codes (`EntryLevel` → `Entry`, etc.).
- Truncates descriptions to 300 characters for the summary post.

**`format_thread_details(job_data)`** — The thread expansion:
- Shows the full job description (truncated at 1800 chars to respect Discord's 2000-character message limit — a bug fix implemented today).
- Displays job duration, type, and experience level.
- Shows client stats placeholders (`Total Spent`, `Hire Rate`, etc.) ready for when full details become available.

**`get_thread_title(title)`** — Sanitizes job titles for use as Discord thread names (maximum 100 characters).

---

## Data Flow Diagram

```
Discord: !track "graphic designer"
         │
         ▼
   bot.py: track()
         │─── save_config() → config.json updated
         │─── ensure_job_channel() → creates #graphic-designer
         │─── scan last_fetched_jobs → post any immediate matches
         │
         ▼
   job_scraper_loop() [every 30s]
         │─── scraper.fetch_jobs_summary(count=100)
         │─── for each new job:
         │       │─── check title & description for "graphic designer"
         │       │─── if match found:
         │               │─── format_job_summary() → channel message
         │               │─── post_job_to_channels() → Discord
         │               │─── create_job_thread() → thread attached
         │               └─── format_thread_details() → posted in thread
```

---

## Technical Challenges Solved Today

| Challenge | Solution |
|---|---|
| 403 Forbidden from Cloudflare | `curl_cffi` with `impersonate="chrome124"` |
| Messages crashing with 400 error | Added 1800-character truncation for job descriptions |
| Bot posting nothing (no keyword matches) | Upwork API returns global feed — increased fetch count & improved local filtering |
| Keywords lost on restart | `save_config()` persists to `config.json` after every `!track`/`!untrack` |
| Old code running after edits | Cleared `.pyc` cache files to force fresh code reload |
| Bot silent after `!track` | Added immediate "retro-active" scan of last fetched batch |

---

## How to Run

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Create your .env file
echo DISCORD_TOKEN=your_token_here > .env

# 3. Start the bot
python main.py
```

**Then in your Discord server:**
```
!track graphic designer      ← Start monitoring a keyword
!track python developer      ← Add another
!list                        ← View all active keywords
!untrack graphic designer    ← Stop monitoring a keyword
!test                        ← Instantly fetch and post 1 job
```

---

*Last updated: April 20, 2026 — V2.0 Dynamic Keyword Tracking*
