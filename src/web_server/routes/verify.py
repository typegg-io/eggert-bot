from datetime import datetime, timezone

import jwt
from aiohttp import web
from discord import Embed, Forbidden

from config import SECRET, TYPEGG_GUILD_ID
from database.bot.users import link_user
from utils.colors import SUCCESS
from utils.logging import log
from web_server.utils import assign_user_roles, error_response


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

    # Link user in database
    link_user(discord_id, user_id)
    log(f"Linked user {discord_id} to user ID {user_id}")

    # Assign all roles (verified, nWPM, GG+) and update database
    try:
        await assign_user_roles(cog, guild, discord_id, user_id)
    except Exception as e:
        return error_response(str(e), 500)

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

    # Invalidate token
    expiry_date = datetime.fromtimestamp(expiry_timestamp, timezone.utc)
    cog.used_tokens[token] = expiry_date

    return web.json_response({"success": True, "message": "User verified successfully."})
