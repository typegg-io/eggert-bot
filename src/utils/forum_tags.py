"""Pure decisions about which forum tags a thread should carry."""

from collections.abc import Sequence

from config import REVIEW_EXCLUDED_THREAD_IDS, REVIEW_TAGS

# Discord rejects a thread edit that applies more than five tags.
MAX_APPLIED_TAGS = 5


def find_tag(available: Sequence, name: str):
    """Return the tag called name, ignoring case, or None."""
    return next((tag for tag in available if tag.name.lower() == name.lower()), None)


def review_tag_name(thread_id: int, parent_id: int | None) -> str | None:
    """Return the review tag a thread gets, or None for other channels and excluded threads."""
    if thread_id in REVIEW_EXCLUDED_THREAD_IDS:
        return None
    return REVIEW_TAGS.get(parent_id)


def tags_with_review(applied: Sequence, tag) -> list | None:
    """Return the applied tags plus tag, or None when it is already there or there is no room."""
    if tag in applied or len(applied) >= MAX_APPLIED_TAGS:
        return None
    return [*applied, tag]


def tags_replacing(applied: Sequence, tag, remove_name: str) -> list:
    """Return the applied tags with remove_name dropped and tag added."""
    kept = [t for t in applied if t.name.lower() != remove_name.lower()]
    return kept if tag in kept else [*kept, tag]


def is_unsolved(applied: Sequence, unsolved_name: str) -> bool:
    """Return whether every applied tag is the unsolved tag, which includes having none."""
    return all(t.name.lower() == unsolved_name.lower() for t in applied)
