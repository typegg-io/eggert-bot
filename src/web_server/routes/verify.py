from datetime import datetime, timezone

import aiohttp
import discord
import jwt
from aiohttp import web
from discord import Embed, Forbidden

from api.core import API_URL
from config import SECRET, TYPEGG_GUILD_ID, VERIFIED_ROLE_NAME
from database.bot.users import link_user
from utils.colors import SUCCESS
from utils.logging import log
from web_server.utils import update_nwpm_role, error_response


async def verify_user(cog, request: web.Request):
    data = await request.json()
    token = data.get("token")

    if not token:
        return error_response("Token is required.", 400)

    if token in cog.used_tokens:
        return error_response("Token already invalidated.", 401)

    try:
        decoded_token = jwt.decode(token, SECRET, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        return error_response("Token has expired.", 401)
    except jwt.InvalidTokenError:
        return error_response("Token is invalid.", 401)

    discord_id = int(decoded_token.get("discordId"))
    user_id = decoded_token.get("userId")
    expiry_timestamp = decoded_token.get("exp")

    if not (discord_id and user_id and expiry_timestamp):
        return error_response("Invalid token payload.", 400)

    guild = cog.bot.get_guild(TYPEGG_GUILD_ID)
    if not guild:
        return error_response("Guild not found.", 500)

    member = guild.get_member(int(discord_id))
    if not member:
        return error_response("User not found in server.", 404)

    role = discord.utils.get(guild.roles, name=VERIFIED_ROLE_NAME)
    if not role:
        return error_response("Verification role not found.", 500)

    # Assign verified role
    try:
        await member.add_roles(role)
        log(f"Assigned '{VERIFIED_ROLE_NAME}' role to {member.name}")
    except (Forbidden, discord.HTTPException) as e:
        return error_response(f"Failed to assign verification role: {e}", 500)

    # Link user in database
    link_user(discord_id, user_id)
    log(f"Linked user {discord_id} to user ID {user_id}")

    # Send success DM
    user = await cog.bot.fetch_user(discord_id)
    try:
        await user.send(embed=Embed(
            title="Verification Successful",
            description="Successfully verified your account.",
            color=SUCCESS,
        ))
        log(f"Sent verification success message to {user.name}")
    except Forbidden:
        pass

    # Fetch and assign nWPM role
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{API_URL}/user/{user_id}/nwpm") as response:
                if response.status == 200:
                    data = await response.json()
                    nwpm = data.get("nwpm")
                    await update_nwpm_role(cog, guild, discord_id, nwpm)
                else:
                    log(f"Failed to fetch nWPM for user {user_id}: HTTP {response.status}")
        except Exception as e:
            log(f"Error fetching nWPM for user {user_id}: {e}")

        # Fetch GG+ status and assign role if applicable
        try:
            async with session.get(f"{API_URL}/v1/users/{user_id}") as response:
                if response.status == 200:
                    profile_data = await response.json()
                    is_gg_plus = profile_data.get("isGgPlus", False)

                    if is_gg_plus:
                        gg_plus_role = discord.utils.get(guild.roles, name="GG+")
                        if gg_plus_role:
                            try:
                                await member.add_roles(gg_plus_role)
                                log(f"Assigned GG+ role to {member.name}")
                            except (Forbidden, discord.HTTPException) as e:
                                log(f"Failed to assign GG+ role to {member.name}: {e}")
                        else:
                            log("GG+ role not found in guild")
                else:
                    log(f"Failed to fetch profile for user {user_id}: HTTP {response.status}")
        except Exception as e:
            log(f"Error fetching profile for user {user_id}: {e}")

    # Invalidate token
    expiry_date = datetime.fromtimestamp(expiry_timestamp, timezone.utc)
    cog.used_tokens[token] = expiry_date

    return web.json_response({"success": True, "message": "User verified successfully."})
