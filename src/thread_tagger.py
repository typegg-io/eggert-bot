"""The cog that tags new forum threads for review, so untriaged ones can be filtered."""

import discord
from discord.ext import commands

from config import REVIEW_TAGS
from utils.forum_tags import find_tag, review_tag_name, tags_with_review
from utils.logging import log, log_error


async def apply_review_tag(thread: discord.Thread) -> bool:
    """Add its forum's review tag to a thread, returning whether it was tagged. Never raises."""
    try:
        name = review_tag_name(thread.id, thread.parent_id)
        forum = thread.parent
        if name is None or not isinstance(forum, discord.ForumChannel):
            return False

        tag = find_tag(forum.available_tags, name)
        if tag is None:
            log(f"Thread tagger: no `{name}` tag in #{forum.name}")
            return False

        if not forum.permissions_for(thread.guild.me).manage_threads:
            log(f"Thread tagger: missing Manage Threads in #{forum.name}")
            return False

        applied = tags_with_review(thread.applied_tags, tag)
        if applied is None:
            return False

        # An archived thread cannot be edited, so it is reopened and closed again in the same edit.
        if thread.archived:
            await thread.edit(archived=False)
            await thread.edit(applied_tags=applied, archived=True)
        else:
            await thread.edit(applied_tags=applied)
        return True
    except Exception as error:
        log_error(f"Thread tagger: {thread.id}", error)
        return False


def review_forums(bot: commands.Bot) -> list[discord.ForumChannel]:
    """Return the review forums the bot can see."""
    forums = [bot.get_channel(forum_id) for forum_id in REVIEW_TAGS]
    return [forum for forum in forums if isinstance(forum, discord.ForumChannel)]


class ThreadTagger(commands.Cog):
    """Cog that tags each new review forum thread and catches up on startup."""

    def __init__(self, bot) -> None:
        """Hold the bot whose forums get tagged."""
        self.bot = bot

    async def cog_load(self) -> None:
        """Sweep once on load, since the bot is already ready by the time this cog loads."""
        self.bot.loop.create_task(self.catch_up())

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        """Sweep again after a fresh session, for threads posted while disconnected."""
        await self.catch_up()

    @commands.Cog.listener()
    async def on_thread_create(self, thread: discord.Thread) -> None:
        """Tag a thread posted in a review forum."""
        await apply_review_tag(thread)

    async def catch_up(self) -> None:
        """Tag every active thread with no tags in the review forums."""
        await self.bot.wait_until_ready()
        for forum in review_forums(self.bot):
            for thread in forum.threads:
                if not thread.applied_tags:
                    await apply_review_tag(thread)


async def setup(bot) -> None:
    """Register the thread tagger cog."""
    await bot.add_cog(ThreadTagger(bot))
