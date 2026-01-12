from datetime import datetime, timezone, timedelta

import aiohttp
import discord
import jwt
from discord.ext import commands

from commands.base import Command
from commands.checks import is_bot_admin
from config import SECRET
from database.bot.users import get_user
from utils.colors import SUCCESS, ERROR
from utils.logging import log
from utils.messages import Page, Message

info = {
    "name": "forcelink",
    "aliases": [],
    "description": "Force link a Discord user to a TypeGG account",
    "parameters": "<discord_user> <typegg_user_id>",
}


class ForceLink(Command):
    @commands.command(aliases=info["aliases"])
    @is_bot_admin()
    async def forcelink(self, ctx: commands.Context, user: discord.User, typegg_user_id: str):
        discord_id = str(user.id)
        get_user(discord_id)

        # Generate a JWT token for the verification endpoint
        expiry = datetime.now(timezone.utc) + timedelta(minutes=5)
        token = jwt.encode(
            {
                "discordId": discord_id,
                "userId": typegg_user_id,
                "exp": expiry.timestamp(),
            },
            SECRET,
            algorithm="HS256"
        )

        log(f"Admin {ctx.author.name} force-linking Discord user {user.name} ({discord_id}) to TypeGG user {typegg_user_id}")

        # Call the existing verify endpoint to handle linking and role assignment
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "http://localhost:8888/verify",
                    json={"token": token}
                ) as response:
                    if response.status == 200:
                        log(f"Force link successful for {user.name} ({discord_id})")
                        message = Message(ctx, Page(
                            title="Force Link Successful",
                            description=f"Successfully linked {user.mention} to TypeGG user `{typegg_user_id}` and assigned roles",
                            color=SUCCESS,
                        ))
                    else:
                        response_text = await response.text()
                        try:
                            import json
                            error_data = json.loads(response_text)
                            error_message = error_data.get("error", "Unknown error")
                        except:
                            error_message = response_text
                        log(f"Force link failed for {user.name} ({discord_id}): {error_message}")
                        message = Message(ctx, Page(
                            title="Force Link Failed",
                            description=f"Failed to link {user.mention}: {error_message}",
                            color=ERROR,
                        ))
        except aiohttp.ClientError as e:
            log(f"Error during forcelink for {user.name} ({discord_id}): {e}")
            message = Message(ctx, Page(
                title="Force Link Error",
                description=f"Failed to connect to verification service: {str(e)}",
                color=ERROR,
            ))

        await message.send()
