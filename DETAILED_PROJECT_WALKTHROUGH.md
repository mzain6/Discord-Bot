# Upwork Discord Bot — Detailed Project Walkthrough

This document provides a comprehensive overview of the technical implementation, features, and current state of the Upwork Job Tracker Bot.

---

## 1. Core Architecture

The bot is designed as a modular Python application consisting of four primary layers:

### A. The Scraper Layer (`upwork/scraper.py`)
*   **Stealth Engine**: Uses `curl_cffi` to impersonate a Chrome 124 browser TLS fingerprint.
*   **GraphQL Integration**: Interacts directly with Upwork's internal API (`/api/graphql/v1`) using the `VisitorJobSearch` query.
*   **Authentication**: Managed by `AuthManager`, which handles bearer tokens and cookie rotation to prevent session expiration.

### B. The Persistence Layer (`database/db.py`)
*   **SQLite Engine**: Replaced basic JSON configuration with a robust relational database (`jobs.db`).
*   **Tracking Management**: Stores keywords and their associated Discord Channel IDs in the `tracked_keywords` table.
*   **Deduplication**: Maintains a history of every job ID posted per keyword to ensure no duplicate alerts are ever sent.

### C. The Bot Layer (`discord_bot/bot.py`)
*   **Command Suite**:
    *   `!track <keyword>`: Starts live monitoring for a new term and creates a dedicated Discord channel.
    *   `!untrack <keyword>`: Stops monitoring and cleans up.
    *   `!list`: Displays all active keywords and their current job counts.
    *   `!stats`: Shows global statistics (total jobs tracked, most active keywords).
*   **Background Loop**: A non-blocking `tasks.loop` that runs every 30-60 seconds, cycling through all keywords in the database.

### D. The Formatting Layer (`formatters/discord_formatter.py`)
*   **Rich Embeds**: Converts raw API data into structured, aesthetic Discord messages.
*   **Threaded Details**: Automatically creates a thread for every job post containing full descriptions and client metadata.

---

## 2. Multi-Keyword Tracking Logic

The bot handles multiple keywords simultaneously using a "Sequential Polling" strategy:

1.  **Registry**: All keywords are fetched from the SQLite `tracked_keywords` table.
2.  **Dedicated Channels**: Each keyword is mapped to a specific Discord channel ID.
3.  **Search Context**: For every keyword, the scraper performs a targeted search (`q=keyword&sort=recency`).
4.  **Rate Limiting**: A 2-second safety delay is implemented between keywords to prevent API rate-limiting or IP bans.

---

## 3. Recent Technical Improvements & Stability

We have recently implemented several critical fixes to ensure the bot remains "production-ready":

*   **Nested Data Safety (AttributeError Fix)**: Added robustness to the sorting and extraction logic. The bot now safely handles cases where Upwork returns `null` for `jobTile` or `job` objects using the `(data or {}).get()` pattern.
*   **Database Count Integration**: Added `get_job_count()` to provide real-time feedback on how many jobs have been archived for each keyword.
*   **Enhanced Logging**:
    *   The bot now prints the total jobs in the database during every poll cycle.
    *   Added specific error handling for DNS issues (`curl: (6) Could not resolve host`).
*   **Migration System**: Built a one-time migration path that automatically moved keywords from the old `config.json` into the new SQLite database.

---

## 4. How to Use the Bot

| Command | Action |
| :--- | :--- |
| `!track python` | Creates `#python` channel and starts 24/7 monitoring. |
| `!list` | Shows all keywords and their database totals. |
| `!test` | Fetches the single most recent job on Upwork for instant verification. |
| `!stats` | Shows how many unique jobs have been processed since the bot started. |

---

## 5. Current Project Status

*   **Scraper**: Operational (Stealth Mode).
*   **Database**: SQLite (Migrated).
*   **Loop**: Active (Dynamic Interval).
*   **Stability**: High (Fixed AttributeError and DNS recovery logic).
