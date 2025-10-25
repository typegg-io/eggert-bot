import re

import aiohttp
from discord.ext import tasks

from api.core import API_URL
from config import TYPEGG_GUILD_ID
from database.bot.users import get_all_linked_users
from utils import dates
from utils.logging import log, log_error


def setup_tasks(cog):
    """Attach background loops to the WebServer cog."""
    cog.token_cleanup_loop = token_cleanup_loop(cog)
    cog.nwpm_update_loop = nwpm_update_loop(cog)
    cog.token_cleanup_loop.start()
    cog.nwpm_update_loop.start()


def teardown_tasks(cog):
    """Cancel loops when cog unloads."""
    cog.token_cleanup_loop.cancel()
    cog.nwpm_update_loop.cancel()


def token_cleanup_loop(cog):
    """Cleanup expired tokens."""

    @tasks.loop(minutes=1)
    async def loop():
        now = dates.now()
        expired = [token for token, exp in cog.used_tokens.items() if exp < now]
        for t in expired:
            del cog.used_tokens[t]

    @loop.error
    async def on_error(error):
        log_error("Token Cleanup Error", error)

    return loop


def nwpm_update_loop(cog):
    """Update nWPM roles for all linked users using batched API calls."""

    @tasks.loop(hours=1)
    async def loop():
        guild = cog.bot.get_guild(TYPEGG_GUILD_ID)
        linked_users = get_all_linked_users()
        user_ids = list(linked_users.keys())
        log(f"Updating nWPM roles for {len(user_ids)} users")

        cog.nwpm_roles = [
            role for role in guild.roles
            if re.match(r"^\d{1,3}-\d{1,3}$|^250\+$", role.name)
        ]

        async with aiohttp.ClientSession() as session:
            async with session.post(f"{API_URL}/batch/user/nwpm", json={"user_ids": user_ids}) as resp:
                resp.raise_for_status()
                batch_data = await resp.json()

        for user_data in batch_data.get("users", []):
            user_id = user_data.get("user_id")
            nwpm = user_data.get("nwpm")
            discord_id = int(linked_users.get(str(user_id)))
            await cog.update_nwpm_role(guild, discord_id, nwpm)

        log("nWPM role update completed")

    @loop.error
    async def on_error(error):
        log_error("nWPM Update Error", error)

    return loop
