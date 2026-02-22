from database.bot import db
from utils import dates


def add_art(title: str, image_url: str, author_discord_id: str):
    """Add a new piece of art to the database."""
    timestamp = dates.now().timestamp()

    db.run("""
        INSERT INTO art (title, image_url, author_id, timestamp)
        VALUES (?, ?, ?, ?)
    """, [title, image_url, author_discord_id, timestamp])


def get_art_by_title(title: str):
    """Get a specific piece of art by exact title."""
    result = db.fetch_one("""
        SELECT * FROM art
        WHERE title = ?
    """, [title])

    return dict(result) if result else None


def get_all_art():
    """Get all pieces of art."""
    results = db.fetch("""
        SELECT * FROM art
        ORDER BY timestamp DESC
    """)

    return [dict(row) for row in results]


def get_art_by_author(author_id: str):
    """Get all art submitted by a specific author."""
    results = db.fetch("""
        SELECT * FROM art
        WHERE author_id = ?
        ORDER BY timestamp DESC
    """, [author_id])

    return [dict(row) for row in results]


def get_random_art():
    """Get a random piece of art."""
    result = db.fetch_one("""
        SELECT * FROM art
        ORDER BY RANDOM()
        LIMIT 1
    """)

    return dict(result) if result else None


def delete_art(title: str):
    """Delete a piece of art by title."""
    db.run("""
        DELETE FROM art
        WHERE title = ?
    """, [title])


def art_exists(title: str) -> bool:
    """Check if art with the given title exists."""
    result = db.fetch_one("""
        SELECT 1 FROM art
        WHERE title = ?
    """, [title])

    return result is not None
