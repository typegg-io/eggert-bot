"""TypeGG links an account it verified through Discord OAuth, and asks who is linked."""

import asyncio
import json
import types

import pytest
from aiohttp.test_utils import make_mocked_request

from database.bot.users import add_user, get_discord_id, get_user, link_if_free, link_user
from web_server import utils as web_utils
from web_server.routes import link

SECRET = "test-secret"
DISCORD = "111"
OTHER_DISCORD = "222"
USER_ID = "typegg"


@pytest.fixture(autouse=True)
def signing_key(monkeypatch):
    """Accept the test key as the backend's bearer token."""
    monkeypatch.setattr(web_utils, "SECRET", SECRET)


@pytest.fixture
def assigned(monkeypatch):
    """Record role assignments instead of calling Discord."""
    calls = []

    async def assign(guild, discord_id, user_id):
        calls.append((discord_id, user_id))

    async def remove(guild, discord_id):
        calls.append(("removed", discord_id))

    monkeypatch.setattr(link, "assign_user_roles", assign)
    monkeypatch.setattr(link, "remove_user_roles", remove)
    return calls


def cog(members=()):
    """Return a stand-in web server cog whose guild holds only `members`."""
    member_map = {int(m): types.SimpleNamespace(name=f"name{m}") for m in members}
    guild = types.SimpleNamespace(get_member=lambda discord_id: member_map.get(discord_id))

    async def fetch_user(discord_id):
        return types.SimpleNamespace(name=f"fetched{discord_id}")

    bot = types.SimpleNamespace(get_guild=lambda _: guild, get_user=lambda _: None, fetch_user=fetch_user)
    return types.SimpleNamespace(bot=bot)


def post(body: dict, token: str = SECRET):
    """Return a mocked POST /link carrying `body`."""
    request = make_mocked_request("POST", "/link", headers={"Authorization": f"Bearer {token}"})

    async def read_json():
        return body

    request.json = read_json
    return request


def status_request(user_id: str):
    """Return a mocked GET /users/{userId}/link."""
    return make_mocked_request(
        "GET", f"/users/{user_id}/link", headers={"Authorization": f"Bearer {SECRET}"},
        match_info={"userId": user_id},
    )


# link_if_free

def test_fill_links_a_discord_id_the_bot_has_never_seen(scratch_db):
    assert link_if_free(DISCORD, USER_ID) == "linked"
    assert get_discord_id(USER_ID) == DISCORD


def test_fill_reports_an_existing_identical_link(scratch_db):
    link_if_free(DISCORD, USER_ID)
    assert link_if_free(DISCORD, USER_ID) == "already"


def test_fill_never_moves_a_linked_discord_account(scratch_db):
    add_user(DISCORD)
    link_user(DISCORD, "someone-else")
    assert link_if_free(DISCORD, USER_ID) == "conflict"
    assert get_user(DISCORD)["userId"] == "someone-else"


def test_fill_never_moves_a_linked_typegg_account(scratch_db):
    add_user(OTHER_DISCORD)
    link_user(OTHER_DISCORD, USER_ID)
    assert link_if_free(DISCORD, USER_ID) == "conflict"
    assert get_discord_id(USER_ID) == OTHER_DISCORD


# POST /link

def test_link_rejects_a_missing_token(scratch_db, assigned):
    response = asyncio.run(link.link_account(cog(), post({"discordId": DISCORD, "userId": USER_ID}, token="nope")))
    assert response.status == 401


def test_fill_assigns_roles_to_a_member(scratch_db, assigned):
    response = asyncio.run(link.link_account(cog([DISCORD]), post({"discordId": DISCORD, "userId": USER_ID})))
    assert json.loads(response.text) == {"status": "linked", "inGuild": True}
    assert assigned == [(int(DISCORD), USER_ID)]


def test_fill_stores_a_non_member_and_waits_for_them_to_join(scratch_db, assigned):
    response = asyncio.run(link.link_account(cog(), post({"discordId": DISCORD, "userId": USER_ID})))
    assert json.loads(response.text) == {"status": "linked", "inGuild": False}
    assert assigned == []
    assert get_discord_id(USER_ID) == DISCORD


def test_a_conflict_answers_200_so_the_outbox_stops(scratch_db, assigned):
    add_user(DISCORD)
    link_user(DISCORD, "someone-else")
    response = asyncio.run(link.link_account(cog([DISCORD]), post({"discordId": DISCORD, "userId": USER_ID})))
    assert response.status == 200
    assert json.loads(response.text)["status"] == "conflict"
    assert assigned == []


def test_override_moves_the_link_and_strips_the_old_account(scratch_db, assigned):
    add_user(OTHER_DISCORD)
    link_user(OTHER_DISCORD, USER_ID)
    body = {"discordId": DISCORD, "userId": USER_ID, "mode": "override"}
    response = asyncio.run(link.link_account(cog([DISCORD, OTHER_DISCORD]), post(body)))
    assert json.loads(response.text)["status"] == "linked"
    assert get_discord_id(USER_ID) == DISCORD
    assert ("removed", int(OTHER_DISCORD)) in assigned


# GET /users/{userId}/link

def test_status_of_an_unlinked_user(scratch_db):
    response = asyncio.run(link.link_status(cog(), status_request(USER_ID)))
    assert json.loads(response.text)["linked"] is False


def test_status_names_a_member_from_the_guild(scratch_db):
    link_if_free(DISCORD, USER_ID)
    response = asyncio.run(link.link_status(cog([DISCORD]), status_request(USER_ID)))
    assert json.loads(response.text) == {
        "linked": True, "discordId": DISCORD, "username": f"name{DISCORD}", "inGuild": True,
    }


def test_status_names_a_non_member_from_discord(scratch_db):
    link_if_free(DISCORD, USER_ID)
    response = asyncio.run(link.link_status(cog(), status_request(USER_ID)))
    body = json.loads(response.text)
    assert body["inGuild"] is False
    assert body["username"] == f"fetched{DISCORD}"
