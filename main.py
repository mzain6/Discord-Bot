from utils.logger import logger
from config import load_config
from discord_bot import setup_bot
from discord_bot.bot import job_scraper_loop

def main():
    logger.info("Loading configuration...")
    try:
        config_data, token = load_config()
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        return

    logger.info("Initializing Discord Bot...")
    bot = setup_bot(config_data)

    # Patch the scrape interval according to config
    interval = config_data.get('scrape_interval', 60)
    logger.info(f"Setting scrape interval to {interval} seconds.")
    job_scraper_loop.change_interval(seconds=interval)

    logger.info("Starting bot...")
    bot.run(token)

if __name__ == "__main__":
    main()
