from json import JSONDecodeError

import discord
from aiohttp import web

from database.bot.users import get_discord_id
from utils.logging import log_server
from web_server.utils import validate_authorization, error_response, get_nwpm_role_name


async def update_nwpm_role(cog, request: web.Request):
    """Update a given user's nWPM role."""

    # Verify authorization
    auth_error = validate_authorization(request)
    if auth_error:
        return auth_error

    # Parse request data
    try:
        data = await request.json()
    except JSONDecodeError:
        return error_response("Invalid JSON data.", 400)

    user_id = data.get("userId")
    nwpm = data.get("nWpm")

    discord_id = get_discord_id(user_id)
    if not discord_id:
        return error_response("User not verified.", 401)

    guild = cog.guild
    member = guild.get_member(int(discord_id))
    if not member:
        return error_response("User not found in guild.", 404)

    role_name = get_nwpm_role_name(nwpm)
    if not role_name:
        return error_response("nWPM role not found.", 404)

    new_role = discord.utils.get(guild.roles, name=role_name)
    current_roles = [role for role in member.roles if role in cog.nwpm_roles]

    await member.remove_roles(*current_roles, reason="Updating nWPM role")
    await member.add_roles(new_role, reason="Assigning nWPM role")

    log_server(f"Assigned {role_name} role to {member.name}")

    return web.json_response({"success": True, "message": "Updated user's nWPM role successfully."})
