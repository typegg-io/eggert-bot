from datetime import datetime, timezone

import aiohttp
import discord
import jwt
from aiohttp import web
from discord import Embed

from api.core import API_URL
from config import SECRET, TYPEGG_GUILD_ID, VERIFIED_ROLE_NAME
from database.bot.users import link_user
from utils.colors import SUCCESS
from utils.logging import log
from web_server.utils import update_nwpm_role


async def verify_user(cog, request: web.Request):
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

    discord_id = int(decoded_token.get("discordId"))
    user_id = decoded_token.get("userId")
    expiry_timestamp = decoded_token.get("exp")

    if not (discord_id and user_id and expiry_timestamp):
        return web.json_response({"error": "Invalid token payload."}, status=400)

    expiry_date = datetime.fromtimestamp(expiry_timestamp, timezone.utc)
    cog.used_tokens[token] = expiry_date

    guild = cog.bot.get_guild(TYPEGG_GUILD_ID)
    if not guild:
        return web.json_response({"error": "Guild not found."}, status=500)

    member = guild.get_member(int(discord_id))
    if not member:
        return web.json_response({"error": "User not found in server."}, status=404)

    role = discord.utils.get(guild.roles, name=VERIFIED_ROLE_NAME)
    if not role:
        log(f"'{VERIFIED_ROLE_NAME}' role not found in guild {guild.name}")
        return web.json_response({"error": "Verification role not found."}, status=500)

    await member.add_roles(role)
    log(f"Assigned '{VERIFIED_ROLE_NAME}' role to {member.name}")

    link_user(discord_id, user_id)
    log(f"Linked user {discord_id} to user ID {user_id}")

    user = await cog.bot.fetch_user(discord_id)
    await user.send(embed=Embed(
        title="Verification Successful",
        description="Successfully verified your account.",
        color=SUCCESS,
    ))
    log(f"Sent verification success message to {user.name}")

    async with aiohttp.ClientSession() as session:
        async with session.get(f"{API_URL}/user/{user_id}/nwpm") as response:
            response.raise_for_status()

            data = await response.json()
            nwpm = data.get("nwpm")
            await update_nwpm_role(cog, guild, discord_id, nwpm)

    return web.json_response({"success": True, "message": "User verified successfully."})
