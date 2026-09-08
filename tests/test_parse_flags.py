"""Tests for flag parsing, which runs before dispatch on every command.

parse_flags strips flag tokens out of the message and returns the resolved Flags, the cleaned
command string that discord.py then parses, and the tokens the user actually typed.
"""

import pytest

from bot_setup import parse_flags
from utils.flags import Language, apply_universe_status, resolve_universe, universe_code


def flags_for(content):
    """Return just the Flags for a message."""
    return parse_flags(content)[0]


def cleaned(content):
    """Return just the cleaned command string, stripped."""
    return parse_flags(content)[1].strip()


def explicit(content):
    """Return just the set of flag names the user typed."""
    return set(parse_flags(content)[2])


# Defaults

def test_defaults_when_no_flags_are_given():
    f = flags_for("-best")
    assert (f.metric, f.raw, f.gamemode, f.status) == ("pp", False, None, "ranked")
    assert (f.number, f.number_range, f.language, f.quote_id) == (None,) * 4


def test_date_is_always_resolved_even_when_absent():
    """Flags.date defaults to None, but parse_flags runs parse_date over it unconditionally.

    Commands reading ctx.flags.date therefore never see None, they see now().
    """
    from datetime import datetime

    assert isinstance(flags_for("-best").date, datetime)


def test_no_flags_means_no_explicit_flags():
    assert explicit("-best keegant") == set()


# Individual flags

def test_raw_flag():
    assert flags_for("-best raw").raw is True


@pytest.mark.parametrize("token", ["solo", "quickplay", "lobby"])
def test_gamemode_flags(token):
    assert flags_for(f"-best {token}").gamemode == token


def test_gamemode_accepts_an_alias():
    assert flags_for("-best qp").gamemode == "quickplay"


@pytest.mark.parametrize("token", ["ranked", "unranked", "any"])
def test_status_flags(token):
    assert flags_for(f"-best {token}").status == token


def test_metric_flag_survives_only_while_ranked():
    assert flags_for("-best pp").metric == "pp"


def test_metric_falls_back_to_wpm_when_not_ranked():
    """pp is meaningless outside ranked races, so the parser forces wpm."""
    assert flags_for("-best pp unranked").metric == "wpm"
    assert flags_for("-best pp any").metric == "wpm"


# Numbers

@pytest.mark.parametrize(("token", "expected"), [
    ("500", 500),
    ("-500", -500),
    ("1,234", 1234),
    ("2k", 2000),
    ("1.5k", 1500),
])
def test_number_flag(token, expected):
    assert flags_for(f"-best {token}").number == expected


def test_underscores_are_not_treated_as_a_number():
    """1_000 is valid Python but is a username here, not a count."""
    assert flags_for("-best 1_000").number is None


@pytest.mark.parametrize(("token", "expected"), [
    (">150", (150.0, None)),
    ("<120", (None, 120.0)),
    ("100-150", (100.0, 150.0)),
])
def test_number_range_flag(token, expected):
    assert flags_for(f"-best {token}").number_range == expected


# Languages

def test_language_is_an_iso_code_not_a_name():
    """Language flags come from the LANGUAGES keys, so 'fr' is a flag and 'french' is not."""
    assert flags_for("-best fr").language is not None
    assert flags_for("-best french").language is None


def test_a_language_flag_no_longer_decides_status():
    """A universe resolves after the user loads, so parsing leaves status alone."""
    f = flags_for("-best fr")
    assert (f.status, f.metric) == ("ranked", "pp")


def test_a_universe_keeps_its_ranked_pool():
    """French is a universe, so its quotes stay ranked and scored in pp."""
    f = flags_for("-best fr")
    apply_universe_status(f)
    assert (f.status, f.metric) == ("ranked", "pp")


def test_a_language_without_a_universe_is_unranked():
    """Latin has no universe, so its quotes are unranked and scored in wpm."""
    f = flags_for("-best la")
    apply_universe_status(f)
    assert (f.status, f.metric) == ("unranked", "wpm")


def test_an_explicit_ranked_survives_a_universe():
    """A universe does not override a typed status the way a plain language does."""
    f = flags_for("-best fr -ranked")
    apply_universe_status(f)
    assert f.status == "ranked"


