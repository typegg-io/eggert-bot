def calculate_total_pp(quote_bests: list[dict]):
    """Returns the total performance given a list of quote bests."""
    return sum(q["pp"] * (0.97 ** i) for i, q in enumerate(quote_bests))
