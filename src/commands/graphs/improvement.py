import numpy as np
from discord.ext import commands

from command_info import CommandInfo
from commands.base import Command
from context import BotContext
from database.typegg.quotes import get_quotes
from database.typegg.races import get_races
from graphs import improvement
from utils.colors import ERROR
from utils.dates import parse_date
from utils.messages import Field, Message, Page
from utils.schemas import Profile

metrics = {
    "pp": {"label": "pp", "suffix": " pp", "scale": 1},
    "wpm": {"label": "WPM", "suffix": " WPM", "scale": 1},
    "accuracy": {"label": "Accuracy", "suffix": "%", "scale": 100, "ceiling": 100},
}
info = CommandInfo(
    name="improvement",
    aliases=["imp", "simp"],
    description="Displays a user's pp, WPM or accuracy improvement over races.\n"
                "Use `-simp` to view solo PBs by pp instead of multiplayer.\n",
    parameters="[username] [wpm|pp|acc]",
    examples=[
        "-imp",
        "-imp eiko wpm",
        "-imp eiko acc",
        "-simp eiko",
    ],
)


class Improvement(Command):
    """Graph a user's pp, WPM or accuracy improvement over races."""

    supported_flags = {"metric", "raw", "status", "language", "date_range"}

    @commands.command(aliases=info.aliases)
    async def improvement(self, ctx: BotContext, *args: str):
        """Pick the solo or multiplayer graph, then draw it for one user."""
        solo = ctx.invoked_with == "simp"
        metric = "pp" if solo else "wpm"
        params = self.extract_params(args, ["accuracy"])

        if params.argument:
            metric = params.argument
        elif ctx.explicit_flags.get("metric"):  # Overriding default metric
            metric = ctx.explicit_flags["metric"].lstrip("-")

        if ctx.flags.status != "ranked" and metric == "pp":  # Unranked quotes are 0 pp
            metric = "wpm"

        self.check_raw_pp(ctx, metric == "pp")

        profile = await self.get_profile(ctx, params.username)

        if solo:
            await solo_improvement(ctx, profile, metric)
        else:
            await multiplayer_improvement(ctx, profile, metric)


def get_window_size(n: int, min_n: int = 25, max_n: int = 500) -> int:
    """Return a moving-average window scaled to the race count."""
    window_size = int(min(max_n, max(min_n, np.sqrt(n) * 5)))
    return window_size if window_size < n else 1


