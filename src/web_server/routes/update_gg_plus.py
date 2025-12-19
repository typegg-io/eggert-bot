from json import JSONDecodeError

import discord
from aiohttp import web

from database.bot.users import update_gg_plus_status, get_discord_id, update_theme
from utils.colors import GG_PLUS_THEME
from utils.logging import log
from web_server.utils import validate_authorization, error_response


async def update_gg_plus(cog, request: web.Request):
    """Update a user's GG+ subscription status in the database."""

    auth_error = validate_authorization(request)
    if auth_error:
        return auth_error

    try:
        data = await request.json()
    except JSONDecodeError:
        return error_response("Invalid JSON data.", 400)

    user_id = data.get("userId")
    is_gg_plus = data.get("isGgPlus")

    # Validate required fields
    if not user_id:
        return error_response("Missing required field: userId.", 400)

    if is_gg_plus is None:
        return error_response("Missing required field: isGgPlus.", 400)

    if not isinstance(is_gg_plus, bool):
        return error_response("Field 'isGgPlus' must be a boolean.", 400)

    # Check if user exists
    discord_id = get_discord_id(user_id)
    if not discord_id:
        return error_response("User not found or not linked.", 404)

    # Update GG+ status
    update_gg_plus_status(user_id, is_gg_plus)

    # Update theme
    update_theme(discord_id, GG_PLUS_THEME)

    status_text = "subscribed to" if is_gg_plus else "unsubscribed from"
    log(f"User {user_id} (<@{discord_id}>) {status_text} GG+")

    # Update GG+ role
    guild = cog.guild
    member = guild.get_member(int(discord_id))

    if member:
        role = discord.utils.get(guild.roles, name="GG+")

        if is_gg_plus:
            await member.add_roles(role, reason="Assigning GG+ role")
        else:
            await member.remove_roles(role, reason="Removing GG+ role")

        log(f"Assigned GG+ role to {member.name}")

    return web.json_response({
        "success": True,
        "message": "Updated GG+ status successfully.",
    })
