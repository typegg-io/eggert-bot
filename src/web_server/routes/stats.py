from aiohttp import web

from api.users import get_profile


async def stats_page(request: web.Request):
    username = request.match_info["username"]
    profile = await get_profile(username)
    html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>User Stats</title>
            <link rel="stylesheet" href="/static/css/style.css">
        </head>
        <body>
            <h1>{username}</h1>
            <p>nWPM: {profile["stats"].get('nWpm', "n/a")}</p>
            <p>Races: {profile["stats"].get('races', "n/a")}</p>
        </body>
        </html>
    """

    return web.Response(text=html, content_type="text/html")
