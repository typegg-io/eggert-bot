import math
from collections import defaultdict

from discord.ext import commands

from commands.base import Command
from database.typegg.quotes import get_quotes
from database.typegg.users import get_quote_bests
from graphs import compare_histogram, compare_bar
from utils.errors import NoCommonTexts, SameUsername, InvalidRange, InvalidArgument
from utils.messages import Page, Message, Field
from utils.strings import username_with_flag

metrics = ["pp", "wpm"]
info = {
    "name": "comparegraph",
    "aliases": ["cg", "flaneur"],
    "description": "Displays a quote best comparison graph based on difficulty, with optional range filtering.",
    "parameters": "<username1> [username2] [difficulty_range] [pp|wpm]",
}


class CompareGraph(Command):
    @commands.command(aliases=info["aliases"])
    async def comparegraph(self, ctx, username1: str, *args: str):
        username2 = "me"
        diff_range = None
        metric = None

        remaining_args = list(args)
        if remaining_args:
            second_arg = remaining_args[0]
            if "-" not in second_arg and second_arg not in metrics:
                username2 = second_arg
                remaining_args = remaining_args[1:]

        for arg in remaining_args:
            if "-" in arg and diff_range is None:
                try:
                    low, high = map(float, arg.split("-", 1))
                    if low == high:
                        raise ValueError
                    diff_range = (min(low, high), max(low, high))
                    continue
                except ValueError:
                    raise InvalidRange

            if arg in metrics and metric is None:
                metric = arg
                continue

            raise InvalidArgument(metrics)

        metric = metric or "pp"
        username1, username2 = self.get_usernames(ctx, username1, username2)
        profile1 = await self.get_profile(ctx, username1, races_required=True)
        profile2 = await self.get_profile(ctx, username2, races_required=True)

        if profile1["username"] == profile2["username"]:
            raise SameUsername

        await self.import_user(ctx, profile1)
        await self.import_user(ctx, profile2)

        if diff_range:
            await comparegraph_ranged(ctx, profile1, profile2, diff_range[0], diff_range[1], metric)
        else:
            await comparegraph_main(ctx, profile1, profile2)


def difficulty_range(lower, upper):
    lower = round(lower, 2)
    upper = round(upper, 2)
    return f"{lower:.10g} - {upper:.10g}★"


def max_positive_subarray_sum(buckets, diffs):
    max_sum = 0
    current_sum = 0
    start = 0
    best_start = best_end = None

    for i, diff in enumerate(diffs):
        if diff > 0:
            if current_sum == 0:
                start = i
            current_sum += diff
            if current_sum > max_sum:
                max_sum = current_sum
                best_start, best_end = start, i
        else:
            current_sum = 0

    if best_start is None:
        return 0, None, None
    return max_sum, buckets[best_start], buckets[best_end]


async def comparegraph_main(ctx: commands.Context, profile1: dict, profile2):
    quotes = get_quotes()
    quote_bests1 = get_quote_bests(profile1["userId"], as_dictionary=True)
    quote_bests2 = get_quote_bests(profile2["userId"], as_dictionary=True)
    quote_ids1 = quote_bests1.keys()
    quote_ids2 = quote_bests2.keys()

    if not list(quote_bests1.keys() & quote_bests2.keys()):
        raise NoCommonTexts

    gains1 = defaultdict(int)
    gains2 = defaultdict(int)
    defaults = defaultdict(int)

    # Aggregation
    min_difficulty1 = float("inf")
    max_difficulty1 = float("-inf")
    min_difficulty2 = float("inf")
    max_difficulty2 = float("-inf")

    for quote_id in set(quote_ids1) | set(quote_ids2):
        difficulty = quotes[quote_id]["difficulty"]
        bucket = math.floor(difficulty * 2) / 2

        in1 = quote_id in quote_bests1
        in2 = quote_id in quote_bests2

        if in1:
            min_difficulty1 = min(min_difficulty1, difficulty)
            max_difficulty1 = max(max_difficulty1, difficulty)
        if in2:
            min_difficulty2 = min(min_difficulty2, difficulty)
            max_difficulty2 = max(max_difficulty2, difficulty)

        if in1 and not in2:
            defaults[bucket] -= 1
        elif in2 and not in1:
            defaults[bucket] += 1
        else:
            if quote_bests1[quote_id]["pp"] > quote_bests2[quote_id]["pp"]:
                gains1[bucket] += 1
            else:
                gains2[bucket] += 1

    # Post-processing
    all_buckets = set(gains1) | set(gains2)
    differences = {b: gains1[b] - gains2[b] for b in all_buckets}
    most_active_bucket, most_active_quotes = max(
        ((b, gains1[b] + gains2[b]) for b in differences),
        key=lambda x: x[1],
        default=(None, 0)
    )

    sorted_buckets = sorted(differences.keys())
    diff_values = [differences[b] for b in sorted_buckets]

    sum1, start1, end1 = max_positive_subarray_sum(sorted_buckets, diff_values)
    sum2, start2, end2 = max_positive_subarray_sum(sorted_buckets, [-d for d in diff_values])

    strength1 = "—"
    strength2 = "—"
    if sum1 > 0:
        strength1 = f"{difficulty_range(start1, end1 + 0.5)} (+{sum1:,} quotes)"
    if sum2 > 0:
        strength2 = f"{difficulty_range(start2, end2 + 0.5)} (+{sum2:,} quotes)"

    quotes1 = sum(gains1.values())
    quotes2 = sum(gains2.values())
    unique1 = len(quote_ids1 - quote_ids2)
    unique2 = len(quote_ids2 - quote_ids1)
    common = len(quote_ids1 & quote_ids2)
    total_quotes = quotes1 + quotes2
    edge1 = (quotes1 - quotes2) / total_quotes
    edge2 = (quotes2 - quotes1) / total_quotes

    # Output
    description = (
        f"**Common Quotes:** {common:,}\n"
        f"**Most Active Difficulty:** {difficulty_range(most_active_bucket, most_active_bucket + 0.5)} "
        f"({most_active_quotes} quotes)"
    )

    field1 = Field(
        title=f"{username_with_flag(profile1)}",
        content=(
            f"**Quotes:** +{quotes1}\n"
            f"**Unique Quotes:** +{unique1:,}\n"
            f"**Difficulty Range:** {difficulty_range(min_difficulty1, max_difficulty1)}\n" +
            f"**Strength:** {strength1}\n"
            f"**Edge:** {edge1:,.2%}{" :trophy:" * (edge1 == 1)}"
        ),
        inline=True,
    )

    field2 = Field(
        title=f"{username_with_flag(profile2)}",
        content=(
            f"**Quotes:** +{quotes2}\n"
            f"**Unique Quotes:** +{unique2:,}\n"
            f"**Difficulty Range:** {difficulty_range(min_difficulty2, max_difficulty2)}\n" +
            f"**Strength:** {strength2}\n"
            f"**Edge:** {edge2:,.2%}{" :trophy:" * (edge2 == 1)}"
        ),
        inline=True,
    )

    message = Message(
        ctx, page=Page(
            title="Quote Best Comparison",
            description=description,
            fields=[field1, field2],
            render=lambda: compare_bar.render(
                profile1["username"],
                gains1,
                profile2["username"],
                gains2,
                defaults,
                ctx.user["theme"],
            )
        )
    )

    await message.send()


