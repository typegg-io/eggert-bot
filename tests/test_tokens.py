"""Tests for the spent token store behind the verify and dashboard routes."""

from datetime import timedelta

from utils.dates import now
from web_server.tokens import UsedTokens


def test_a_spent_token_stays_spent():
    tokens = UsedTokens()
    tokens["abc"] = now() + timedelta(minutes=10)

    assert "abc" in tokens


def test_an_unspent_token_is_absent():
    assert "abc" not in UsedTokens()


def test_an_expired_token_is_forgotten():
    tokens = UsedTokens()
    tokens["abc"] = now() - timedelta(seconds=1)

    assert "abc" not in tokens
    assert len(tokens) == 0


def test_pruning_keeps_the_tokens_that_still_matter():
    tokens = UsedTokens()
    tokens["fresh"] = now() + timedelta(minutes=10)
    tokens["stale"] = now() - timedelta(minutes=10)

    assert len(tokens) == 1
    assert "fresh" in tokens
