"""Which unraced quotes -unraced recommends, and in what order."""

from commands.quotes.unraced import in_length_range, recommend


def make_quote(quote_id: str, length: int, complexity: float = 5.0, difficulty: float = 5.0) -> dict:
    """Return a ranked quote row of the given shape."""
    return {"quoteId": quote_id, "text": "a" * length, "complexity": complexity, "difficulty": difficulty}


POOL = [
    *[make_quote(f"short{i}", 50 + i, 2.0 + i / 10, 3.0 + i / 10) for i in range(10)],
    *[make_quote(f"long{i}", 2000 + i, 7.0 + i / 10, 8.0 + i / 10) for i in range(10)],
]


def best(quote_id: str) -> dict:
    """Return a quote best on one quote."""
    return {"quoteId": quote_id, "pp": 100.0}


def test_raced_quotes_are_never_recommended():
    """Every unraced quote is listed once, and no raced one is."""
    raced = {"short0", "short1", "long0"}

    recommendations = [quote["quoteId"] for quote in recommend(POOL, [best("short0")], raced)]

    assert sorted(recommendations) == sorted(quote["quoteId"] for quote in POOL if quote["quoteId"] not in raced)


def first_recommendation(quote_ids: list[str]) -> str:
    """Return the top recommendation for a user whose pp comes from these quotes, in order."""
    return recommend(POOL, [best(quote_id) for quote_id in quote_ids], set(quote_ids))[0]["quoteId"]


def test_the_quote_most_like_the_users_pp_comes_first():
    """The top recommendation neighbours the quotes a user's pp comes from."""
    assert first_recommendation(["long4", "long5"]).startswith("long")
    assert first_recommendation(["short4", "short5"]).startswith("short")


def test_a_users_best_pp_leads_the_order():
    """Between two equally lone bests, the one worth more pp decides the top recommendation."""
    assert first_recommendation(["long5", "short5"]).startswith("long")
    assert first_recommendation(["short5", "long5"]).startswith("short")


def test_a_best_on_a_quote_outside_the_pool_is_ignored():
    """A quote that has since left the ranked pool does not break the scoring."""
    quote_bests = [best("unranked-now"), best("long0")]

    recommendations = recommend(POOL, quote_bests, {"long0"})

    assert recommendations[0]["quoteId"].startswith("long")


def test_a_length_range_keeps_its_low_end_and_drops_its_high_end():
    """The range matches the one -best filters by, so `50-100c` holds 50 but not 100."""
    assert in_length_range(make_quote("low", 50), (50, 100))
    assert not in_length_range(make_quote("high", 100), (50, 100))
    assert in_length_range(make_quote("open", 5000), (250, None))
    assert not in_length_range(make_quote("under", 99), (None, 50))
