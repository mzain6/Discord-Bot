# Upwork Job Tracker Discord Bot 🚀

A highly resilient, multi-keyword Discord bot designed to continuously monitor Upwork for new jobs and dispatch real-time alerts to dedicated Discord channels. Built with advanced anti-bot evasion techniques and a robust SQLite persistence layer to ensure high stability and duplicate-free tracking.

## ✨ Features

- **Advanced Anti-Bot Evasion**: Utilizes `curl_cffi` to mimic Chrome v124 TLS fingerprints and `SeleniumBase` (in undetected-chromedriver mode) to seamlessly fetch Cloudflare cookies and OAuth tokens, avoiding 403 Forbidden errors.
- **Multi-Keyword Tracking**: Dynamically track multiple search queries simultaneously (e.g., "Python", "React", "Web Developer").
- **Smart Discord Routing**: Automatically creates dedicated text channels for each keyword and posts relevant jobs exactly where they belong.
- **Rich Embeds & Threading**: Posts clean, aesthetic summary cards in channels and automatically creates sub-threads containing the full job description and client history (total spent, hire rate, location).
- **Zero Duplicates**: Employs an SQLite database to maintain a permanent history of tracked jobs, ensuring you never see the same job twice—even if it's updated. Handles job updates by sending a "🔄 Job Updated" notification instead of a duplicate.
- **Non-Blocking Architecture**: A background loop polls Upwork every 30-60 seconds while a separate thread handles token refreshes, preventing the main Discord bot loop from hanging.

---

## 🛠️ Tech Stack
- **Python 3.10+**
- **discord.py** - Core Discord API interaction.
- **curl_cffi** - TLS fingerprinting for GraphQL API requests.
- **SeleniumBase** - Headless browser automation for auth cookie extraction.
- **SQLite** - Relational database for job state persistence and keyword mapping.

---

## 📂 Project Structure

```text
.
├── main.py                     # Entry point to start the bot
├── auth/
│   ├── fetch_cookies.py        # Uses SeleniumBase to solve Cloudflare and extract tokens
│   └── visitor_auth.py         # Background manager to refresh expired tokens seamlessly
├── upwork/
│   └── scraper.py              # Executes internal GraphQL queries via curl_cffi
├── discord_bot/
│   ├── bot.py                  # Main async loop and Discord command registry
│   └── handlers.py             # Logic for channel & thread creation, message dispatch
├── database/
│   └── db.py                   # SQLite wrapper for deduplication and status checking
├── formatters/
│   └── discord_formatter.py    # Transforms Upwork JSON into aesthetic Discord Embeds
└── logs/                       # System logs and bot diagnostics
```

---

## 🚀 Setup & Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/mzain6/Discord-Bot.git
   cd Discord-Bot
   ```

2. **Install dependencies:**
   Ensure you have Python installed, then run:
   ```bash
   pip install -r requirements.txt
   ```

3. **Environment Setup:**
   Create a `.env` file in the root directory (you can use `.env.example` as a template) and add your Discord bot token:
   ```env
   DISCORD_BOT_TOKEN=your_token_here
   ```

4. **Run the bot:**
   ```bash
   python main.py
   ```

---

## 🎮 Bot Commands

You can control the bot directly from any channel in your Discord server:

| Command | Description |
| :--- | :--- |
| `!track <keyword>` | Adds a keyword, creates a `#keyword` channel, and starts 24/7 monitoring. |
| `!untrack <keyword>` | Stops monitoring a keyword but retains historical data and the channel. |
| `!delete <keyword>` | Completely removes a keyword, deletes its historical data, and **deletes** the Discord channel. |
| `!list` | Shows all actively tracked keywords and the total jobs captured for each. |
| `!test` | Fetches the single most recent job on Upwork across all queries to verify API connectivity. |
| `!stats` | Displays global metrics, such as total unique jobs tracked across the server. |

---

## 🧠 How it Works

1. **Authentication Layer:** Upwork blocks standard REST requests. This bot uses a background daemon (`AuthManager`) that spins up a headless `SeleniumBase` instance to fetch valid session cookies and an `oauth2/token`.
2. **GraphQL Queries:** With valid cookies, the `UpworkScraper` uses `curl_cffi` to send targeted GraphQL queries (`VisitorJobSearch`) to Upwork's internal search API.
3. **Tracking & Deduplication:** Every fetched job is checked against the `jobs.db` database. If it's `NEW`, it's sent to Discord. If it's an `UPDATE` (e.g., the client changed the budget), a modify alert is sent. If it's `SEEN`, it's ignored.
4. **Discord Presentation:** Raw data is converted into clean embeds. To keep the channel legible, the bot posts a summary card and creates a **Thread** underneath containing the full verbose job description.
