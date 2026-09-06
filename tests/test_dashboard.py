"""Tests for the dashboard's aggregates and its token and session handling."""

import time
import types

import jwt
import pytest
from aiohttp import web
from aiohttp.test_utils import make_mocked_request

from api import verification
from database.bot import command_log, servers, users
from web_server.routes import dashboard

SECRET = "test-secret"


@pytest.fixture(autouse=True)
def signing_key(monkeypatch):
    """Sign every token in these tests with a known key rather than the deployed one."""
    monkeypatch.setattr(dashboard, "SECRET", SECRET)
    monkeypatch.setattr(verification, "SECRET", SECRET)


@pytest.fixture
def admin(monkeypatch):
    """Treat Discord ID 1 as an admin and everyone else as not."""
    monkeypatch.setattr(dashboard, "get_user", lambda discord_id, auto_insert=True: {"isAdmin": discord_id == "1"})


@pytest.fixture
def cog():
    """Return a stand-in for the web server cog, carrying only its used token map."""
    return types.SimpleNamespace(used_tokens={})


def request_with_session(cookie: str) -> web.Request:
    """Return a mocked GET carrying a dashboard session cookie."""
    return make_mocked_request("GET", "/dashboard", headers={"Cookie": f"{dashboard.COOKIE_NAME}={cookie}"})


def issue_session(discord_id: str = "1") -> str:
    """Return the session cookie set_session would hand a browser."""
    response = web.Response()
    dashboard.set_session(response, discord_id)
    return response.cookies[dashboard.COOKIE_NAME].value


def link_token(discord_id: str = "1") -> str:
    """Return the single-use token the -dashboard command puts in a link."""
    return verification.generate_dashboard_link(discord_id).split("token=")[1]


# Sessions

def test_session_round_trip(admin):
    assert dashboard.read_session(request_with_session(issue_session())) == "1"


def test_session_cookie_is_locked_down():
    response = web.Response()
    dashboard.set_session(response, "1")
    cookie = response.cookies[dashboard.COOKIE_NAME]

    assert cookie["httponly"]
    assert cookie["secure"]
    assert cookie["samesite"] == "Lax"
    assert cookie["path"] == "/dashboard"
    assert int(cookie["max-age"]) == dashboard.SESSION_SECONDS


def test_no_cookie_is_no_session():
    assert dashboard.read_session(make_mocked_request("GET", "/dashboard")) is None


def test_session_rejects_another_signing_key(admin):
    cookie = jwt.encode(
        {"discordId": "1", "scope": dashboard.SESSION_SCOPE, "exp": time.time() + 60}, "other", algorithm="HS256"
    )

    assert dashboard.read_session(request_with_session(cookie)) is None


def test_session_rejects_an_expired_cookie(admin):
    cookie = jwt.encode(
        {"discordId": "1", "scope": dashboard.SESSION_SCOPE, "exp": time.time() - 1}, SECRET, algorithm="HS256"
    )

    assert dashboard.read_session(request_with_session(cookie)) is None


def test_session_rejects_a_verification_token(admin):
    """A verification token names the same Discord ID, so only its scope keeps it out."""
    assert dashboard.read_session(request_with_session(verification.generate_jwt("1"))) is None


def test_session_rejects_a_link_token(admin):
    assert dashboard.read_session(request_with_session(link_token())) is None


def test_session_dies_when_admin_is_revoked(admin, monkeypatch):
    cookie = issue_session()
    monkeypatch.setattr(dashboard, "get_user", lambda discord_id, auto_insert=True: {"isAdmin": 0})

    assert dashboard.read_session(request_with_session(cookie)) is None


# Link tokens

def test_redeem_returns_the_admin(admin, cog):
    assert dashboard.redeem_token(cog, link_token()) == "1"


def test_redeem_burns_the_token(admin, cog):
    token = link_token()

    assert dashboard.redeem_token(cog, token) == "1"
    assert dashboard.redeem_token(cog, token) is None


def test_redeem_rejects_a_non_admin(admin, cog):
    assert dashboard.redeem_token(cog, link_token("2")) is None
    assert cog.used_tokens == {}


def test_redeem_rejects_a_verification_token(admin, cog):
    assert dashboard.redeem_token(cog, verification.generate_jwt("1")) is None


def test_redeem_rejects_a_session_cookie(admin, cog):
    assert dashboard.redeem_token(cog, issue_session()) is None


def test_link_expires_within_the_advertised_window():
    payload = jwt.decode(link_token(), SECRET, algorithms=["HS256"])

    assert payload["exp"] - time.time() <= verification.DASHBOARD_MINUTES * 60


# Aggregates

