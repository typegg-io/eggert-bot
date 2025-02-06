import os

from dotenv import load_dotenv

load_dotenv()

bot_token = os.getenv("bot_token")
secret = os.getenv("secret")
home_guild_id = 703605179433484289  # TypeGG Official Server
bot_prefix = "-"

# Bot themes
default_theme = {
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
