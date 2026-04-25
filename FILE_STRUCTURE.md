# Upwork Discord Bot - File Structure & Detailed Responsibilities

This document provides a detailed breakdown of every file in the project, explaining its specific role and how it connects to the rest of the application.

---

## 1. Root Directory

- **`main.py`**
  The main entry point of the application. It loads environment variables, initializes the bot configuration, and starts the Discord bot connection loop using the bot token.
- **`config.json` / `.env`**
  Configuration files storing the Discord bot token, global settings, and legacy settings.
- **`requirements.txt`**
  Lists all Python dependencies needed to run the project (e.g., `discord.py`, `curl_cffi`, `seleniumbase`).

---

## 2. Authentication (`auth/`)
This folder handles everything related to bypassing Upwork's bot protection and keeping the session alive.

- **`auth/fetch_cookies.py`**
  Uses **SeleniumBase** (`SB` in undetected-chromedriver mode) to open a headless browser. It navigates to Upwork, solves any initial Cloudflare checks, and extracts the vital `oauth2/token` and active session cookies.
- **`auth/visitor_auth.py`**
  Contains the `AuthManager` class. This is a background daemon that monitors the lifespan of the Upwork token. When the token nears expiration, it runs `fetch_cookies.py` in a separate background thread. This ensures the main Discord bot loop is never blocked or paused while waiting for browser interactions.
- **`auth/saved_cookies.json`**
  A local storage file where the active Upwork cookies, OAuth access token, and CSRF tokens are stored after a successful browser run. The scraper reads from this file.
- **`auth/token_state.json`**
  A small tracking file that strictly stores the expiration timestamp of the current token to help the `AuthManager` know exactly when to refresh.

---

## 3. Scraper Core (`upwork/`)
This folder is strictly responsible for communicating with Upwork's API.

- **`upwork/scraper.py`**
  Contains the `UpworkScraper` class. It reads the cookies from `saved_cookies.json` and uses `curl_cffi` (impersonating Chrome v120) to send requests. It executes raw GraphQL POST requests to Upwork's internal search API to fetch the latest job postings based on the keywords requested by the bot.

---

## 4. Bot Engine (`discord_bot/`)
This folder contains the Discord application logic and the main execution loop.

- **`discord_bot/bot.py`**
  The central brain of the Discord bot. 
  - Runs the `@tasks.loop(seconds=60)` which iterates over all keywords stored in the database.
  - Commands the `UpworkScraper` to fetch jobs for those keywords.
  - Filters out old jobs by querying the database.
  - Dispatches `NEW` and `UPDATE` jobs to the Discord server.
  - Registers all user commands (`!track`, `!untrack`, `!list`, `!delete`, `!stats`).
- **`discord_bot/handlers.py`**
  Contains helper functions for directly interacting with the Discord API. This includes `ensure_job_channel` (which dynamically creates new Discord text channels for new keywords and locks permissions), `post_job_to_channels`, and `create_job_thread` (which creates a thread under the main job message for extra details).

---

## 5. Database (`database/`)
This folder is responsible for state persistence and deduplication.

- **`database/db.py`**
  Contains the `JobDatabase` class. It is a SQLite wrapper that:
  - Creates the `jobs` and `tracked_keywords` tables.
  - Houses the `get_job_status()` logic, which compares a newly scraped job against historical data to determine if it is `NEW`, an `UPDATE` (e.g., the title, description, or budget changed), or already `SEEN`.
  - Safely saves jobs and tracks which Discord channels correspond to which keywords.
- **`database/jobs.db`**
  The actual SQLite database file containing all historical job data.

---

## 6. Formatters (`formatters/`)
This folder handles the visual presentation of data.

- **`formatters/discord_formatter.py`**
  Takes the raw, messy JSON returned by Upwork's GraphQL API and transforms it into clean, readable text blocks for Discord. It calculates "time ago" (e.g., "Posted 5 minutes ago"), maps job types to emojis, structures the budget strings securely, and constructs the detailed text used in the Discord threads.

---

## 7. Utilities (`utils/` & `logs/`)
- **`utils/logger.py`**
  Configures the standard Python `logging` module. It ensures that clean, timestamped logs are printed to the terminal and simultaneously saved to a log file.
- **`logs/bot.log`**
  The active log file where all `[INFO]`, `[WARNING]`, and `[ERROR]` messages are permanently recorded. Useful for tracking down API errors or checking when a specific job was posted.
