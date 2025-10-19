import asyncio
import re
from datetime import datetime, timezone

import aiohttp
import discord
import jwt
from aiohttp import web
from discord import Embed, Guild
from discord.ext import commands, tasks

from api.core import API_URL
from config import SECRET, TYPEGG_GUILD_ID, VERIFIED_ROLE_NAME
from database.bot.users import get_all_linked_users, link_user
from utils import dates
from utils.colors import SUCCESS
from utils.logging import log, log_error


class WebServer(commands.Cog):
    """Cog to manage the aiohttp web server and its background tasks."""

    def __init__(self, bot):
        self.bot = bot
        self.app = web.Application()
        self.runner = None
        self.site = None

        self.nwpm_roles = []
        self.used_tokens = {}
        self.role_pattern = re.compile(r"^\d{1,3}-\d{1,3}$|^250\+$")

        # Routes
        self.app.router.add_post("/verify", self.verify_user)

        # Background tasks
        self.token_cleanup_loop.start()
        self.nwpm_update_loop.start()

        # Web server
        self.bot.loop.create_task(self.start_web_server())

    async def cog_unload(self):
        await self.stop_web_server()

    ### Web Server ###

    async def start_web_server(self):
        """Start the web server."""
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, host="0.0.0.0", port=8888)
        await self.site.start()

        log("Web server started on port 8888")

    async def stop_web_server(self):
        """Stop the web server."""
        if self.runner:
            await self.runner.cleanup()

        log("Web server stopped")

    ### Background tasks ###

    @tasks.loop(minutes=1)
    async def token_cleanup_loop(self):
        """Cleanup expired tokens."""
        now = dates.now()
        expired_tokens = [token for token, exp in self.used_tokens.items() if exp < now]
        for token in expired_tokens:
            del self.used_tokens[token]

    @token_cleanup_loop.error
    async def token_cleanup_error(self, error):
        log_error("Token Cleanup Error", error)

    @tasks.loop(hours=1)
    async def nwpm_update_loop(self):
        """Update nWPM roles for all linked users using batched API calls."""
        guild = self.bot.get_guild(TYPEGG_GUILD_ID)
        linked_users = get_all_linked_users()
        user_ids = list(linked_users.keys())
        log(f"Updating nWPM roles for {len(user_ids)} users")

        self.nwpm_roles = [role for role in guild.roles if self.role_pattern.match(role.name)]

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{API_URL}/batch/user/nwpm",
                json={"user_ids": user_ids}
            ) as response:
                response.raise_for_status()

                batch_data = await response.json()

                for user_data in batch_data.get("users", []):
                    user_id = user_data.get("user_id")
                    nwpm = user_data.get("nwpm")
                    discord_id = int(linked_users.get(str(user_id)))
                    await self.update_nwpm_role(guild, discord_id, nwpm)

                log(f"nWPM role update completed")

    @nwpm_update_loop.error
    async def nwpm_update_error(self, error):
        log_error("nWPM Update Error", error)

    ### Utilities ###

    @staticmethod
    def get_nwpm_role_name(nwpm):
        """Get the role name for a given nWPM value."""
        if nwpm is None:
            return None
        if nwpm >= 250:
            return "250+"
        lower_bound = int((nwpm // 10) * 10)
        upper_bound = lower_bound + 9
        return f"{lower_bound}-{upper_bound}"

    async def update_nwpm_role(self, guild: Guild, discord_id: int, nwpm: float):
        """Update a given user's nWPM role."""
        member = guild.get_member(discord_id)
        if not member:
            return

        role_name = self.get_nwpm_role_name(nwpm)
        if not role_name:
            return

        new_role = discord.utils.get(guild.roles, name=role_name)
        current_roles = [role for role in member.roles if role in self.nwpm_roles]

        if len(current_roles) == 1 and current_roles[0] == new_role:
            return

        if current_roles:
            await member.remove_roles(*current_roles, reason="Updating nWPM role")
            await asyncio.sleep(0.5)

        await member.add_roles(new_role, reason="Assigning nWPM role")
        log(f"Assigned {role_name} role to {member.name}")
        await asyncio.sleep(1)

    ### Route Handlers ###

    async def verify_user(self, request: web.Request):
        data = await request.json()
        token = data.get("token")

        if not token:
            return web.json_response({"error": "Token is required."}, status=400)

        if token in self.used_tokens:
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
        self.used_tokens[token] = expiry_date

        guild = self.bot.get_guild(TYPEGG_GUILD_ID)
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

        user = await self.bot.fetch_user(discord_id)
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
                await self.update_nwpm_role(guild, discord_id, nwpm)

        return web.json_response({"success": True, "message": "User verified successfully."})


async def setup(bot):
    await bot.add_cog(WebServer(bot))
