import os

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
SECRET = os.getenv("SECRET", None)
SITE_URL = os.getenv("SITE_URL")
API_URL = os.getenv("API_URL")

TYPEGG_GUILD_ID = 703605179433484289 # TypeGG Official Server
VERIFIED_ROLE_NAME = "Verified Egg 🥚"
bot_prefix = "-"

# Bot themes
default_theme = {
    "embed": 0x004B87,
    "axis": "#8E8E9F",
    "background": "#00031B",
    "graph_background": "#00031B",
    "grid": "#8E8E9F",
    "grid_opacity": 0.25,
    "line": "#00B5E2",
    "title": "#FFFFFF",
    "text": "#8E8E9F"
}
light_theme = {
    "embed": 0x00AAD6,
    "axis": "#000000",
    "background": "#FFFFFF",
    "graph_background": "#FFFFFF",
    "grid": "#B0B0B0",
    "grid_opacity": 1,
    "line": "#157EFD",
    "title": "#000000",
    "text": "#000000",
}
dark_theme = {
    "embed": 0x00AAD6,
    "axis": "#777777",
    "background": "#111111",
    "graph_background": "#161616",
    "grid": "#333333",
    "grid_opacity": 1,
    "line": "#157EFD",
    "title": "#FFFFFF",
    "text": "#FFFFFF"
}
