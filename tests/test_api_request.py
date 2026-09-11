"""A 503 that says when to retry becomes an explanation rather than a bare API error."""

import asyncio

import pytest
from aiohttp import web
from aiohttp.test_utils import TestServer

from api.core import request
from utils.errors import APIError, APIUnavailable


def fetch(status: int, headers: dict) -> None:
    """Request one path from a local server that answers with the given status and headers."""

    async def handler(_: web.Request) -> web.Response:
        """Answer with TypeGG's error body shape."""
        return web.json_response({"message": "Quote positions are still being built"}, status=status, headers=headers)

    async def main() -> None:
        """Serve the handler and send one request to it."""
        app = web.Application()
        app.router.add_get("/", handler)
        async with TestServer(app) as server:
            await request(str(server.make_url("/")))

    asyncio.run(main())


def test_a_warming_503_says_when_to_retry():
    """TypeGG answers 503 with Retry-After while the quote position boards build."""
    with pytest.raises(APIUnavailable) as caught:
        fetch(503, {"Retry-After": "30"})

    assert caught.value.retry_after == 30
    assert caught.value.embed.description == "Quote positions are still being built\nTry again in 30 seconds"


def test_a_503_without_retry_after_stays_an_api_error():
    """Only a retry hint earns the friendlier embed."""
    with pytest.raises(APIError) as caught:
        fetch(503, {})

    assert caught.value.status == 503
