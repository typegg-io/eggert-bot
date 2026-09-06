"""Tests for the middlewares wrapping every web server request."""

import asyncio

from aiohttp import web
from aiohttp.test_utils import make_mocked_request

from web_server.middleware import security_headers_middleware


async def ok(request) -> web.Response:
    """Return a bare 200, standing in for whatever handler a route carries."""
    return web.Response(text="ok")


def headers_for(path: str) -> dict:
    """Return the headers the security middleware puts on a response for a path."""
    response = asyncio.run(security_headers_middleware(make_mocked_request("GET", path), ok))

    return dict(response.headers)


def test_static_assets_must_be_revalidated():
    assert headers_for("/static/js/dashboard.js")["Cache-Control"] == "no-cache"


def test_uploaded_assets_must_be_revalidated():
    assert headers_for("/assets/logo.png")["Cache-Control"] == "no-cache"


def test_pages_are_left_uncached():
    assert "Cache-Control" not in headers_for("/dashboard")


def test_every_response_carries_the_security_headers():
    headers = headers_for("/dashboard")

    assert "script-src 'self'" in headers["Content-Security-Policy"]
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["X-Frame-Options"] == "DENY"
