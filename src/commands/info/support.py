from discord.ext import commands

from commands.base import Command
from utils.colors import PLUS
from utils.messages import Page, Message, Field
from utils.strings import GG_PLUS

info = {
    "name": "support",
    "aliases": ["gg+", "premium", "subscribe"],
    "description": "Displays information about the GG+ subscription",
}


class Support(Command):
    @commands.command(aliases=info["aliases"])
    async def support(self, ctx):
        page = Page(
            description=(
                f"### [Upgrade to {GG_PLUS}](https://typegg.io/plus)\n"
                f"**Unlock your full typing potential**\n"
                f"Get exclusive features, customization options, and support the platform you love.\n"
            ),
            fields=[
                Field(
                    title="💰 Premium Perks",
                    content=(
                        "• **Ad-Free Experience** - Enjoy uninterrupted typing\n"
                        "• **+20% Bonus Keycaps** - Earn in-game currency faster\n"
                        "• **Custom Emojis** - Express yourself in multiplayer lobbies"
                    ),
                ),
                Field(
                    title="📊 Advanced Features",
                    content=(
                        "• **Advanced Quote Filters** - Unplayed, time filters & more\n"
                        "• **Friend & Country Leaderboards** - Compare with your circle\n"
                        "• **Quickplay nWPM Requirements** - See quote difficulty thresholds"
                    ),
                ),
                Field(
                    title="📈 Bot Enhancements",
                    content=(
                        "• **Custom Graph Themes** - Personalize your stat visualizations\n"
                        "• **Raw pp Access** - View detailed pp calculations\n"
                        "• **pp Calculator** - Plan your improvement strategy"
                    ),
                ),
                Field(
                    title="💎 Visual Customization",
                    content=(
                        "• **Gradient Name & GG+ Badge** - Stand out in leaderboards and chat\n"
                        "• **Custom Banner** - Personalize your profile page\n"
                        "• **About Me Section** - Share your story with the world"
                    ),
                ),
                Field(
                    title="✨ And More...",
                    content=(
                        "New features are being added regularly!\n"
                        "Your subscription helps support development and keep TypeGG running."
                    ),
                ),
            ],
            color=PLUS,
        )

        message = Message(
            ctx=ctx,
            page=page,
            footer=f"GG+ · $4.99/mo · Cancel anytime",
        )

        await message.send()
