import discord
import jwt
from aiohttp import web

from config import TYPEGG_GUILD_ID, SECRET
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
    data = await request.json()
    token = data.get("token")

    if not token:
        return web.json_response({"error": "Token is required."}, status=400)

    if token in cog.used_tokens:
        return web.json_response({"error": "Token already invalidated."}, status=401)

    try:
        decoded_token = jwt.decode(token, SECRET, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        return web.json_response({"error": "Token has expired."}, status=401)
    except jwt.InvalidTokenError:
        return web.json_response({"error": "Token is invalid."}, status=401)
    user_id = decoded_token.get("userId")
    nwpm = decoded_token.get("nWpm")
    discord_id = get_discord_id(user_id)

    guild = cog.bot.get_guild(TYPEGG_GUILD_ID)
    if not guild:
        return web.json_response({"error": "Guild not found."}, status=500)

    member = guild.get_member(int(discord_id))
    if not member:
        return web.json_response({"error": "User not found in server."}, status=404)

    role_name = get_nwpm_role_name(nwpm)
    if not role_name:
        return web.json_response({"error": "nWPM role not found."}, status=404)

    new_role = discord.utils.get(guild.roles, name=role_name)
    current_roles = [role for role in member.roles if role in cog.nwpm_roles]
    await member.remove_roles(*current_roles, reason="Updating nWPM role")

    await member.add_roles(new_role, reason="Assigning nWPM role")
    log(f"Assigned {role_name} role to {member.name}")

    return web.json_response({"success": True, "message": "Updated user's nWPM role successfully."})
