import aiohttp
from aiohttp import web

from config import CHAT_WEBHOOK_URL
from utils.logging import log_server
from web_server.utils import validate_authorization, error_response


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

    if not username or not content:
        return error_response("Missing required fields: username, content.", 400)

    async with aiohttp.ClientSession() as session:
        await session.post(CHAT_WEBHOOK_URL, json={
            "username": username,
            "avatar_url": avatar_url,
            "content": content,
        })

    log_server(f"[chat] {username}: {content[:50]}")
    return web.json_response({"success": True})
