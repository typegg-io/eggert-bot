from aiohttp import web


async def member_count(server, request: web.Request):
    return web.json_response({"memberCount": server.member_count})
