"""Every route the backend calls refuses a request without the shared bearer token."""

import asyncio
from functools import partial

import pytest
from aiohttp.test_utils import make_mocked_request

from web_server import utils as web_utils
from web_server.routes import chat, link, quotes, sources, update_gg_plus, update_nwpm_role, users

# An aiohttp response is an empty mapping, so `if response:` is false. These pin the `is not None` checks.
HANDLERS = {
    "import_user": users.import_user,
    "delete_user": users.delete_user,
    "create_quote": quotes.create_quote,
    "patch_quote": quotes.patch_quote,
    "remove_quote": quotes.remove_quote,
    "create_source": sources.create_source,
    "patch_source": sources.patch_source,
    "remove_source": sources.remove_source,
    "receive_message": chat.receive_message,
    "update_gg_plus": partial(update_gg_plus.update_gg_plus, None),
    "update_nwpm_role": partial(update_nwpm_role.update_nwpm_role, None),
    "link_account": partial(link.link_account, None),
    "link_status": partial(link.link_status, None),
}


@pytest.fixture(autouse=True)
def signing_key(monkeypatch):
    """Give the server a known key, so a wrong one is wrong."""
    monkeypatch.setattr(web_utils, "SECRET", "test-secret")


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer wrong"}], ids=["missing", "wrong"])
@pytest.mark.parametrize("name", HANDLERS)
def test_a_route_refuses_a_bad_token(name, headers):
    request = make_mocked_request("POST", "/", headers=headers, match_info={"userId": "u", "quoteId": "q"})
    response = asyncio.run(HANDLERS[name](request))
    assert response.status == 401
