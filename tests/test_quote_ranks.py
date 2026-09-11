"""A quote rank shows its lead over the next racer, and the header counts the placements held."""

from commands.quotes.quoteranks import lead_display, placement_line


def test_a_lead_is_shown_in_pp():
    """The API sends the margin in pp, floored to two decimals."""
    assert lead_display(12.3) == "+12.30 pp ahead"


def test_a_zero_margin_is_a_tie():
    """Two racers on the same pp share a position and leave no gap."""
    assert lead_display(0) == "Tied"


def test_a_null_margin_means_no_one_is_below():
    """The API sends null when nobody sits at or below the user's best."""
    assert lead_display(None) == "No one below"


def test_the_header_leaves_out_a_zero_count():
    """A user with no firsts sees only the placements they hold."""
    stats = {"firsts": 0, "podiums": 1934, "topTens": 3778}

    assert placement_line(stats) == "**Podiums:** 1,934 | **Top 10s:** 3,778"


def test_the_header_is_empty_with_no_placements():
    """Three zeros leave nothing worth a header line."""
    assert placement_line({"firsts": 0, "podiums": 0, "topTens": 0}) == ""
