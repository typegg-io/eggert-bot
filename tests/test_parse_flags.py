"""Tests for flag parsing, which runs before dispatch on every command.

parse_flags strips flag tokens out of the message and returns the resolved Flags, the cleaned
command string that discord.py then parses, and the tokens the user actually typed.
"""

import pytest

from bot_setup import parse_flags


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


def test_language_forces_unranked_and_wpm():
    """Only English quotes are ranked, so any language flag implies unranked."""
    f = flags_for("-best fr")
    assert (f.status, f.metric) == ("unranked", "wpm")


def test_an_unrecognised_word_is_left_alone():
    assert cleaned("-best french") == "-best french"


# Quote ids

@pytest.mark.parametrize("token", ["^", "daily", "piykyai_3408"])
def test_quote_id_flag(token):
    assert flags_for(f"-r {token}").quote_id == token


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
