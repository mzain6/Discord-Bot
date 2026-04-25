# Upwork Discord Bot - System Architecture & Data Flow

This document outlines the complete end-to-end architecture and data flow of the Upwork Discord Bot V2. The system is designed to bypass Upwork's anti-bot protections, fetch jobs continuously across multiple search keywords, track historical jobs to prevent duplicates, and route jobs to specific Discord channels.

---

## 1. Authentication & Cookie Management Flow
Upwork aggressively blocks standard scrapers (returning `403 Forbidden`). The bot uses a multi-layered approach to maintain a valid, human-like session.

1. **Initial Authentication (`auth/fetch_cookies.py`)**
   - Uses **SeleniumBase** (specifically `SB` with undetected-chromedriver mode) to open a headless browser.
   - Navigates to Upwork and fetches valid security cookies and OAuth tokens (`oauth2/token`).
   - Saves these credentials securely into `auth/saved_cookies.json`.

2. **Background Refresh (`auth/auth_manager.py` & `bot.py`)**
   - When the bot starts, the `AuthManager` checks if tokens are expired.
   - It runs a **background thread** that periodically fetches fresh cookies using SeleniumBase.
   - This ensures the main Discord bot loop never gets blocked waiting for browser interactions.

---

## 2. Job Scraping Flow
Instead of traditional REST endpoints or HTML scraping, the bot reverse-engineers Upwork's internal GraphQL API.

1. **TLS Fingerprinting (`upwork/scraper.py`)**
   - Uses `curl_cffi` (impersonating Chrome v120) instead of the standard `requests` library. This perfectly mimics browser TLS signatures to bypass Cloudflare/Upwork WAF.
2. **GraphQL Queries**
   - The bot loads the active cookies and tokens from `AuthManager`.
   - It sends an HTTP POST request to `https://www.upwork.com/api/graphql/v1` containing the GraphQL query for job searches.
   - The query includes the specific `userQuery` (e.g., "web dev") and requests a batch of jobs sorted by recency.

---

## 3. Core Bot Loop & Tracking Flow
The heart of the application runs on a 60-second asynchronous loop using `discord.py`'s `@tasks.loop`.

1. **Keyword Iteration (`discord_bot/bot.py`)**
   - The loop queries the SQLite database (`jobs.db` -> `tracked_keywords` table) to get a list of all currently tracked keywords.
   - For each keyword, it calls the `UpworkScraper` to fetch the top 20 most recent jobs.
2. **Database Deduplication (`database/db.py`)**
   - Every fetched job is passed to the database via `job_db.get_job_status()`.
   - **`NEW`**: If the `job_id` has never been seen for this keyword.
   - **`UPDATE`**: If the `job_id` exists, but the client edited the `title`, `description`, `budget`, or `experience_level`.
   - **`SEEN`**: If the job exists and hasn't fundamentally changed. (Ignored).
3. **Data Persistence**
   - Jobs marked as NEW or UPDATE are saved/updated in the `jobs` table so they are not posted again. The database handles composite primary keys `(job_id, keyword)` to allow the same job to be posted in multiple distinct keyword channels without collision.

---

## 4. Discord Routing & Formatting Flow
Once a job is confirmed as NEW or an UPDATE, it gets pushed to the Discord server.

1. **Channel Management (`discord_bot/handlers.py`)**
   - The bot looks for a Discord channel named after the keyword (e.g., `#web-dev`).
   - If the channel does not exist, the bot **dynamically creates it** and restricts its permissions (so only the bot can post, users can read).
2. **Message Formatting (`formatters/discord_formatter.py`)**
   - The job JSON is parsed into a clean, visually appealing Discord Embed/Message.
   - It highlights Budget, Experience Level, Job Type (Hourly/Fixed), and a preview of the description.
   - Updates get a `🔄 Job Updated` header, while new jobs get a `🆕 New Job Alert` header.
3. **Thread Creation (`discord_bot/handlers.py`)**
   - To keep the main channel clean, the bot posts the summary message, and then instantly creates a **Discord Thread** underneath that message.
   - Inside the thread, the bot posts the **Full Description** and **Client History** (Total Spent, Hire Rate, Location).

---

## User Interaction Flow (Commands)
Users can control the bot dynamically from within Discord without restarting the server:

- `!track <keyword>`: Adds a keyword to the database, creates a Discord channel, and instantly fetches the last 20 jobs.
- `!list`: Shows all currently tracked keywords and how many jobs have been captured for each.
- `!untrack <keyword>`: Stops tracking the keyword but leaves the historical data and Discord channel intact.
- `!delete <keyword>`: Completely wipes the keyword from the database, deletes the historical jobs, and **deletes the Discord channel**.
- `!stats`: Shows global metrics (e.g., total unique jobs tracked across all keywords).