async def multiplayer_improvement(ctx: BotContext, profile: Profile, metric: str) -> None:
    """Send an improvement graph over a user's quickplay races."""
    ctx.flags.gamemode = "quickplay"
    race_list = await get_races(
        user_id=profile["userId"],
        columns=["quoteId", metric, "timestamp", "completionType"],
        flags=ctx.flags,
    )

    if not race_list:
        message = Message(
            ctx, page=Page(
                title="No Races",
                description=f"User `{profile["username"]}` has no quickplay races",
                footer="Use -simp to view solo improvement!",
                color=ERROR,
            )
        )

        return await message.send()

    quote_list = get_quotes()
    scale = metrics[metric]["scale"]

    values, dates, difficulties = zip(*[
        (race[metric] * scale, race["timestamp"], quote_list[race["quoteId"]]["difficulty"])
        for race in race_list
        if race["completionType"] == "finished"
    ])

    moving_25 = np.convolve(values, np.ones(25) / 25, mode="valid")
    best_25 = max(moving_25)
    last_25 = moving_25[-1]

    moving_100 = np.convolve(values, np.ones(100) / 100, mode="valid")
    best_100 = max(moving_100)
    last_100 = moving_100[-1]

    window = get_window_size(len(values))
    moving_average = np.convolve(values, np.ones(window) / window, mode="valid")
    best_average = max(moving_average)
    last_average = moving_average[-1]

    finishes_covered = window
    quits_in_average = 0

    for race in reversed(race_list):
        if race["completionType"] == "finished":
            finishes_covered -= 1
            if finishes_covered == 0:
                break
        else:
            quits_in_average += 1

    dnf_indices = []
    dnf = False

    for race in race_list:
        if race["completionType"] == "finished":
            dnf_indices.append(dnf)
            dnf = False
        else:
            dnf = True

    label, suffix = metrics[metric]["label"], metrics[metric]["suffix"]
    description = f"**Races:** {len(values):,}\n"

    fields = []

    if window > 25:
        fields.append(Field(
            title="Average of 25",
            content=f"– Recent: {last_25:,.2f}{suffix} | Best: {best_25:,.2f}{suffix}",
        ))

    if window > 100:
        fields.append(Field(
            title="Average of 100",
            content=f"– Recent: {last_100:,.2f}{suffix} | Best: {best_100:,.2f}{suffix}",
        ))

    fields.append(Field(
        title=f"Average of {window}",
        content=(
            f"– Recent: {last_average:,.2f}{suffix} | Best: {best_average:,.2f}{suffix}\n"
            f"– Completion: {window / (window + quits_in_average):.2%}"
        ),
    ))

    message = Message(
        ctx,
        title=f"{label} Improvement",
        header=description,
        pages=[
            Page(
                fields=fields,
                button_name="Over Races",
                render=lambda: improvement.render_over_races(
                    values=values,
                    difficulties=difficulties,
                    metric=label,
                    theme=ctx.user["theme"],
                    window_size=window,
                    dnf_indices=dnf_indices,
                ),
                flag_title=True,
            ),
            Page(
                fields=fields,
                button_name="Over Time",
                render=lambda: improvement.render_over_time(
                    values=values,
                    metric=label,
                    theme=ctx.user["theme"],
                    dates=dates,
                    window_size=window,
                    dnf_indices=dnf_indices,
                    ceiling=metrics[metric].get("ceiling"),
                ),
                flag_title=True,
            ),
        ],
        profile=profile,
    )

    await message.send()


async def solo_improvement(ctx: BotContext, profile: Profile, metric: str) -> None:
    """Send an improvement graph over a user's solo personal bests."""
    ctx.flags.gamemode = "solo"
    race_list = await get_races(
        user_id=profile["userId"],
        columns=["quoteId", metric, "timestamp"],
        flags=ctx.flags,
    )

    if not race_list:
        message = Message(
            ctx, page=Page(
                title="No Races",
                description=f"User `{profile["username"]}` has no ranked solo races",
                footer="Use -imp to view multiplayer improvement!",
                color=ERROR,
            )
        )

        return await message.send()

    pb_dict = {}
    pbs = []
    for race in race_list:
        quote_id = race["quoteId"]
        if quote_id not in pb_dict or race[metric] > pb_dict[quote_id][metric]:
            pb_dict[quote_id] = race
            pbs.append(race)
    pbs.sort(key=lambda r: parse_date(r["timestamp"]).timestamp())

    quote_list = get_quotes()
    scale = metrics[metric]["scale"]
    values, dates, quote_ids = zip(*[(race[metric] * scale, race["timestamp"], race["quoteId"]) for race in pbs])
    difficulties = [quote_list[qid]["difficulty"] for qid in quote_ids]

    window = get_window_size(len(values))

    label, suffix = metrics[metric]["label"], metrics[metric]["suffix"]
    description = (
        f"**PB Improvements:** {len(values):,}\n"
        f"**PB Average:** {np.mean(values):,.2f}{suffix}\n"
        f"**Best:** {max(values):,.2f}{suffix}\n"
    )

    message = Message(
        ctx,
        title=f"{label} PB Improvement",
        header=description,
        pages=[
            Page(
                button_name="Over Races",
                render=lambda: improvement.render_over_races(
                    values=values,
                    difficulties=difficulties,
                    metric=label,
                    theme=ctx.user["theme"],
                    window_size=window,
                ),
                flag_title=True,
            ),
            Page(
                button_name="Over Time",
                render=lambda: improvement.render_over_time(
                    values=values,
                    metric=label,
                    theme=ctx.user["theme"],
                    dates=dates,
                    window_size=window,
                    ceiling=metrics[metric].get("ceiling"),
                ),
                flag_title=True,
            )
        ],
        profile=profile,
    )

    await message.send()