def log_at(connection, discord_id, command, days_ago, server_id="900", user_id=None):
    """Insert one dated invocation directly, since log_command always stamps now."""
    connection.execute("""
        INSERT INTO command_log (discordId, userId, command, origin, serverId, timestamp)
        VALUES (?, ?, ?, ?, ?, strftime('%s', 'now') - ? * 86400)
    """, [discord_id, user_id, command, "server" if server_id else "dm", server_id, days_ago])
    connection.commit()


def test_get_totals_counts_origins_and_links(scratch_db):
    users.log_command("1", "u1", "stats", "900")
    users.log_command("1", None, "day", None)
    users.log_command("2", "u2", "stats", None)

    totals = command_log.get_totals()

    assert totals["commands"] == 3
    assert totals["users"] == 2
    assert totals["distinctCommands"] == 2
    assert totals["dm"] == 2
    assert totals["linked"] == 2


def test_get_totals_on_an_empty_table(scratch_db):
    totals = command_log.get_totals()

    assert totals["commands"] == 0
    assert totals["firstSeen"] is None


def test_get_daily_counts_buckets_by_day(scratch_db):
    log_at(scratch_db, "1", "stats", 1)
    log_at(scratch_db, "2", "stats", 1)
    log_at(scratch_db, "1", "day", 3)

    daily = command_log.get_daily_counts(7)

    assert [row["commands"] for row in daily] == [1, 2]
    assert [row["users"] for row in daily] == [1, 2]


def test_get_daily_counts_drops_undated_rows(scratch_db):
    scratch_db.execute("""
        INSERT INTO command_log (discordId, command, origin, timestamp) VALUES ('1', 'stats', 'dm', NULL)
    """)
    scratch_db.commit()

    assert command_log.get_daily_counts(7) == []


def test_get_daily_counts_honours_the_window(scratch_db):
    log_at(scratch_db, "1", "stats", 2)
    log_at(scratch_db, "1", "stats", 40)

    assert len(command_log.get_daily_counts(7)) == 1
    assert len(command_log.get_daily_counts(90)) == 2


def test_get_daily_counts_defaults_to_all_time(scratch_db):
    log_at(scratch_db, "1", "stats", 2)
    log_at(scratch_db, "1", "stats", 5000)

    assert len(command_log.get_daily_counts()) == 2


def log_at_time(connection, discord_id, moment):
    """Insert one invocation stamped at a UTC wall clock time."""
    connection.execute("""
        INSERT INTO command_log (discordId, command, origin, serverId, timestamp)
        VALUES (?, 'stats', 'server', '900', CAST(strftime('%s', ?) AS REAL))
    """, [discord_id, moment])
    connection.commit()


def test_get_hourly_counts_buckets_by_utc_hour(scratch_db):
    log_at_time(scratch_db, "1", "2026-03-04 07:30:00")
    log_at_time(scratch_db, "2", "2026-03-05 07:59:59")
    log_at_time(scratch_db, "1", "2026-03-04 23:00:00")

    counts = {row["hour"]: row["commands"] for row in command_log.get_hourly_counts()}

    assert counts[7] == 2
    assert counts[23] == 1
    assert sum(counts.values()) == 3


def test_get_hourly_counts_covers_every_hour(scratch_db):
    hourly = command_log.get_hourly_counts()

    assert [row["hour"] for row in hourly] == list(range(24))
    assert sum(row["commands"] for row in hourly) == 0


def test_get_hourly_counts_drops_undated_rows(scratch_db):
    scratch_db.execute("""
        INSERT INTO command_log (discordId, command, origin, timestamp) VALUES ('1', 'stats', 'dm', NULL)
    """)
    scratch_db.commit()

    assert sum(row["commands"] for row in command_log.get_hourly_counts()) == 0


def test_get_active_users_counts_distinct_users_in_the_window(scratch_db):
    log_at(scratch_db, "1", "stats", 0)
    log_at(scratch_db, "1", "day", 0)
    log_at(scratch_db, "2", "stats", 20)

    assert command_log.get_active_users(1) == 1
    assert command_log.get_active_users(30) == 2


def test_get_top_commands_orders_by_usage(scratch_db):
    for _ in range(3):
        users.log_command("1", None, "stats", "900")
    users.log_command("1", None, "day", "900")

    assert command_log.get_top_commands(1) == [{"command": "stats", "total": 3}]


def test_get_command_mix_pools_the_tail_into_other(scratch_db):
    log_at(scratch_db, "1", "stats", 1)
    log_at(scratch_db, "1", "stats", 1)
    log_at(scratch_db, "1", "day", 1)

    mix = command_log.get_command_mix(weeks=4, commands=1)

    assert mix["buckets"] == ["stats", "other"]
    assert len(mix["weeks"]) == 1
    assert mix["series"]["stats"] == [2]
    assert mix["series"]["other"] == [1]


