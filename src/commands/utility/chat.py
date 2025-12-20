import aiohttp
from discord.ext import commands

from commands.base import Command
from config import CHATBOT_WEBHOOK_URL, SECRET
from utils.colors import ERROR
from utils.errors import NotSubscribed
from utils.messages import Message, Page, usable_in
from utils.strings import EGGERT

info = {
    "name": "chat",
    "aliases": ["ask", "ai"],
    "description": "Ask Eggert a question about TypeGG or the bot",
    "parameters": "[question]",
}


class Chat(Command):
    @commands.command(aliases=info["aliases"])
    @usable_in(1397687954117361745)
    async def chat(self, ctx, *, question: str = None):
        if not ctx.user["isGgPlus"]:
            raise NotSubscribed("AI chat")

        if not question:
            return await ctx.send(content=f"Hello {EGGERT} If you have any questions, just ask!")

        if not CHATBOT_WEBHOOK_URL:
            message = Message(ctx, Page(
                description="Chatbot is not configured.",
                color=ERROR,
            ))
            return await message.send()

        async with ctx.typing():
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        CHATBOT_WEBHOOK_URL,
                        json={
                            "chatInput": question,
                            "sessionId": ctx.author.id,
                        },
                        headers={"Authorization": f"Bearer {SECRET}"},
                        timeout=aiohttp.ClientTimeout(total=30)
                    ) as response:
                        if response.status != 200:
                            message = Message(ctx, Page(
                                description=f"Error: Failed to get response (Status {response.status})",
                                color=ERROR,
                            ))
                            return await message.send()

                        data = await response.json()
                        output = data.get("output")
                        await ctx.message.reply(output, mention_author=False)

            except aiohttp.ClientError:
                message = Message(ctx, Page(
                    description=f"Error: Failed to connect to chatbot service.",
                    color=ERROR,
                ))
                await message.send()
