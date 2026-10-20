"""A TypeGG account links to one Discord account, and the newest link wins."""

from database.bot.users import add_user, get_discord_id, get_user, link_user, update_gg_plus_status, update_theme
from utils.colors import DEFAULT_THEME, GG_PLUS_THEME

OLD = "1"
NEW = "2"
USER_ID = "typegg"


def test_a_new_link_supersedes_the_old_one(scratch_db):
    """Linking a second Discord account unlinks the first and reports it."""
    add_user(OLD)
    add_user(NEW)
    link_user(OLD, USER_ID)

    assert link_user(NEW, USER_ID) == [OLD]
    assert get_user(OLD)["userId"] is None
    assert get_discord_id(USER_ID) == NEW


def test_the_superseded_account_loses_its_gg_plus_perks(scratch_db):
    """The old account drops GG+ and its theme, like a manual unlink."""
    add_user(OLD)
    add_user(NEW)
    link_user(OLD, USER_ID)
    update_gg_plus_status(USER_ID, True)
    update_theme(OLD, GG_PLUS_THEME)

    link_user(NEW, USER_ID)

    old = get_user(OLD)
    assert old["isGgPlus"] == 0
    assert old["theme"] == DEFAULT_THEME


def test_relinking_the_same_account_supersedes_nothing(scratch_db):
    """A Discord account that links again keeps its own row untouched."""
    add_user(OLD)
    link_user(OLD, USER_ID)
    update_theme(OLD, GG_PLUS_THEME)

    assert link_user(int(OLD), USER_ID) == []
    assert get_user(OLD)["theme"] == GG_PLUS_THEME