async def comparegraph_ranged(
    ctx: commands.Context,
    profile1: dict,
    profile2: dict,
    min_difficulty: float,
    max_difficulty: float,
    metric: str,
):
    quotes = get_quotes(min_difficulty=min_difficulty, max_difficulty=max_difficulty)
    quote_bests1 = get_quote_bests(profile1["userId"], as_dictionary=True)
    quote_bests2 = get_quote_bests(profile2["userId"], as_dictionary=True)
    common_quotes = list(quotes.keys() & quote_bests1.keys() & quote_bests2.keys())
    if not common_quotes:
        raise NoCommonTexts

    differences = [
        quote_bests1[quote_id][metric] - quote_bests2[quote_id][metric]
        for quote_id in common_quotes
    ]

    gains1 = [diff for diff in differences if diff > 0]
    gains2 = [-diff for diff in differences if diff < 0]
    match = max((
        (common_quotes[i], quote_bests1[common_quotes[i]][metric])
        for i, diff in enumerate(differences)
        if diff == 0.0
    ), key=lambda x: x[1], default=None)

    def display_gain(value, decimals=2):
        gain = f"{value:,.{decimals}f}"
        if value >= 0:
            gain = "+" + gain

        return gain

    def make_field(username, country, quotes_greater, gain, average_gain, max_gap, metric1, metric2, metric):
        if metric == "wpm":
            metric = metric.upper()
        flag = "" if country == "" else f":flag_{country.lower()}: "

        content = (
            f"**Quotes:** {display_gain(quotes_greater, 0)}\n"
            f"**Gain:** {display_gain(gain)} {metric}\n"
            f"**Average Gain:** {display_gain(average_gain)} {metric}\n"
            f"**{"Biggest Gain" if max_gap > 0 else "Closest"}:** {display_gain(max_gap)} {metric}\n"
            f"{metric1:,.2f} {metric} vs. {metric2:,.2f} {metric}\n"
        )

        if match:
            content += f"{match[0]} - {match[1]:,.2f} {metric} :handshake:"

        return Field(
            title=flag + username,
            content=content,
            inline=True,
        )

    fields = []

    username1 = profile1["username"]
    country = profile1["country"]
    quotes_greater = len(gains1)
    gain = sum(gains1)
    average_gain = 0 if gain == 0 else gain / quotes_greater
    max_gap = -min(gains2) if gain == 0 else max(gains1)
    quote_id = common_quotes[differences.index(max_gap)]
    metric1 = quote_bests1[quote_id][metric]
    metric2 = quote_bests2[quote_id][metric]

    fields.append(
        make_field(
            username1, country, quotes_greater, gain, average_gain, max_gap, metric1, metric2, metric
        )
    )

    username2 = profile2["username"]
    country = profile2["country"]
    quotes_greater = len(gains2)
    gain = sum(gains2)
    average_gain = 0 if gain == 0 else gain / quotes_greater
    max_gap = -min(gains1) if gain == 0 else max(gains2)
    quote_id = common_quotes[differences.index(-max_gap)]
    metric1 = quote_bests2[quote_id][metric]
    metric2 = quote_bests1[quote_id][metric]

    fields.append(
        make_field(
            username2, country, quotes_greater, gain, average_gain, max_gap, metric1, metric2, metric
        )
    )

    page = Page(
        title=f"Quote Best Comparison ({difficulty_range(min_difficulty, max_difficulty)})",
        fields=fields,
        render=lambda: compare_histogram.render(
            username1,
            gains1,
            username2,
            gains2,
            metric,
            ctx.user["theme"],
        )
    )

    message = Message(
        ctx,
        page=page,
    )

    await message.send()