def test_only_registered_codes_are_universes():
    """A universe is a language with its own ranked pool, which Latin does not have."""
    assert Language("fr").is_universe
    assert Language("vi").is_universe
    assert not Language("la").is_universe


def test_a_non_universe_language_sends_no_universe_code():
    """The API 400s on a code outside the registry rather than falling back to English."""
    assert universe_code(flags_for("-best la")) is None


def test_a_universe_sends_its_code():
    assert universe_code(flags_for("-best fr")) == "fr"


def test_a_typed_universe_beats_the_stored_one():
    assert resolve_universe(flags_for("-best fr"), "de") == Language("fr")


def test_a_stored_universe_applies_with_nothing_typed():
    assert resolve_universe(flags_for("-best"), "de") == Language("de")


def test_a_stored_english_universe_reads_as_no_universe():
    """English is the default world, so storing it leaves titles and queries untouched."""
    assert resolve_universe(flags_for("-best"), "en") is None


def test_an_unrecognised_word_is_left_alone():
    assert cleaned("-best french") == "-best french"


# Quote ids

@pytest.mark.parametrize("token", ["^", "daily"])
def test_quote_id_keywords(token):
    assert flags_for(f"-r {token}").quote_id == token


def test_a_real_quote_id_is_recognised(monkeypatch):
    """is_quote_id queries the quotes table, so this branch is stubbed to stay database free.

    parse_flags therefore runs one SELECT per unrecognised token on every command invocation.
    """
    import bot_setup

    monkeypatch.setattr(bot_setup, "is_quote_id", lambda token: token == "piykyai_3408")
    assert flags_for("-r piykyai_3408").quote_id == "piykyai_3408"


def test_an_unknown_token_is_not_a_quote_id(monkeypatch):
    import bot_setup

    monkeypatch.setattr(bot_setup, "is_quote_id", lambda token: False)
    assert flags_for("-r keegant").quote_id is None


# Stripping and reporting

def test_flags_are_stripped_from_the_command():
    assert cleaned("-best keegant raw solo") == "-best keegant"


def test_argument_order_does_not_matter():
    def without_date(f):
        return {k: v for k, v in f.__dict__.items() if k != "date"}

    assert without_date(flags_for("-best raw solo 500")) == without_date(flags_for("-best 500 solo raw"))


def test_explicit_flags_report_what_the_user_typed():
    assert explicit("-best keegant raw solo") == {"raw", "gamemode"}


def test_explicit_flags_exclude_defaults_the_user_did_not_type():
    """cog_before_invoke warns on unsupported flags, so silent defaults must not appear here."""
    assert "metric" not in explicit("-best raw")
    assert "status" not in explicit("-best raw")


# Date ranges

def test_two_dates_are_kept_in_the_order_typed():
    f = flags_for("-best 9/1/2025 9/1/2026")
    assert [date.year for date in f.dates] == [2025, 2026]


def test_one_date_still_lands_in_the_single_date_flag():
    f = flags_for("-d keegant 2024-01-01")
    assert f.date.year == 2024
    assert len(f.dates) == 1


def test_one_date_reports_the_date_flag_not_the_range():
    assert explicit("-d keegant 2024-01-01") == {"date"}


def test_two_dates_report_the_range_flag():
    assert explicit("-best 9/1/2025 9/1/2026") == {"date_range"}


def test_a_period_keyword_reports_the_range_flag():
    f = flags_for("-best year")
    assert f.period == "year"
    assert explicit("-best year") == {"date_range"}


def test_period_keywords_accept_their_aliases():
    assert flags_for("-best yr").period == "year"
    assert flags_for("-best mo").period == "month"


def test_dates_are_stripped_from_the_command():
    assert cleaned("-best keegant 9/1/2025 9/1/2026") == "-best keegant"


def test_a_bare_year_is_still_a_number():
    """parse_number runs before is_date_like, so -best 2025 asks for 2025 races."""
    f = flags_for("-best 2025")
    assert f.number == 2025
    assert f.dates == ()


def test_period_keywords_accept_their_single_letter_aliases():
    for alias, period in [("d", "day"), ("w", "week"), ("m", "month"), ("y", "year")]:
        assert flags_for(f"-imp {alias}").period == period
