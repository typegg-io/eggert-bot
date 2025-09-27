from typing import Optional

from discord.ext import commands

from api.users import get_races, get_profile
from commands.base import Command
from database.typegg import users, races
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
        profile = await self.get_profile(ctx, username)
        await run(ctx, profile)


def race_insert(race):
    return (
        race.get("raceId"),
        race.get("quoteId"),
        race.get("userId"),
        race.get("raceNumber"),
        race.get("pp"),
        race.get("rawPp"),
        race.get("wpm"),
        race.get("rawWpm"),
        race.get("duration"),
        race.get("accuracy"),
        race.get("errorReactionTime"),
        race.get("errorRecoveryTime"),
        race.get("timestamp"),
        race.get("stickyStart"),
        race.get("gamemode"),
    )


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

        insert_list = [race_insert(race) for race in race_list]
        races.add_races(insert_list)

        start_number = race_list[-1]["raceNumber"] + 1

    if send_message:
        page.title = "Import Request"
        page.description = f"Finished importing races for {formatted_username}"

        await initial_send
        await message.edit()
