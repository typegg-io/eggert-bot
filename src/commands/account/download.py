import asyncio
from typing import Optional

from discord.ext import commands

from api.core import API_RATE_LIMIT
from api.quotes import get_quote
from api.sources import get_source
from api.users import get_races, get_profile
from commands.base import Command
from database.typegg import users, races
from database.typegg.quotes import get_quotes, add_quote
from database.typegg.races import add_races
from database.typegg.sources import get_sources, add_source
from database.typegg.users import get_user
from utils.logging import log
from utils.messages import Page, Message
from utils.strings import escape_formatting, LOADING

info = {
    "name": "download",
    "aliases": ["import", "dl", "gd", "i"],
    "description": "Imports a user's complete race history",
    "parameters": "[username]",
}


class Download(Command):
    @commands.command(aliases=info["aliases"])
    async def download(self, ctx, username: Optional[str] = "me"):
        profile = await self.get_profile(ctx, username, races_required=True)
        await run(ctx, profile)


async def import_new_quotes(new_quote_ids):
    source_ids = set(get_sources().keys())
    log("New quotes found: " + ", ".join(new_quote_ids))

    async def process_quote(quote_id):
        quote = await get_quote(quote_id)
        source_id = quote["source"]["sourceId"]

        if source_id not in source_ids:
            source = await get_source(source_id)
            log(f"Adding source: {source_id}")
            source_ids.add(source_id)
            add_source(source)

        log(f"Adding quote: {quote_id}")
        add_quote(quote)

    if len(new_quote_ids) <= 10:
        await asyncio.gather(*(process_quote(quote_id) for quote_id in new_quote_ids))
    else:
        for quote_id in new_quote_ids:
            await process_quote(quote_id)
            await asyncio.sleep(API_RATE_LIMIT)


async def run(
    ctx: Optional[commands.Context] = None,
    profile: Optional[dict] = None,
    user_id: Optional[str] = None
):
    background_import = ctx is None
    auto_import = (
        not background_import
        and ctx.invoked_with not in [info["name"]] + info["aliases"]
    )

    if not profile:
        profile = await get_profile(user_id)

    user_id = profile["userId"]
    formatted_username = escape_formatting(profile["username"])

    user_entry = get_user(user_id)
    if not user_entry:
        users.create_user(user_id)

    total_races = profile["stats"]["races"]
    latest_race_number = races.get_latest_race_number(user_id)
    races_left = total_races - latest_race_number

    status_message = (
        f"Importing {races_left:,} races for {formatted_username}"
        if races_left >= 1
        else f"No new races to import for {formatted_username}"
    )
    log(status_message)

    send_message = (
        not background_import
        and (not auto_import or races_left > 1000)
    )

    if send_message:
        page = Page(
            title=f"Import Request {LOADING}",
            description=status_message,
        )
        message = Message(ctx, page=page)

        if races_left < 1:
            page.title = "Import Request"
            page.description = status_message
            return await message.send()

        initial_send = message.start()

    if races_left < 1:
        return

    quote_ids = set(get_quotes().keys())
    new_quote_ids = set()

    start_number = latest_race_number + 1
    while start_number <= total_races:
        end_number = min(start_number + 999, total_races)
        log(f"Fetching races {start_number:,} - {end_number:,}")

        results = await get_races(
            user_id,
            start_number=start_number,
            end_number=end_number,
            per_page=1000,
            sort="number",
            reverse=False,
        )
        race_list = results["races"]

        for race in race_list:
            if race["quoteId"] not in quote_ids:
                new_quote_ids.add(race["quoteId"])

        add_races(race_list)

        start_number = race_list[-1]["raceNumber"] + 1

    if send_message:
        await initial_send

    if new_quote_ids:
        if not send_message:
            page = Page(
                title=f"New Quote Import {LOADING}",
                description="Adding new quotes to database",
            )
            message = Message(ctx, page)
            await message.send()
        elif len(new_quote_ids) > 10:
            page.title = f"New Quote Import {LOADING}"
            page.description = "Adding new quotes to database"
            await message.edit()

        await import_new_quotes(list(new_quote_ids))

        if not send_message:
            page.title = "New Quotes Import"
            page.description = "Finished adding new quotes"
            await message.edit()

    if send_message:
        page.title = "Import Request"
        page.description = f"Finished importing races for {formatted_username}"
        await message.edit()
