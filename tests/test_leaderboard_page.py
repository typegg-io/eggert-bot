"""The page every leaderboard opens on, the top 10 or the caller's own, and which presses save it."""

import asyncio
from types import SimpleNamespace

import pytest

from database.bot.users import add_user, get_user, update_leaderboard_page
from utils.messages import Message, Page, paginate_leaderboard

DISCORD_ID = "1"


@pytest.fixture
def caller(scratch_db) -> None:
    """Insert the caller with default settings."""
    add_user(DISCORD_ID)


def stored_page() -> str:
    """Return the caller's saved leaderboard page."""
    return get_user(DISCORD_ID)["leaderboardPage"]


def make_message(jump_page: int | None) -> Message:
    """Return a built three-page leaderboard message for the caller as they are stored."""
    ctx = SimpleNamespace(author=SimpleNamespace(id=int(DISCORD_ID)), user=get_user(DISCORD_ID))
    message = Message(ctx, pages=[Page() for _ in range(3)], jump_page=jump_page, remember=True)
    message.build_embeds()
    return message


def press(user_id: str = DISCORD_ID) -> SimpleNamespace:
    """Return an interaction from one user whose responses do nothing."""

    async def respond(**kwargs) -> None:
        """Accept an edit or a defer."""

    return SimpleNamespace(
        user=SimpleNamespace(id=int(user_id)),
        response=SimpleNamespace(is_done=lambda: False, edit_message=respond, defer=respond),
    )


# Opening page


def test_a_new_user_opens_on_their_own_position(caller):
    """A user who never chose opens on their page, and on the top 10 when they did not place."""

    async def run() -> list[int]:
        """Build one message per jump page and report where each opens."""
        return [make_message(jump_page).page_index for jump_page in [2, None]]

    assert asyncio.run(run()) == [2, 0]


def test_a_user_who_chose_the_top_opens_there(caller):
    """A stored 'top' opens on the first page even when the caller placed."""
    update_leaderboard_page(DISCORD_ID, "top")

    async def run() -> int:
        """Build the message and report its opening page."""
        return make_message(jump_page=2).page_index

    assert asyncio.run(run()) == 0


# Saving


def test_the_last_page_chosen_is_saved(caller):
    """The last of several presses is the one saved."""

    async def run() -> None:
        """Press the top, the caller's page, then the top."""
        message = make_message(jump_page=2)
        await message.first(press())
        await message.jump(press())
        await message.first(press())

    asyncio.run(run())

    assert stored_page() == "top"


def test_the_next_leaderboard_opens_on_a_choice_before_the_buttons_expire(caller):
    """A press saves at once, so a leaderboard run while the last one is live opens on it."""
    update_leaderboard_page(DISCORD_ID, "top")

    async def run() -> int:
        """Press the caller's page, then open a second leaderboard."""
        await make_message(jump_page=2).jump(press())
        return make_message(jump_page=1).page_index

    assert asyncio.run(run()) == 1


def test_your_position_on_the_top_page_is_still_a_choice(caller):
    """A caller in the top 10 who presses 👤 wants their position on every other leaderboard."""
    update_leaderboard_page(DISCORD_ID, "top")

    async def run() -> None:
        """Press the caller's page while already on it."""
        await make_message(jump_page=0).jump(press())

    asyncio.run(run())

    assert stored_page() == "me"


def test_a_caller_who_did_not_place_keeps_their_choice(caller):
    """Browsing back to the top of a leaderboard the caller is missing from saves nothing."""

    async def run() -> None:
        """Page forward and back to the top."""
        message = make_message(jump_page=None)
        await message.next(press())
        await message.first(press())

    asyncio.run(run())

    assert stored_page() == "me"


def test_another_users_press_is_not_a_choice(caller):
    """Only the caller's presses count."""

    async def run() -> None:
        """Press the top as someone else."""
        await make_message(jump_page=2).first(press(user_id="2"))

    asyncio.run(run())

    assert stored_page() == "me"


# Leaderboard pages


def format_row(index: int, score: dict) -> str:
    """Format a row as its rank and user."""
    return f"{index + 1} {score["userId"]}\n"


def test_the_callers_row_follows_them_onto_every_other_page():
    """The caller's row closes every page but their own."""
    scores = [{"userId": f"u{i}"} for i in range(25)]

    pages, jump_page = paginate_leaderboard(scores, format_row, "u13")

    assert jump_page == 1
    assert len(pages) == 3
    assert pages[0].description.endswith("\n14 u13\n")
    assert pages[1].description.count("u13") == 1
    assert pages[2].description.endswith("\n14 u13\n")


def test_a_caller_who_did_not_place_has_no_page():
    """A caller missing from the leaderboard gets no jump page and no extra rows."""
    scores = [{"userId": f"u{i}"} for i in range(25)]

    pages, jump_page = paginate_leaderboard(scores, format_row, "nobody")

    assert jump_page is None
    assert [page.description.count("\n") for page in pages] == [10, 10, 5]
