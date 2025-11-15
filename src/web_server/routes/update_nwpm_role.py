from json import JSONDecodeError

import discord
from aiohttp import web

from config import SECRET
from database.bot.users import get_discord_id
from utils.logging import log


def get_nwpm_role_name(nwpm):
    """Get the role name for a given nWPM value."""
    if nwpm is None:
        return None
    if nwpm >= 250:
        return "250+"
    lower_bound = int((nwpm // 10) * 10)
    upper_bound = lower_bound + 9
    return f"{lower_bound}-{upper_bound}"


async def update_nwpm_role(cog, request: web.Request):
    """Update a given user's nWPM role."""

    def error(message: str, status: int = 500):
        return web.json_response({"error": message}, status=status)

    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return error("Missing Authorization header.", 401)

    token = auth_header.removeprefix("Bearer ").strip()
    if token != SECRET:
        return error("Token is invalid.", 401)

    try:
        data = await request.json()
    except JSONDecodeError:
        return error("Invalid JSON data.", 400)

    user_id = data.get("userId")
    nwpm = data.get("nWpm")

    discord_id = get_discord_id(user_id)
    if not discord_id:
        return error("User not verified.", 401)

    guild = cog.guild
    member = guild.get_member(int(discord_id))
    if not member:
        return error("User not found in guild.", 404)

    role_name = get_nwpm_role_name(nwpm)
    if not role_name:
        return error("nWPM role not found.", 404)

    new_role = discord.utils.get(guild.roles, name=role_name)
    current_roles = [role for role in member.roles if role in cog.nwpm_roles]

    await member.remove_roles(*current_roles, reason="Updating nWPM role")
    await member.add_roles(new_role, reason="Assigning nWPM role")

    log(f"Assigned {role_name} role to {member.name}")

    return web.json_response({"success": True, "message": "Updated user's nWPM role successfully."})
