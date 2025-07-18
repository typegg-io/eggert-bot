import os

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
SECRET = os.getenv("SECRET", None)
SITE_URL = os.getenv("SITE_URL")
API_URL = os.getenv("API_URL")

TYPEGG_GUILD_ID = 703605179433484289 # TypeGG Official Server
bot_prefix = "-"

# Bot themes
default_theme = {
    "embed": 0x004B87,
    "axis": "#777777",
    "background": "#00031B",
    "graph_background": "#00031B",
    "grid": "#333333",
    "line": "#00B5E2",
    "text": "#ffffff"
}
light_theme = {
    "embed": 0x00AAD6,
    "axis": "#000000",
    "background": "#FFFFFF",
    "graph_background": "#FFFFFF",
    "grid": "#B0B0B0",
    "line": "#157EFD",
    "text": "#000000",
}
dark_theme = {
    "embed": 0x00AAD6,
    "axis": "#777777",
    "background": "#111111",
    "graph_background": "#161616",
    "grid": "#333333",
    "line": "#157EFD",
    "text": "#ffffff"
}
