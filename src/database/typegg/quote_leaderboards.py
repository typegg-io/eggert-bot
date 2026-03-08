from database.typegg import db


def get_quote_leaderboard(quote_id: str):
    """Fetch the top 10 leaderboard for a quote."""
    return db.fetch("""
        SELECT ql.rank, ql.userId, u.username, u.country
        FROM quote_leaderboards ql
        LEFT JOIN users u ON u.userId = ql.userId
        WHERE ql.quoteId = ?
        ORDER BY ql.rank
    """, [quote_id])


def update_quote_leaderboards(quote_ids: list[str]):
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
                       ROW_NUMBER() OVER (PARTITION BY quoteId ORDER BY MAX(pp) DESC, MAX(wpm) DESC, MIN(timestamp) ASC) AS rn
                FROM races
                WHERE quoteId IN ({placeholders})
                GROUP BY userId, quoteId
            )
            WHERE rn <= 10
        """, quote_ids),
    ])


def remove_user_from_leaderboards(user_id: str):
    """Recompute leaderboards for all quotes a user appeared in, then remove their races."""
    from database.typegg.races import delete_races

    affected = db.fetch("SELECT DISTINCT quoteId FROM quote_leaderboards WHERE userId = ?", [user_id])
    quote_ids = [row["quoteId"] for row in affected]
    delete_races(user_id)
    update_quote_leaderboards(quote_ids)
