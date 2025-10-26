import aiohttp_jinja2
from aiohttp import web

from api.users import get_profile
from commands.account.download import run as download
from database.typegg.quotes import get_quotes
from database.typegg.users import get_quote_bests
from utils.strings import truncate_clean
from utils.urls import race_url


@aiohttp_jinja2.template("compare.html")
async def compare_page(request: web.Request):
    username1 = request.match_info.get("username1")
    username2 = request.match_info.get("username2")

    profile1 = await get_profile(username1)
    profile2 = await get_profile(username2)

    await download(profile=profile1)
    await download(profile=profile2)

    quotes = get_quotes()
    quote_bests1 = get_quote_bests(profile1["userId"], as_dictionary=True)
    quote_bests2 = get_quote_bests(profile2["userId"], as_dictionary=True)

    common_quote_ids = set(quote_bests1.keys()) & set(quote_bests2.keys())

    comparison = []
    for quote_id in common_quote_ids:
        score1 = quote_bests1[quote_id]["pp"]
        score2 = quote_bests2[quote_id]["pp"]
        difference = score1 - score2
        quote = quotes[quote_id]
        comparison.append({
            "text": truncate_clean(quote["text"], 60, 3),
            "score1": score1,
            "score2": score2,
            "difference": difference,
            "difficulty": quote["difficulty"],
            "link": race_url(quote_id),
        })

    comparison.sort(key=lambda x: -x["difference"])

    return {
        "username1": profile1["username"],
        "username2": profile2["username"],
        "comparison": comparison,
    }
