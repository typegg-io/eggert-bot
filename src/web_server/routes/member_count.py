"""The guild member count route."""

from typing import TYPE_CHECKING

from aiohttp import web

if TYPE_CHECKING:
    from web_server.server import WebServer


async def member_count(server: "WebServer", request: web.Request) -> web.Response:
    """Return the TypeGG guild's member count (GET /member-count)."""
    return web.json_response({"memberCount": server.member_count})
