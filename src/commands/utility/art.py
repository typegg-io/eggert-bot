import re
from difflib import get_close_matches
from typing import Optional

from discord.ext import commands

from commands.base import Command
from database.bot import art as art_db
from database.bot.users import get_user
from utils.errors import GeneralException, MissingArguments
from utils.logging import ADMIN_ALIASES
from utils.messages import Page, Message, paginate_data
from utils.strings import discord_date

info = {
    "name": "art",
    "aliases": [],
    "description": (
        "View and submit community art!\n\n"
        "**Usage:**\n"
        "`-art` - View a random piece of art\n"
        "`-art add <title>` - Submit new art (attach an image)\n"
        "`-art <title>` - View specific art by title\n"
        "`-art list` - View all submitted art\n"
        "`-art delete <title>` - Delete art (admin only)"
    ),
    "parameters": "[title | add <title> | list | delete <title>]",
}


class Art(Command):
    @commands.command(aliases=info["aliases"])
    async def art(self, ctx, *, args: Optional[str] = None):
        if not args:
            await show_random_art(ctx)
            return

        parts = args.split(None, 1)
        subcommand = parts[0].lower()

        if subcommand == "add":
            if len(parts) < 2:
                raise MissingArguments
            await add_art(ctx, parts[1])
        elif subcommand in ["list", "gallery"]:
            await list_art(ctx)
        elif subcommand == "delete":
            if len(parts) < 2:
                raise MissingArguments
            await delete_art_command(ctx, parts[1])
        elif user := get_user(re.sub(r"<@!?(\d+)>", r"\1", subcommand), auto_insert=False):
            await list_art(ctx, author_id=user["discordId"])
        else:
            await show_art_by_title(ctx, args)


async def show_random_art(ctx: commands.Context):
    """Display a random piece of art."""
    art = art_db.get_random_art()

    if not art:
        page = Page(
            title="Art Gallery",
            description=(
                "No art has been submitted yet.\n"
                "Use `-art add <title>` and attach an image to be the first!"
            ),
        )
        message = Message(ctx, page=page)
        return await message.send()

    await display_art(ctx, art)


async def add_art(ctx: commands.Context, args: str):
    """Add a new piece of art."""
    if not ctx.message.attachments:
        raise GeneralException(
            "No Image Attached",
            "Please attach an image to your message.\n"
            "Usage: `-art add <title>` with an image attached"
        )

    image_url = ctx.message.attachments[0].url
    title = args.strip()

    if len(title) > 100:
        raise GeneralException(
            "Title Too Long",
            "Title must be 100 characters or less."
        )

    if art_db.art_exists(title):
        raise GeneralException(
            "Title Already Exists",
            "Please choose a different title."
        )

    art_db.add_art(title, image_url, str(ctx.author.id))

    page = Page(
        title="Art Submitted!",
        description=(
            f"**{title}** has been added to the gallery.\n\n"
            f"View it with `-art {title}`"
        ),
    )

    message = Message(ctx, page=page)
    await message.send()


async def show_art_by_title(ctx: commands.Context, title: str):
    """Show a specific piece of art by title (with fuzzy matching)."""
    art = art_db.get_art_by_title(title)

    if not art:  # Fuzzy search
        all_art = art_db.get_all_art()
        all_titles = [a["title"] for a in all_art]
        matches = get_close_matches(title, all_titles, n=1, cutoff=0.6)

        if matches:
            art = art_db.get_art_by_title(matches[0])
        else:
            page = Page(
                title="Art Not Found",
                description="Use `-art list` to see all available art.",
            )
            message = Message(ctx, page=page)
            return await message.send()

    await display_art(ctx, art)


async def list_art(ctx: commands.Context, author_id: str = None):
    """Display a list of all art in the gallery, optionally filtered by author."""
    if author_id:
        all_art = art_db.get_art_by_author(author_id)
        header = f"**By:** <@{author_id}>\n"
        empty = f"<@{author_id}> hasn't submitted any art yet!"

        def formatter(art):
            return f"**{art["title"]}** - {discord_date(art["timestamp"], "D")}\n"
    else:
        all_art = art_db.get_all_art()
        header = ""
        empty = "No art has been submitted yet!"

        def formatter(art):
            return (
                f"**{art["title"]}** | "
                f"By: <@{art["author_id"]}> - "
                f"{discord_date(art["timestamp"], "D")}\n"
            )

    if not all_art:
        page = Page(title="Art Gallery", description=empty)
        message = Message(ctx, page=page)
        return await message.send()

    pages = paginate_data(all_art, formatter, page_count=999, per_page=20)

    message = Message(
        ctx,
        title="Art Gallery",
        header=header,
        pages=pages,
        footer="Use -art <title> to view a specific piece"
    )
    await message.send()


async def display_art(ctx: commands.Context, art: dict):
    """Display a single piece of art."""
    page = Page(
        title=art["title"],
        description=(
            f"**Artist:** <@{art["author_id"]}>\n"
            f"**Submitted:** {discord_date(art["timestamp"], "D")}"
        ),
        image_url=art["image_url"],
    )

    message = Message(ctx, page=page)
    await message.send()


async def delete_art_command(ctx: commands.Context, title: str):
    """Delete a piece of art (admins only)."""
    if ctx.author.id not in ADMIN_ALIASES.keys():
        raise GeneralException(
            "Permission Denied",
            "Only admins can delete art."
        )

    if not art_db.art_exists(title):
        raise GeneralException(
            "Art Not Found",
            f"No art found with this title."
        )

    art_db.delete_art(title)

    page = Page(
        title="Art Deleted",
        description=f"**{title}** has been removed from the gallery.",
    )

    message = Message(ctx, page=page)
    await message.send()
