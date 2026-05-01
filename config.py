"""
Telegram Log Bot - Config (Heroku)
"""
import os
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.getenv("API_ID", 0))
API_HASH = os.getenv("API_HASH", "")
STRING_SESSION = os.getenv("STRING_SESSION", "")
SOURCE_GROUP_ID = int(os.getenv("SOURCE_GROUP_ID", 0))
LOG_GROUP_ID = int(os.getenv("LOG_GROUP_ID", 0))
