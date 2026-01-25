from typing import Optional

from dateutil.relativedelta import relativedelta
from discord.ext import commands

from api.quotes import get_quote
from api.sources import get_source
from api.users import get_races, get_profile
from commands.base import Command
from database.typegg.keystroke_data import add_keystroke_data
from database.typegg.match_results import add_match_results
from database.typegg.matches import add_matches
from database.typegg.quotes import get_quotes, add_quote
from database.typegg.races import add_races, get_latest_race
from database.typegg.sources import get_sources, add_source
from database.typegg.users import get_user, create_user
from utils.dates import string_to_date, date_to_string, epoch, parse_date
from utils.logging import log
from utils.messages import Page, Message
from utils.stats import calculate_duration
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

    total_races = await get_total_races(user_id)
    latest_race = get_latest_race(user_id)

    if latest_race is None:
        latest_date = epoch()
        latest_race_number = 0
    else:
        latest_date = string_to_date(latest_race["timestamp"])
        latest_race_number = latest_race["raceNumber"]

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
    start_date = latest_date + relativedelta(microseconds=1000)

    while True:
        new_quote_ids = set()

        results = await get_races(
            user_id,
            start_date=date_to_string(start_date),
            per_page=1000,
            sort="timestamp",
            reverse=False,
            get_keystrokes=True,
        )
        race_list = results["races"]
        race_list_no_dnf = []

        if not race_list:
            break

        log(f"Fetched races {race_list[0]["raceNumber"] or "DNF"} - {race_list[-1]["raceNumber"] or "DNF"}")

        match_list = []
        match_result_list = []

        for race in race_list:
            quote_id = race["quoteId"]

            if quote_id not in quote_ids:
                new_quote_ids.add(quote_id)
                quote_ids.add(quote_id)

            if race["completionType"] == "finished":
                race_list_no_dnf.append(race)

            match = race.get("match")

            if match:
                race["matchId"] = match["matchId"]
                players = match["players"]
                match["players"] = len(players)
                match["gamemode"] = race["gamemode"]
                match["quoteId"] = quote_id
                match_list.append(match)

                for player in players:
                    player["matchId"] = match["matchId"]
                    player["rawMatchPp"] = player.get("rawPp", 0) * (player["matchWpm"] / (player["wpm"] or 1))
                    start_timestamp = match["startTime"]
                    duration = calculate_duration(player["matchWpm"], player["charactersTyped"])
                    end_timestamp = parse_date(start_timestamp) + relativedelta(microseconds=duration * 1000)
                    player["timestamp"] = date_to_string(end_timestamp)
                    match_result_list.append(player)

        if new_quote_ids:
            new_quote_count = len(new_quote_ids)
            title = f"New Quote Import {LOADING}"
            description = f"Adding {new_quote_count:,} new quotes to database"
            if message is not None:
                page.title = title
                page.description = description
                await initial_send
                await message.edit()
            elif new_quote_count > 10 and not background_import:
                page = Page(
                    title=title,
                    description=description,
                )
                message = Message(ctx, page)
                await message.send()

            await import_new_quotes(list(new_quote_ids))

        add_races(race_list_no_dnf)
        add_keystroke_data(race_list_no_dnf)
        add_matches(match_list)
        add_match_results(match_result_list)

        start_date = string_to_date(race_list[-1]["timestamp"]) + relativedelta(microseconds=1000)

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


async def get_total_races(user_id):
    """Get the true latest race number by iterating backwards through races."""
    page = 1
    per_page = 20
    max_pages = 5

    while page <= max_pages:
        races_data = await get_races(user_id, page=page, per_page=per_page)
        races = races_data["races"]

        if not races:
            return 0

        for race in races:
            if race.get("raceNumber") is not None:
                return race["raceNumber"]

        page += 1

    return 0
