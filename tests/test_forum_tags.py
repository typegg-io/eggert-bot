from types import SimpleNamespace

import pytest

from config import (
    BUG_FORUM_CHANNEL_ID,
    BUG_UNSOLVED_TAG,
    REVIEW_EXCLUDED_THREAD_IDS,
    SUGGESTION_FORUM_CHANNEL_ID,
    SUGGESTION_OPEN_TAG,
)
from utils.forum_tags import find_tag, is_unsolved, review_tag_name, tags_replacing, tags_with_review


def tag(name):
    return SimpleNamespace(name=name)


UNSOLVED = tag("Unsolved")
OPEN = tag("OPEN")
STAGED = tag("staged")
DEFERRED = tag("deferred")


# review_tag_name

@pytest.mark.parametrize(("parent_id", "expected"), [
    (BUG_FORUM_CHANNEL_ID, BUG_UNSOLVED_TAG),
    (SUGGESTION_FORUM_CHANNEL_ID, SUGGESTION_OPEN_TAG),
    (123, None),
    (None, None),
])
def test_review_tag_name_picks_the_forums_tag(parent_id, expected):
    assert review_tag_name(1, parent_id) == expected


@pytest.mark.parametrize("parent_id", [BUG_FORUM_CHANNEL_ID, SUGGESTION_FORUM_CHANNEL_ID])
@pytest.mark.parametrize("thread_id", sorted(REVIEW_EXCLUDED_THREAD_IDS))
def test_review_tag_name_skips_excluded_threads(thread_id, parent_id):
    assert review_tag_name(thread_id, parent_id) is None


def test_find_tag_ignores_case():
    assert find_tag([STAGED, UNSOLVED], "unsolved") is UNSOLVED
    assert find_tag([OPEN], "open") is OPEN
    assert find_tag([STAGED], "unsolved") is None


# tags_with_review

def test_tags_with_review_keeps_the_posters_tags():
    question = tag("question")
    assert tags_with_review([question], OPEN) == [question, OPEN]


def test_tags_with_review_tags_an_untagged_thread():
    assert tags_with_review([], UNSOLVED) == [UNSOLVED]


def test_tags_with_review_skips_a_thread_at_the_tag_limit():
    assert tags_with_review([tag(str(i)) for i in range(5)], UNSOLVED) is None


def test_tags_with_review_has_room_for_a_fifth():
    four = [tag(str(i)) for i in range(4)]
    assert tags_with_review(four, UNSOLVED) == [*four, UNSOLVED]


def test_tags_with_review_skips_an_already_tagged_thread():
    assert tags_with_review([UNSOLVED], UNSOLVED) is None


# tags_replacing

def test_tags_replacing_drops_unsolved_in_the_same_edit():
    other = tag("ios")
    assert tags_replacing([UNSOLVED, other], STAGED, "unsolved") == [other, STAGED]


def test_tags_replacing_does_not_duplicate_the_new_tag():
    assert tags_replacing([DEFERRED, UNSOLVED], DEFERRED, "unsolved") == [DEFERRED]


# is_unsolved

@pytest.mark.parametrize(("applied", "expected"), [
    ([], True),
    ([UNSOLVED], True),
    ([tag("UNSOLVED")], True),
    ([UNSOLVED, STAGED], False),
    ([DEFERRED], False),
])
def test_is_unsolved_exports_only_untouched_reports(applied, expected):
    assert is_unsolved(applied, "unsolved") is expected
