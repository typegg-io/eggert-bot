from collections import OrderedDict

import anthropic
from discord.ext import commands

from commands.base import Command
from config import ANTHROPIC_API_KEY
from database.bot.chat_usage import get_daily_usage, increment_usage
from utils.chatbot import get_system_prompt, MODEL, MAX_HISTORY
from utils.colors import ERROR
from utils.errors import DailyLimitReached
from utils.messages import Message, Page, usable_in
from utils.strings import EGGERT

info = {
    "name": "chat",
    "aliases": ["ask", "ai"],
    "description": "Ask Eggert a question about TypeGG or the bot.",
    "parameters": "<question>",
    "examples": [
        "-ask how does pp work?",
    ],
}

FREE_DAILY_LIMIT = 20
MAX_CONTEXTS = 500  # max unique (user, channel) pairs kept in memory

_client: anthropic.AsyncAnthropic = None
_history: OrderedDict[tuple, list] = OrderedDict()


def get_client() -> anthropic.AsyncAnthropic:
    global _client
    if _client is None:
        _client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
    return _client


class Chat(Command):
    @commands.command(aliases=info["aliases"])
    @usable_in(1397687954117361745)
    async def chat(self, ctx, *, question: str = None):
        is_gg_plus = ctx.user["isGgPlus"]
        if not is_gg_plus:
            current_usage = get_daily_usage(str(ctx.author.id))
            if current_usage >= FREE_DAILY_LIMIT:
                raise DailyLimitReached

        if not question:
            return await ctx.send(content=f"Hello {EGGERT} If you have any questions, just ask!")

        if not ANTHROPIC_API_KEY:
            message = Message(ctx, Page(
                description="Chatbot is not configured.",
                color=ERROR,
            ))
            return await message.send()

        user_id = str(ctx.author.id)
        history_key = (user_id, str(ctx.channel.id))
        if history_key in _history:
            _history.move_to_end(history_key)
        else:
            if len(_history) >= MAX_CONTEXTS:
                _history.popitem(last=False)  # evict least recently used
            _history[history_key] = []
        _history[history_key].append({"role": "user", "content": question})
        if len(_history[history_key]) > MAX_HISTORY:
            _history[history_key] = _history[history_key][-MAX_HISTORY:]

        async with ctx.typing():
            try:
                response = await get_client().messages.create(
                    model=MODEL,
                    max_tokens=512,
                    system=[{
                        "type": "text",
                        "text": get_system_prompt(),
                        "cache_control": {"type": "ephemeral"},
                    }],
                    messages=_history[history_key],
                )
                reply = response.content[0].text
                _history[history_key].append({"role": "assistant", "content": reply})
                _history.move_to_end(history_key)
                await ctx.message.reply(reply, mention_author=False)

                if not is_gg_plus:
                    increment_usage(user_id)

            except Exception:
                message = Message(ctx, Page(
                    description="Error: Failed to get a response from the chatbot.",
                    color=ERROR,
                ))
                await message.send()
