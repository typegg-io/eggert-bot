"""The guild member count route."""

from aiohttp import web


async def member_count(server, request: web.Request) -> web.Response:
    """Return the TypeGG guild's member count (GET /member-count)."""
    return web.json_response({"memberCount": server.member_count})
