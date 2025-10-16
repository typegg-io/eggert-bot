from typing import Optional

from discord.ext import commands

from api.quotes import get_quote
from api.sources import get_source
from api.users import get_races, get_profile
from commands.base import Command
from database.typegg.quotes import get_quotes, add_quote
from database.typegg.races import add_races, get_latest_race
from database.typegg.sources import get_sources, add_source
from database.typegg.users import get_user, create_user
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

    for quote_id in new_quote_ids:
        await process_quote(quote_id)


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
    message = None

    if not profile:
        profile = await get_profile(user_id)

    user_id = profile["userId"]
    formatted_username = escape_formatting(profile["username"])

    user_entry = get_user(user_id)
    if not user_entry:
        create_user(user_id)

    total_races = profile["stats"]["races"]
    latest_race = get_latest_race(user_id)
    latest_race_number = 0 if latest_race is None else latest_race["raceNumber"]
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

    start_number = latest_race_number + 1
    while start_number <= total_races:
        new_quote_ids = set()
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
            quote_id = race["quoteId"]
            if quote_id not in quote_ids:
                new_quote_ids.add(quote_id)
                quote_ids.add(quote_id)

        if new_quote_ids:
            new_quote_count = len(new_quote_ids)
            title = f"New Quote Import {LOADING}"
            description = f"Adding {new_quote_count:,} new quotes to database"
            if message is not None:
                page.title = title
                page.description = description
                await message.edit()
            elif new_quote_count > 10:
                page = Page(
                    title=title,
                    description=description,
                )
                message = Message(ctx, page)
                await message.send()

            await import_new_quotes(list(new_quote_ids))

        add_races(race_list)

        start_number = race_list[-1]["raceNumber"] + 1

    if send_message:
        await initial_send

    if send_message:
        page.title = "Import Request"
        page.description = f"Finished importing races for {formatted_username}"
        await message.edit()
    elif message is not None:
        page.title = "New Quotes Import"
        page.description = "Finished adding new quotes"
        await message.edit()
