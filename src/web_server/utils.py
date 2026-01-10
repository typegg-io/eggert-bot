import asyncio

import discord
from aiohttp import web

from config import SECRET
from utils.logging import log


# Request Utilities

def error_response(message: str, status: int = 500):
    """Create a JSON error response."""
    log(f"Error response ({status}): {message}")
    return web.json_response({"error": message}, status=status)


def validate_authorization(request: web.Request):
    """Validate the Authorization header with Bearer token, returns error response or None."""
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return error_response("Missing Authorization header.", 401)

    token = auth_header.removeprefix("Bearer ").strip()
    if token != SECRET:
        return error_response("Token is invalid.", 401)

    return None


# Discord Role Management

def get_nwpm_role_name(nwpm):
    """Get the role name for a given nWPM value."""
    if nwpm is None:
        return None
    if nwpm >= 250:
        return "250+"
    lower_bound = int((nwpm // 10) * 10)
    upper_bound = lower_bound + 9
    return f"{lower_bound}-{upper_bound}"


async def update_nwpm_role(cog, guild: discord.Guild, discord_id: int, nwpm: float):
    """Update a given user's nWPM role."""
    member = guild.get_member(discord_id)
    if not member:
        raise ValueError(f"Member with ID {discord_id} not found in guild")

    role_name = get_nwpm_role_name(nwpm)
    if not role_name:
        log(f"No nWPM role needed for nwpm={nwpm}")
        return

    new_role = discord.utils.get(guild.roles, name=role_name)
    if not new_role:
        raise ValueError(f"nWPM role '{role_name}' not found in guild")

    current_roles = [role for role in member.roles if role in cog.nwpm_roles]

    if len(current_roles) == 1 and current_roles[0] == new_role:
        log(f"Member {member.name} already has correct nWPM role '{role_name}'")
        return

    try:
        if current_roles:
            await member.remove_roles(*current_roles, reason="Updating nWPM role")
            await asyncio.sleep(0.5)

        await member.add_roles(new_role, reason="Assigning nWPM role")
        log(f"Assigned {role_name} role to {member.name}")
        await asyncio.sleep(1)
    except (discord.Forbidden, discord.HTTPException) as e:
        raise RuntimeError(f"Failed to update nWPM role for {member.name}: {e}")
