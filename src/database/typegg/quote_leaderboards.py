"""The cached top ten user IDs per quote."""

from database.typegg import db


def update_quote_leaderboards(quote_ids: list[str]) -> None:
    """Recompute the top 10 leaderboard rows for the given quote IDs."""
    if not quote_ids:
        return

    placeholders = ",".join("?" * len(quote_ids))

    db.run_transaction([
        (f"DELETE FROM quote_leaderboards WHERE quoteId IN ({placeholders})", quote_ids),
        (f"""
            INSERT INTO quote_leaderboards (quoteId, rank, userId)
            SELECT quoteId, rn, userId
            FROM (
                SELECT quoteId, userId,
                       ROW_NUMBER() OVER (
                           PARTITION BY quoteId
                           ORDER BY MAX(pp) DESC, MAX(wpm) DESC, MIN(timestamp) ASC
                       ) AS rn
                FROM races
                WHERE quoteId IN ({placeholders})
                GROUP BY userId, quoteId
            )
            WHERE rn <= 10
        """, quote_ids),
    ])


def remove_user_from_leaderboards(user_id: str) -> None:
    """Recompute the leaderboards of every quote a user appears on."""

    affected = db.fetch("SELECT DISTINCT quoteId FROM quote_leaderboards WHERE userId = ?", [user_id])
    quote_ids = [row["quoteId"] for row in affected]
    update_quote_leaderboards(quote_ids)