def test_get_command_mix_pads_a_week_a_bucket_missed(scratch_db):
    log_at(scratch_db, "1", "stats", 1)
    log_at(scratch_db, "1", "stats", 1)
    log_at(scratch_db, "1", "day", 15)

    mix = command_log.get_command_mix(weeks=8, commands=1)

    assert len(mix["weeks"]) == 2
    assert sum(mix["series"]["stats"]) == 2
    assert all(len(series) == 2 for series in mix["series"].values())


def test_get_command_mix_on_an_empty_table(scratch_db):
    assert command_log.get_command_mix() == {"weeks": [], "buckets": [], "series": {}}


def test_get_concentration_sums_the_busiest_users(scratch_db):
    for _ in range(5):
        users.log_command("1", None, "stats", "900")
    for _ in range(3):
        users.log_command("2", None, "stats", "900")
    users.log_command("3", None, "stats", "900")

    assert command_log.get_concentration(2) == 8
    assert command_log.get_concentration(10) == 9


def test_get_concentration_on_an_empty_table(scratch_db):
    assert command_log.get_concentration(10) == 0


def test_get_top_servers_ranks_by_commands_and_excludes_dms(scratch_db):
    log_at(scratch_db, "1", "stats", 1, server_id="900")
    log_at(scratch_db, "2", "stats", 1, server_id="900")
    log_at(scratch_db, "1", "day", 1, server_id="901")
    log_at(scratch_db, "1", "day", 1, server_id=None)

    assert command_log.get_top_servers() == [
        {"serverId": "900", "total": 2, "users": 2},
        {"serverId": "901", "total": 1, "users": 1},
    ]


def test_week_of_buckets_to_the_sunday_that_starts_the_week(scratch_db):
    for day in ("2026-08-19", "2026-08-22", "2026-08-23", "2026-08-24"):
        scratch_db.execute("""
            INSERT INTO command_log (discordId, command, origin, timestamp)
            VALUES ('1', 'stats', 'server', strftime('%s', ?))
        """, [day])
    scratch_db.commit()

    weeks = command_log.get_command_mix()["weeks"]

    # The 23rd is itself a Sunday, so it opens a week rather than closing the one before.
    assert weeks == ["2026-08-16", "2026-08-23"]


def test_get_command_mix_defaults_to_all_time(scratch_db):
    log_at(scratch_db, "1", "stats", 2)
    log_at(scratch_db, "1", "stats", 5000)

    assert len(command_log.get_command_mix()["weeks"]) == 2
    assert len(command_log.get_command_mix(weeks=4)["weeks"]) == 1


def test_get_new_users_by_week_defaults_to_all_time(scratch_db):
    log_at(scratch_db, "1", "stats", 2)
    log_at(scratch_db, "2", "stats", 5000)

    assert len(command_log.get_new_users_by_week()) == 2
    assert len(command_log.get_new_users_by_week(4)) == 1


def test_get_new_users_by_week_counts_first_commands(scratch_db):
    log_at(scratch_db, "1", "stats", 1)
    log_at(scratch_db, "1", "stats", 20)
    log_at(scratch_db, "2", "stats", 20)

    weeks = command_log.get_new_users_by_week(8)

    assert sum(row["users"] for row in weeks) == 2
    assert len(weeks) == 1


# Server names

def test_remember_server_keeps_the_latest_name(scratch_db):
    servers.remember_server("900", "Old Name")
    servers.remember_server("900", "New Name")

    assert servers.get_server_names() == {"900": "New Name"}


def test_get_server_names_on_an_empty_table(scratch_db):
    assert servers.get_server_names() == {}


def guild_cog(guilds: dict) -> types.SimpleNamespace:
    """Return a stand-in cog whose bot sees only the given guilds."""
    return types.SimpleNamespace(bot=types.SimpleNamespace(
        get_guild=lambda server_id: guilds.get(server_id),
    ))


def test_name_server_prefers_the_live_guild(scratch_db):
    cog = guild_cog({900: types.SimpleNamespace(name="Live Name")})

    assert dashboard.name_server(cog, "900", {"900": "Stale Name"}) == "Live Name"


def test_name_server_falls_back_to_the_remembered_name(scratch_db):
    assert dashboard.name_server(guild_cog({}), "900", {"900": "Remembered"}) == "Remembered"


def test_name_server_falls_back_to_the_id(scratch_db):
    assert dashboard.name_server(guild_cog({}), "900", {}) == "900"
