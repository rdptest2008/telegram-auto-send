"""
Configuration settings for the Telegram bot
"""
import os
from pathlib import Path

# Base directories
BASE_DIR = Path(__file__).parent
ACCOUNTS_DIR = BASE_DIR / 'accounts'
LOGS_DIR = BASE_DIR / 'logs'

# Create directories if they don't exist
ACCOUNTS_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

# Telegram API credentials
API_ID = 'id'
API_HASH = 'hash'
BOT_TOKEN = 'tok'

# Admin settings
ADMIN_USER_ID = id

# Default message settings
DEFAULT_MIN_INTERVAL = 30  # minutes
DEFAULT_MAX_INTERVAL = 60  # minutes

# Auto-send settings
AUTO_SEND_CHECK_INTERVAL = 60  # seconds
MESSAGE_DELAY_BETWEEN_GROUPS = 2  # seconds

# Logging settings
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_FILE = LOGS_DIR / 'bot.log'

# Database settings
DB_NAME = 'bot.db'

# Session settings
SESSION_DIR_NAME = 'sessions'
