"""The routes TypeGG uses to link an account it verified through Discord OAuth."""

from json import JSONDecodeError
from typing import TYPE_CHECKING

from aiohttp import web

from config import TYPEGG_GUILD_ID
from database.bot.users import get_user, get_user_by_user_id, link_if_free, link_user
from utils.logging import log_server
from web_server.utils import assign_user_roles, error_response, remove_user_roles, validate_authorization

if TYPE_CHECKING:
    from web_server.server import WebServer


async def link_account(cog: "WebServer", request: web.Request) -> web.Response:
    """Link a Discord ID to a TypeGG user ID and assign roles to a member (POST /link)."""
    auth_error = validate_authorization(request)
    if auth_error is not None:
        return auth_error

    try:
        data = await request.json()
    except JSONDecodeError:
        return error_response("Invalid JSON data.", 400)

    discord_id = str(data.get("discordId") or "")
    user_id = data.get("userId")
    mode = data.get("mode", "fill")

    if not discord_id.isdigit() or not user_id:
        return error_response("Missing required fields: discordId, userId.", 400)
    if mode not in ("fill", "override"):
        return error_response("Invalid mode.", 400)

    guild = cog.bot.get_guild(TYPEGG_GUILD_ID)

    if mode == "fill":
        status = link_if_free(discord_id, user_id)
    else:
        # link_user only updates, so a Discord ID the bot has never seen needs its row first.
        get_user(discord_id)
        superseded = link_user(discord_id, user_id)
        status = "linked"
        for old_discord_id in superseded:
            log_server(f"Unlinked user {old_discord_id} from user ID {user_id}, superseded by {discord_id}")
            if guild:
                await remove_user_roles(guild, int(old_discord_id))

    in_guild = bool(guild and guild.get_member(int(discord_id)))

    if status == "linked":
        log_server(f"Linked user {discord_id} to user ID {user_id} ({mode})")
        # A non-member gets their roles from on_member_join.
        if in_guild:
            try:
                await assign_user_roles(guild, int(discord_id), user_id)
            except Exception as e:
                log_server(f"Failed to assign roles to {discord_id}: {e}")

    # A conflict is an answer, not a failure, so the backend outbox does not retry it.
    return web.json_response({"status": status, "inGuild": in_guild})


async def link_status(cog: "WebServer", request: web.Request) -> web.Response:
    """Report the Discord account linked to a TypeGG user (GET /users/{userId}/link)."""
    auth_error = validate_authorization(request)
    if auth_error is not None:
        return auth_error

    user = get_user_by_user_id(request.match_info["userId"])
    if not user:
        return web.json_response({"linked": False, "discordId": None, "username": None, "inGuild": False})

    discord_id = int(user["discordId"])
    guild = cog.bot.get_guild(TYPEGG_GUILD_ID)
    member = guild.get_member(discord_id) if guild else None

    username = member.name if member else None
    if not username:
        discord_user = cog.bot.get_user(discord_id)
        if not discord_user:
            try:
                discord_user = await cog.bot.fetch_user(discord_id)
            except Exception:
                discord_user = None
        username = discord_user.name if discord_user else None

    return web.json_response({
        "linked": True,
        "discordId": str(discord_id),
        "username": username,
        "inGuild": member is not None,
    })
