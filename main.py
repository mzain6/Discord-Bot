import os
from config import load_config
from discord_bot import setup_bot
from discord_bot.bot import job_scraper_loop

def main():
    print("Loading configuration...")
    try:
        config_data, token = load_config()
    except Exception as e:
        print(f"Failed to load configuration: {e}")
        return

    print("Initializing Discord Bot...")
    bot = setup_bot(config_data)

    # Patch the scrape interval according to config
    interval = config_data.get('scrape_interval', 60)
    print(f"Setting scrape interval to {interval} seconds.")
    job_scraper_loop.change_interval(seconds=interval)

    print("Starting bot...")
    bot.run(token)

if __name__ == "__main__":
    main()
