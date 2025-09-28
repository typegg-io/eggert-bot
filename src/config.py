import os
from pathlib import Path

from dotenv import load_dotenv

from utils.colors import DEFAULT

load_dotenv()

# === Environment variables ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
SITE_URL = os.getenv("SITE_URL")
API_URL = os.getenv("API_URL")
SECRET = os.getenv("SECRET", "")

# === Webhooks ===
MESSAGE_WEBHOOK = os.getenv("MESSAGE_WEBHOOK")
ERROR_WEBHOOK = os.getenv("ERROR_WEBHOOK")

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

# Bot themes
DEFAULT_THEME = {
    "embed": DEFAULT,
    "axis": "#8E8E8E",
    "background": "#00031B",
    "graph_background": "#00031B",
    "grid": "#8E8E8E",
    "grid_opacity": 0.25,
    "line": "#00B5E2",
    "title": "#FFFFFF",
    "text": "#FFFFFF"
}

LIGHT_THEME = {
    "embed": DEFAULT,
    "axis": "#000000",
    "background": "#FFFFFF",
    "graph_background": "#FFFFFF",
    "grid": "#B0B0B0",
    "grid_opacity": 1,
    "line": "#157EFD",
    "title": "#000000",
    "text": "#000000",
}

DARK_THEME = {
    "embed": DEFAULT,
    "axis": "#777777",
    "background": "#111111",
    "graph_background": "#161616",
    "grid": "#333333",
    "grid_opacity": 1,
    "line": "#157EFD",
    "title": "#FFFFFF",
    "text": "#FFFFFF"
}
