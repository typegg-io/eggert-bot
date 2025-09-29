import asyncio
from datetime import datetime, timezone

import aiohttp
import discord
import jwt
from aiohttp import web
from discord import Embed

from config import API_URL, SECRET, TYPEGG_GUILD_ID, VERIFIED_ROLE_NAME
from database.bot.users import get_all_linked_users, link_user
from utils.logging import log

used_tokens = {}

app = web.Application()


def get_nwpm_role_name(nwpm):
    """Get the role name for a given nWPM value."""
    if nwpm is None:
        return None

    if nwpm >= 250:
        return "250+"

    lower_bound = int((nwpm // 10) * 10)
    upper_bound = lower_bound + 9
    return f"{lower_bound}-{upper_bound}"


async def token_cleanup_task():
    """Periodic cleanup of expired tokens."""
    while True:
        now = datetime.now(timezone.utc)
        expired_tokens = [token for token, exp in used_tokens.items() if exp < now]
        for token in expired_tokens:
            del used_tokens[token]
        await asyncio.sleep(60)


async def check_and_assign_nwpm_role(bot, discord_id, user_id):
    """Check user's nWPM and assign appropriate role."""
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{API_URL}/user/{user_id}/nwpm") as response:
            if response.status != 200:
                log(f"Failed to get nWPM for user {discord_id}: HTTP {response.status}")
                return

            data = await response.json()
            nwpm = data.get("nwpm")

            if nwpm is None:
                return

            guild = bot.get_guild(TYPEGG_GUILD_ID)
            if not guild:
                log(f"Guild with ID {TYPEGG_GUILD_ID} not found")
                return

            member = guild.get_member(int(discord_id))
            if not member:
                log(f"User {user_id} with ID {discord_id} not found in guild {guild.name}")
                return

            role_name = get_nwpm_role_name(nwpm)
            if not role_name:
                log(f"No valid role name for nWPM {nwpm}")
                return

            new_role = discord.utils.get(guild.roles, name=role_name)
            if not new_role:
                log(f"Role '{role_name}' not found in guild {guild.name}")
                return

            all_nwpm_roles = [
                role for role in guild.roles
                if (("-" in role.name and any(c.isdigit() for c in role.name)) or role.name == "250+")
            ]

            current_nwpm_roles = [role for role in member.roles if role in all_nwpm_roles]

            if len(current_nwpm_roles) == 1 and current_nwpm_roles[0] == new_role:
                log(f"User {member.name} already has the correct nWPM role {role_name}")
                return

            if current_nwpm_roles:
                current_role_names = [role.name for role in current_nwpm_roles]
                await member.remove_roles(*current_nwpm_roles, reason="Updating nWPM role")
                log(f"Removed nWPM roles {', '.join(current_role_names)} from {member.name}")
                await asyncio.sleep(0.5)

            await member.add_roles(new_role, reason="Assigning nWPM role")
            log(f"Assigned nWPM role {role_name} to user {member.name} (nWPM: {nwpm})")


async def update_nwpm_roles(bot):
    """Periodic task to update nWPM roles for all linked users using batched API calls."""
    while True:
        log("Starting nWPM role update...")
        guild = bot.get_guild(TYPEGG_GUILD_ID)
        if not guild:
            log(f"Guild with ID {TYPEGG_GUILD_ID} not found. Retrying in 60 minutes.")
            await asyncio.sleep(3600)
            continue

        linked_users = get_all_linked_users()
        if not linked_users:
            log("No linked users found. Retrying in 60 minutes.")
            await asyncio.sleep(3600)
            continue

        user_id_to_discord_id = {str(user_id): str(discord_id) for discord_id, user_id in linked_users}
        user_ids = [str(user_id) for _, user_id in linked_users]

        log(f"Updating nWPM roles for {len(user_ids)} users")

        all_nwpm_roles = [
            role for role in guild.roles
            if (("-" in role.name and any(c.isdigit() for c in role.name)) or role.name == "250+")
        ]

        if not all_nwpm_roles:
            log("ERROR: No nWPM roles found in the guild. Please create the necessary roles (0-9, 10-19, etc., and 250+)")
            await asyncio.sleep(3600)
            continue

        log(f"Found {len(all_nwpm_roles)} nWPM roles: {', '.join(role.name for role in all_nwpm_roles)}")

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{API_URL}/batch/user/nwpm",
                json={"user_ids": user_ids}
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    log(f"Batch API request failed with status {response.status}: {error_text}")
                    await asyncio.sleep(3600)
                    continue

                batch_data = await response.json()
                users_updated = 0
                users_skipped = 0
                users_not_found = 0
                role_errors = 0

                for user_data in batch_data.get("users", []):
                    user_id = user_data.get("user_id")
                    nwpm = user_data.get("nwpm")

                    if not user_id or nwpm is None:
                        users_skipped += 1
                        continue

                    discord_id = user_id_to_discord_id.get(str(user_id))
                    if not discord_id:
                        log(f"Could not find discord_id for user_id {user_id}")
                        users_not_found += 1
                        continue

                    member = guild.get_member(int(discord_id))
                    if not member:
                        users_not_found += 1
                        continue

                    role_name = get_nwpm_role_name(nwpm)
                    if not role_name:
                        users_skipped += 1
                        continue

                    new_role = discord.utils.get(guild.roles, name=role_name)
                    if not new_role:
                        log(f"Role '{role_name}' not found in guild - cannot assign to {member.name}")
                        role_errors += 1
                        continue

                    current_nwpm_roles = [role for role in member.roles if role in all_nwpm_roles]

                    if len(current_nwpm_roles) == 1 and current_nwpm_roles[0] == new_role:
                        log(f"User {member.name} already has the correct nWPM role {role_name}")
                        users_skipped += 1
                        continue

                    if not current_nwpm_roles:
                        log(f"User {member.name} has no nWPM role, adding {role_name}")
                    elif len(current_nwpm_roles) == 1:
                        log(f"User {member.name} has role {current_nwpm_roles[0].name}, changing to {role_name}")
                    else:
                        log(f"User {member.name} has multiple nWPM roles {', '.join(r.name for r in current_nwpm_roles)}, fixing to only {role_name}")

                    if current_nwpm_roles:
                        await member.remove_roles(*current_nwpm_roles, reason="Updating nWPM role")
                        await asyncio.sleep(0.5)

                    await member.add_roles(new_role, reason="Assigning nWPM role")
                    log(f"Successfully updated {member.name}'s nWPM role to {role_name} (nWPM: {nwpm})")
                    users_updated += 1

                    await asyncio.sleep(1)

                log(f"nWPM role update completed: {users_updated} updated, {users_skipped} skipped, {users_not_found} not found, {role_errors} role errors")

        log(f"Next nWPM role update in 60 minutes")
        await asyncio.sleep(3600)


async def verify_user(request: web.Request):
    """Handle user verification via JWT token."""
    data = await request.json()
    token = data.get("token")

    if not token:
        return web.json_response({"error": "Token is required."}, status=400)

    if token in used_tokens:
        return web.json_response({"error": "Token already invalidated."}, status=401)

    try:
        decoded_token = jwt.decode(token, SECRET, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        return web.json_response({"error": "Token has expired."}, status=401)
    except jwt.InvalidTokenError:
        return web.json_response({"error": "Token is invalid."}, status=401)

    discord_id = decoded_token.get("discordId")
    user_id = decoded_token.get("userId")
    expiry_timestamp = decoded_token.get("exp")

    if not (discord_id and user_id and expiry_timestamp):
        return web.json_response({"error": "Invalid token payload."}, status=400)

    expiry_dt = datetime.fromtimestamp(expiry_timestamp, timezone.utc)
    used_tokens[token] = expiry_dt

    guild = app["bot"].get_guild(TYPEGG_GUILD_ID)
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

    user = await app["bot"].fetch_user(discord_id)
    await user.send(embed=Embed(
        title="Verification Successful",
        description="Successfully verified your account.",
        color=1673044,
    ))
    log(f"Sent verification success message to {user.name}")

    asyncio.create_task(check_and_assign_nwpm_role(app["bot"], discord_id, user_id))

    return web.json_response({"success": True, "message": "User verified successfully."})


async def start_web_server(bot):
    """Start the web server and background tasks."""
    app["bot"] = bot

    cleanup_task = asyncio.create_task(token_cleanup_task())
    log("Token cleanup task started")

    nwpm_task = asyncio.create_task(update_nwpm_roles(bot))
    log("nWPM role update task started")

    app["background_tasks"] = [cleanup_task, nwpm_task]

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=8888)
    await site.start()
    log("Web server started on port 8888")


app.router.add_post("/verify", verify_user)
