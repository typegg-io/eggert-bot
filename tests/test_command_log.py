"""Tests for the command_log table and the helpers that read it."""

from database.bot import users


def log(discord_id, command, server_id="900", user_id=None):
    """Record one invocation through the public helper."""
    users.log_command(discord_id, user_id, command, server_id)


def test_log_command_writes_one_row(scratch_db):
    users.log_command("1", "u1", "stats", "900")

    rows = scratch_db.execute("SELECT * FROM command_log").fetchall()
    assert len(rows) == 1
    assert rows[0]["discordId"] == "1"
    assert rows[0]["userId"] == "u1"
    assert rows[0]["command"] == "stats"
    assert rows[0]["origin"] == "server"
    assert rows[0]["serverId"] == "900"
    assert rows[0]["timestamp"] > 0


def test_log_command_reads_the_origin_off_the_server(scratch_db):
    users.log_command("1", None, "stats", None)

    row = scratch_db.execute("SELECT origin, serverId FROM command_log").fetchone()
    assert (row["origin"], row["serverId"]) == ("dm", None)


def test_log_command_stringifies_the_discord_id(scratch_db):
    users.log_command(123, None, "stats", "900")

    assert scratch_db.execute("SELECT discordId FROM command_log").fetchone()[0] == "123"


def test_log_command_keeps_a_row_per_invocation(scratch_db):
    for _ in range(3):
        log("1", "stats")

    assert scratch_db.execute("SELECT COUNT(*) FROM command_log").fetchone()[0] == 3


def test_get_command_usage(scratch_db):
    log("1", "stats")
    log("1", "stats")
    log("1", "day")
    log("2", "stats")

    assert users.get_command_usage("1") == {"stats": 2, "day": 1}
    assert users.get_command_usage(1) == {"stats": 2, "day": 1}
    assert users.get_command_usage("3") == {}


def test_get_all_command_usage(scratch_db):
    log("1", "stats")
    log("2", "stats")
    log("2", "day")

    assert users.get_all_command_usage() == {"stats": 2, "day": 1}


def test_get_command_leaderboard_orders_by_usage(scratch_db):
    log("1", "stats")
    log("2", "stats")
    log("2", "stats")
    log("3", "day")

    assert users.get_command_leaderboard("stats") == [
        {"discord_id": "2", "usages": 2},
        {"discord_id": "1", "usages": 1},
    ]
    assert users.get_command_leaderboard("nothing") == []


def test_get_top_users_by_command_usage_orders_by_total(scratch_db):
    log("1", "stats")
    log("2", "stats")
    log("2", "day")

    assert users.get_top_users_by_command_usage() == [
        {"discord_id": "2", "total_commands": 2},
        {"discord_id": "1", "total_commands": 1},
    ]


def test_get_command_count(scratch_db):
    assert users.get_command_count() == 0

    log("1", "stats")
    log("2", "day")

    assert users.get_command_count() == 2


def test_migrate_command_name_merges_into_the_new_name(scratch_db):
    log("1", "top")
    log("1", "top")
    log("1", "bestgraph")
    log("2", "top")
    log("3", "day")

    assert users.migrate_command_name("top", "bestgraph") == 2
    assert users.get_all_command_usage() == {"bestgraph": 4, "day": 1}


def test_migrate_command_name_reports_no_users_when_unused(scratch_db):
    log("1", "stats")

    assert users.migrate_command_name("nothing", "bestgraph") == 0
    assert users.get_all_command_usage() == {"stats": 1}
