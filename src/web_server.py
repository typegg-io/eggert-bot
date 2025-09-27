import asyncio
import discord
import jwt
import aiohttp
from aiohttp import web
from datetime import datetime, timezone
from discord import Embed

from config import API_URL, SECRET, TYPEGG_GUILD_ID, VERIFIED_ROLE_NAME
from database.bot.users import get_all_linked_users

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
        try:
            now = datetime.now(timezone.utc)
            expired_tokens = [token for token, exp in used_tokens.items() if exp < now]
            for token in expired_tokens:
                del used_tokens[token]
            await asyncio.sleep(60)
        except Exception as e:
            print(f"Error in token cleanup task: {e}")
            await asyncio.sleep(60)

async def check_and_assign_nwpm_role(bot, discord_id, user_id):
    """Check user's nWPM and assign appropriate role."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{API_URL}/user/{user_id}/nwpm") as response:
                if response.status == 200:
                    data = await response.json()
                    nwpm = data.get("nwpm")

                    if nwpm is not None:
                        guild = bot.get_guild(TYPEGG_GUILD_ID)
                        if not guild:
                            print(f"Guild with ID {TYPEGG_GUILD_ID} not found")
                            return

                        member = guild.get_member(int(discord_id))
                        if not member:
                            print(f"User {user_id} with ID {discord_id} not found in guild {guild.name}")
                            return

                        role_name = get_nwpm_role_name(nwpm)
                        if not role_name:
                            print(f"No valid role name for nWPM {nwpm}")
                            return

                        new_role = discord.utils.get(guild.roles, name=role_name)
                        if not new_role:
                            print(f"Role '{role_name}' not found in guild {guild.name}")
                            return

                        all_nwpm_roles = [
                            role for role in guild.roles
                            if (("-" in role.name and any(c.isdigit() for c in role.name)) or role.name == "250+")
                        ]

                        current_nwpm_roles = []
                        for role in member.roles:
                            if role in all_nwpm_roles:
                                current_nwpm_roles.append(role)

                        if len(current_nwpm_roles) == 1 and current_nwpm_roles[0] == new_role:
                            print(f"User {member.name} already has the correct nWPM role {role_name}")
                            return

                        if current_nwpm_roles:
                            current_role_names = [role.name for role in current_nwpm_roles]
                            await member.remove_roles(*current_nwpm_roles, reason="Updating nWPM role")
                            print(f"Removed nWPM roles {', '.join(current_role_names)} from {member.name}")
                            await asyncio.sleep(0.5)

                        await member.add_roles(new_role, reason="Assigning nWPM role")
                        print(f"Assigned nWPM role {role_name} to user {member.name} (nWPM: {nwpm})")
                else:
                    print(f"Failed to get nWPM for user {discord_id}: HTTP {response.status}")
                    error_text = await response.text()
                    print(f"Error details: {error_text}")
    except discord.errors.Forbidden as e:
        print(f"Permission error assigning nWPM role: {e}")
    except Exception as e:
        print(f"Error assigning nWPM role: {e}")

async def update_nwpm_roles(bot):
    """Periodic task to update nWPM roles for all linked users using batched API calls."""
    while True:
        try:
            print("Starting nWPM role update...")
            guild = bot.get_guild(TYPEGG_GUILD_ID)
            if not guild:
                print(f"Guild with ID {TYPEGG_GUILD_ID} not found. Retrying in 60 minutes.")
                await asyncio.sleep(3600)
                continue

            linked_users = get_all_linked_users()

            if not linked_users:
                print("No linked users found. Retrying in 60 minutes.")
                await asyncio.sleep(3600)
                continue

            user_id_to_discord_id = {str(user_id): str(discord_id) for discord_id, user_id in linked_users}

            user_ids = [str(user_id) for _, user_id in linked_users]

            print(f"Updating nWPM roles for {len(user_ids)} users")

            all_nwpm_roles = [
                role for role in guild.roles
                if (("-" in role.name and any(c.isdigit() for c in role.name)) or role.name == "250+")
            ]

            if not all_nwpm_roles:
                print("ERROR: No nWPM roles found in the guild. Please create the necessary roles (0-9, 10-19, etc., and 250+)")
                await asyncio.sleep(3600)
                continue

            print(f"Found {len(all_nwpm_roles)} nWPM roles: {', '.join(role.name for role in all_nwpm_roles)}")

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{API_URL}/batch/user/nwpm",
                    json={"user_ids": user_ids}
                ) as response:
                    if response.status == 200:
                        batch_data = await response.json()
                        users_updated = 0
                        users_skipped = 0
                        users_not_found = 0
                        role_errors = 0

                        for user_data in batch_data.get("users", []):
                            try:
                                user_id = user_data.get("user_id")
                                nwpm = user_data.get("nwpm")

                                if not user_id or nwpm is None:
                                    users_skipped += 1
                                    continue

                                discord_id = user_id_to_discord_id.get(str(user_id))
                                if not discord_id:
                                    print(f"Could not find discord_id for user_id {user_id}")
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
                                    print(f"Role '{role_name}' not found in guild - cannot assign to {member.name}")
                                    role_errors += 1
                                    continue

                                current_nwpm_roles = [role for role in member.roles if role in all_nwpm_roles]

                                if len(current_nwpm_roles) == 1 and current_nwpm_roles[0] == new_role:
                                    print(f"User {member.name} already has the correct nWPM role {role_name}")
                                    users_skipped += 1
                                    continue

                                if not current_nwpm_roles:
                                    print(f"User {member.name} has no nWPM role, adding {role_name}")
                                elif len(current_nwpm_roles) == 1:
                                    print(f"User {member.name} has role {current_nwpm_roles[0].name}, changing to {role_name}")
                                else:
                                    print(f"User {member.name} has multiple nWPM roles {', '.join(r.name for r in current_nwpm_roles)}, fixing to only {role_name}")

                                if current_nwpm_roles:
                                    await member.remove_roles(*current_nwpm_roles, reason="Updating nWPM role")
                                    await asyncio.sleep(0.5)

                                await member.add_roles(new_role, reason="Assigning nWPM role")
                                print(f"Successfully updated {member.name}'s nWPM role to {role_name} (nWPM: {nwpm})")
                                users_updated += 1

                                await asyncio.sleep(1)

                            except discord.errors.Forbidden as e:
                                print(f"Permission error updating roles: {e}")
                            except Exception as e:
                                print(f"Error processing user {user_id}: {e}") # type: ignore

                        print(f"nWPM role update completed: {users_updated} updated, {users_skipped} skipped, {users_not_found} not found, {role_errors} role errors")
                    else:
                        error_text = await response.text()
                        print(f"Batch API request failed with status {response.status}: {error_text}")

        except Exception as e:
            print(f"Error updating nWPM roles: {e}")

        print(f"Next nWPM role update in 60 minutes")
        await asyncio.sleep(3600)

async def verify_user(request: web.Request):
    """Handle user verification via JWT token."""
    try:
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

        if member:
            role = discord.utils.get(guild.roles, name=VERIFIED_ROLE_NAME)
            if role:
                try:
                    await member.add_roles(role)
                    print(f"Assigned verifiedegg role to {member.name}")
                except discord.errors.Forbidden:
                    return web.json_response({"error": "Bot lacks permission to assign roles."}, status=500)
                except Exception as e:
                    print(f"Error assigning verified role: {e}")
                    return web.json_response({"error": "Failed to assign role."}, status=500)
            else:
                print(f"'{VERIFIED_ROLE_NAME}' role not found in guild {guild.name}")
                return web.json_response({"error": "Verification role not found."}, status=500)

            try:
                users.link_user(discord_id, user_id)
                print(f"Linked user {discord_id} to user ID {user_id}")
            except Exception as e:
                print(f"Database error linking user: {e}")
                return web.json_response({"error": "Failed to link user in database."}, status=500)

            try:
                user = await app["bot"].fetch_user(discord_id)
                await user.send(embed=Embed(
                    title="Verification Successful",
                    description="Successfully verified your account.",
                    color=1673044,
                ))
                print(f"Sent verification success message to {user.name}")
            except Exception as e:
                print(f"Error sending verification message: {e}")

            asyncio.create_task(check_and_assign_nwpm_role(app["bot"], discord_id, user_id))

            return web.json_response({"success": True, "message": "User verified successfully."})
        else:
            return web.json_response({"error": "User not found in server."}, status=404)

    except Exception as e:
        print(f"Server Error in verify_user: {e}")
        return web.json_response({"error": "Internal server error."}, status=500)

async def start_web_server(bot):
    """Start the web server and background tasks."""
    app["bot"] = bot

    cleanup_task = asyncio.create_task(token_cleanup_task())
    print("Token cleanup task started")

    nwpm_task = asyncio.create_task(update_nwpm_roles(bot))
    print("nWPM role update task started")

    app["background_tasks"] = [cleanup_task, nwpm_task]

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=8888)
    await site.start()
    print("Web server started on port 8888")

app.router.add_post("/verify", verify_user)
