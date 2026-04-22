import os
import json
from dotenv import load_dotenv

def load_config():
    """Loads configuration and returns it along with the discord token."""
    load_dotenv()
    token = os.getenv('DISCORD_TOKEN')
    
    if not token:
        raise ValueError("DISCORD_TOKEN not found in environment variables. Please check your .env file.")
        
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config.json')
    try:
        with open(config_path, 'r') as f:
            config_data = json.load(f)
    except FileNotFoundError:
        config_data = {
            "tracked_keywords": [],
            "scrape_interval": 60,
            "thread_auto_archive": 60
        }
        
    return config_data, token

def save_config(config_data):
    """Saves the configuration dictionary back to config.json."""
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config.json')
    with open(config_path, 'w') as f:
        json.dump(config_data, f, indent=2)
