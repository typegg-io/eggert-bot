import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# === Environment variables ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
SITE_URL = os.getenv("SITE_URL")
BOT_SUBDOMAIN = os.getenv("BOT_SUBDOMAIN")
SECRET = os.getenv("SECRET", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# === Webhooks ===
MESSAGE_WEBHOOK = os.getenv("MESSAGE_WEBHOOK")
ERROR_WEBHOOK = os.getenv("ERROR_WEBHOOK")
WEB_SERVER_WEBHOOK = os.getenv("WEB_SERVER_WEBHOOK")
CHATBOT_WEBHOOK_URL = os.getenv("CHATBOT_WEBHOOK_URL")
CHAT_WEBHOOK_URL = os.getenv("CHAT_WEBHOOK_URL")
SITE_CHAT_URL = os.getenv("SITE_CHAT_URL")

# === Bot configuration ===
BOT_PREFIX = "-"
STAGING = MESSAGE_WEBHOOK is None
TYPEGG_GUILD_ID = 703605179433484289
STATS_CHANNEL_ID = 1337196592905846864
GENERAL_CHANNEL_ID = 1291419824504705114
VERIFIED_ROLE_NAME = "Verified Egg 🥚"
DAILY_QUOTE_CHANNEL_ID = 1419332457060372633
DAILY_QUOTE_ROLE_ID = 1421957288385712230

LANGUAGE_ROLE_IDS = {
    "french": 1520389620007833790,  # Français
    "german": 1520388722728894515,  # Deutsch
    "indonesian": 1520389795593977856,  # Bahasa Indonesia
    "italian": 1520389436322484244,  # Italiano
    "portuguese": 1520415029109723167,  # Português
    "russian": 1520398942754570270,  # Русский
    "spanish": 1520389699087106049,  # Español
    "turkish": 1520399120467230822,  # Türkçe
    "vietnamese": 1520399008810405999,  # Tiếng Việt
}

# === Global chat bridge (per-universe) ===
# ISO-639-1 universe codes
UNIVERSE_CODES = ("en", "fr", "it", "ru", "es", "vi", "de", "pt", "tr", "id", "nl")
DEFAULT_UNIVERSE = "en"

# Discord channel bridged for each universe (en is the general channel).
CHAT_CHANNEL_IDS = {
    "en": GENERAL_CHANNEL_ID,
    "fr": 1520394133036990607,
    "de": 1520394065798103100,
    "id": 1520394755497000960,
    "it": 1520394682218053632,
    "pt": 1520415436624232498,
    "ru": 1520399776972275753,
    "es": 1520394541578981521,
    "tr": 1520399938780004473,
    "vi": 1520399874560888884,
    "nl": 1529843950272122991,
}

CHAT_WEBHOOK_URLS = {
    code: CHAT_WEBHOOK_URL if code == DEFAULT_UNIVERSE else os.getenv(f"CHAT_{code.upper()}_WEBHOOK_URL")
    for code in UNIVERSE_CODES
}
CHAT_CHANNEL_UNIVERSES = {cid: code for code, cid in CHAT_CHANNEL_IDS.items() if cid}


def normalize_universe(code):
    """Return a valid universe code, defaulting to 'en' for missing/unknown values."""
    return code if code in UNIVERSE_CODES else DEFAULT_UNIVERSE


# === User IDs ===
EIKO = 87926662364160000
KEEGAN = 155481579005804544

# === Paths ===
ROOT_DIR = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT_DIR / "src"
