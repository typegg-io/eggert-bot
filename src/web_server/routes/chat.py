import aiohttp
from aiohttp import web

from config import CHAT_WEBHOOK_URL
from utils.logging import log_server
from web_server.utils import validate_authorization, error_response

GLOBAL_EMOTE = "<:gc1:1489646936813469767>" + "<:gc2:1489646971965935617> "
GLOBAL_EMOTE_PLUS = "<:gc_gg1:1493934783078596669>" + "<:gc_gg2:1493934844441395354> "


async def receive_message(request: web.Request):
    """Forward a site chat message to Discord (POST /chat/receive)."""
    auth_error = validate_authorization(request)
    if auth_error:
        return auth_error

    try:
        data = await request.json()
    except Exception:
        return error_response("Invalid JSON body.", 400)

    username = data.get("username")
    avatar_url = data.get("avatarUrl")
    content = data.get("content")
    is_gg_plus = data.get("isGgPlus")

    if not username or not content:
        return error_response("Missing required fields: username, content.", 400)

    emote = GLOBAL_EMOTE_PLUS if is_gg_plus else GLOBAL_EMOTE

    async with aiohttp.ClientSession() as session:
        await session.post(CHAT_WEBHOOK_URL, json={
            "username": username,
            "avatar_url": avatar_url,
            "content": "\u200b" + emote + content,
            "allowed_mentions": {"parse": []},
        })

    log_server(f"[chat] {username}: {content[:50]}")
    return web.json_response({"success": True})
