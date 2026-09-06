"""Tests for the per-channel recent quote memory."""

from config import STATS_CHANNEL_ID
from database.bot import recent_quotes


def test_a_channel_reads_back_its_own_quote(scratch_db):
    recent_quotes.set_recent_quote("500", "abc_1")

    assert recent_quotes.get_recent_quote("500") == "abc_1"


def test_setting_twice_replaces_the_quote(scratch_db):
    recent_quotes.set_recent_quote("500", "abc_1")
    recent_quotes.set_recent_quote("500", "abc_2")

    assert recent_quotes.get_recent_quote("500") == "abc_2"


def test_an_unseen_channel_falls_back_to_the_stats_channel(scratch_db):
    recent_quotes.set_recent_quote(STATS_CHANNEL_ID, "abc_1")

    assert recent_quotes.get_recent_quote("500") == "abc_1"


def test_no_quote_anywhere_reads_as_none(scratch_db):
    assert recent_quotes.get_recent_quote("500") is None


def test_the_stats_channel_itself_does_not_recurse(scratch_db):
    assert recent_quotes.get_recent_quote(STATS_CHANNEL_ID) is None
