"""The private usage dashboard, its token exchange and its stats endpoint."""

import time
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import aiohttp_jinja2
import jwt
from aiohttp import web

from api.verification import DASHBOARD_SCOPE
from config import SECRET
from database.bot import command_log, servers
from database.bot.users import get_user
from utils.logging import log_server
from web_server.utils import error_response

if TYPE_CHECKING:
    from web_server.server import WebServer

# Constants

COOKIE_NAME = "eggert_dashboard"
SESSION_SECONDS = 30 * 86400
# Re-issue a cookie older than this so the session slides rather than expiring 30 days after login.
REFRESH_AFTER = 86400

SESSION_SCOPE = "dashboard-session"

DENIED = "This dashboard is admin only. Run -dashboard in Discord for a fresh link."


# Sessions

def is_admin(discord_id: str) -> bool:
    """Return whether a Discord ID still belongs to a bot admin."""
    user = get_user(discord_id, auto_insert=False)
    return bool(user and user["isAdmin"])


def read_session(request: web.Request) -> str | None:
    """Return the Discord ID of the signed-in admin, or None when the cookie is absent or stale."""
    cookie = request.cookies.get(COOKIE_NAME)
    if not cookie:
        return None

    try:
        payload = jwt.decode(cookie, SECRET, algorithms=["HS256"])
    except jwt.InvalidTokenError:
        return None

    if payload.get("scope") != SESSION_SCOPE:
        return None

    discord_id = payload.get("discordId")
    if not discord_id or not is_admin(discord_id):
        return None

    request["session_issued"] = payload.get("iat", 0)

    return discord_id


def set_session(response: web.StreamResponse, discord_id: str) -> None:
    """Attach a fresh 30 day session cookie to a response."""
    issued = int(time.time())
    cookie = jwt.encode(
        {
            "discordId": discord_id,
            "scope": SESSION_SCOPE,
            "iat": issued,
            "exp": issued + SESSION_SECONDS,
        },
        SECRET,
        algorithm="HS256",
    )

    response.set_cookie(
        COOKIE_NAME, cookie,
        max_age=SESSION_SECONDS,
        path="/dashboard",
        httponly=True,
        secure=True,
        samesite="Lax",
    )


def redeem_token(cog: "WebServer", token: str) -> str | None:
    """Return the Discord ID a single-use link token names, burning it, or None when it is not valid."""
    if token in cog.used_tokens:
        return None

    try:
        payload = jwt.decode(token, SECRET, algorithms=["HS256"])
    except jwt.InvalidTokenError:
        return None

    if payload.get("scope") != DASHBOARD_SCOPE:
        return None

    discord_id = payload.get("discordId")
    if not discord_id or not is_admin(discord_id):
        return None

    cog.used_tokens[token] = datetime.fromtimestamp(payload["exp"], UTC)

    return discord_id


def private(response: web.StreamResponse) -> web.StreamResponse:
    """Mark a response as one search engines must not index."""
    response.headers["X-Robots-Tag"] = "noindex, nofollow"
    return response


def denied(request: web.Request) -> web.Response:
    """Return the 401 page shown to anyone without a valid session."""
    return private(aiohttp_jinja2.render_template(
        "error.html", request,
        {"status": 401, "error": "Unauthorized", "message": DENIED},
        status=401,
    ))


# Routes

async def dashboard_page(cog: "WebServer", request: web.Request) -> web.StreamResponse:
    """Serve the dashboard, exchanging a link token for a session first (GET /dashboard)."""
    token = request.query.get("token")

    if token:
        discord_id = redeem_token(cog, token)
        if not discord_id:
            return denied(request)

        log_server(f"Dashboard session opened for {discord_id}")

        # Redirecting strips the token from the address bar, so a bookmark cannot carry a spent one.
        response = web.HTTPFound("/dashboard")
        set_session(response, discord_id)
        return response

    discord_id = read_session(request)
    if not discord_id:
        return denied(request)

    response = private(aiohttp_jinja2.render_template("dashboard.html", request, {}))
    if time.time() - request.get("session_issued", 0) > REFRESH_AFTER:
        set_session(response, discord_id)

    return response


async def dashboard_stats(cog: "WebServer", request: web.Request) -> web.StreamResponse:
    """Return the dashboard's aggregates as JSON (GET /dashboard/stats)."""
    if not read_session(request):
        return error_response(DENIED, 401)

    return private(web.json_response(build_stats(cog)))


# Stats

def name_server(cog: "WebServer", server_id: str, remembered: dict[str, str]) -> str:
    """Return a server's name, falling back to the last one seen and then to its ID."""
    guild = cog.bot.get_guild(int(server_id)) if server_id.isdigit() else None
    if guild:
        return guild.name

    return remembered.get(server_id, server_id)


def build_stats(cog: "WebServer") -> dict:
    """Return every aggregate the dashboard renders."""
    totals = command_log.get_totals()
    remembered = servers.get_server_names()
    stats = {
        "totals": totals,
        "active": {
            "day": command_log.get_active_users(1),
            "week": command_log.get_active_users(7),
            "month": command_log.get_active_users(30),
        },
        "daily": command_log.get_daily_counts(),
        "topCommands": command_log.get_top_commands(12),
        "topServers": [
            dict(row, name=name_server(cog, row["serverId"], remembered))
            for row in command_log.get_top_servers(10)
        ],
        "mix": command_log.get_command_mix(),
        "newUsers": command_log.get_new_users_by_week(),
        "concentration": {
            "users": 10,
            "commands": command_log.get_concentration(10),
        },
        "generated": time.time(),
    }

    return stats
