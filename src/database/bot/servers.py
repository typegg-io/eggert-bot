"""Names for the servers the bot has run commands in."""

from database.bot import db
from utils import dates


def remember_server(server_id: str, name: str) -> None:
    """Record a server's current name, replacing the one held before."""
    db.run("""
        INSERT INTO servers (serverId, name, lastSeen) VALUES (?, ?, ?)
        ON CONFLICT (serverId) DO UPDATE SET name = excluded.name, lastSeen = excluded.lastSeen
    """, [str(server_id), name, dates.now().timestamp()])


def get_server_names() -> dict[str, str]:
    """Return every remembered server name, keyed by server ID."""
    return {row["serverId"]: row["name"] for row in db.fetch("SELECT serverId, name FROM servers")}
