import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# === Environment variables ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
SITE_URL = os.getenv("SITE_URL")
BOT_SUBDOMAIN = os.getenv("BOT_SUBDOMAIN")
SECRET = os.getenv("SECRET", "")

# === Webhooks ===
MESSAGE_WEBHOOK = os.getenv("MESSAGE_WEBHOOK")
ERROR_WEBHOOK = os.getenv("ERROR_WEBHOOK")
CHATBOT_WEBHOOK_URL = os.getenv("CHATBOT_WEBHOOK_URL")

# === Bot configuration ===
BOT_PREFIX = "-"
STAGING = MESSAGE_WEBHOOK is None
TYPEGG_GUILD_ID = 703605179433484289
STATS_CHANNEL_ID = 1337196592905846864
VERIFIED_ROLE_NAME = "Verified Egg 🥚"
DAILY_QUOTE_CHANNEL_ID = 1419332457060372633
DAILY_QUOTE_ROLE_ID = 1421957288385712230

# === User IDs ===
EIKO = 87926662364160000
KEEGAN = 155481579005804544

# === Paths ===
ROOT_DIR = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT_DIR / "src"
