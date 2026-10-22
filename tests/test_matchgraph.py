"""A Quickplay ghost is graphed from the replay it plays back, not listed as a DNF."""

import asyncio

from commands.graphs import matchgraph


def test_a_ghost_takes_its_keystrokes_from_its_replay(monkeypatch):
    requested = []

    async def fake_race(race_id: str, get_keystrokes: bool = False) -> dict:
        """Serve the ghost's replay with its keystrokes."""
        requested.append((race_id, get_keystrokes))
        return {"raceId": race_id, "keystrokeData": ["ghost keystrokes"]}

    monkeypatch.setattr(matchgraph, "get_race_by_id", fake_race)

    user = {"userId": "u1", "username": "yuri", "keystrokeData": ["own keystrokes"]}
    ghost = {"username": "bigtoe2727", "ghostReplayId": "r1", "ghostUserId": "u2"}
    bot = {"username": "Max", "botId": "b1", "keystrokeData": ["bot keystrokes"]}

    asyncio.run(matchgraph.attach_ghost_keystrokes([user, ghost, bot]))

    assert requested == [("r1", True)]
    assert ghost["keystrokeData"] == ["ghost keystrokes"]
    assert user["keystrokeData"] == ["own keystrokes"]


def test_a_ghost_and_a_bot_are_marked_apart():
    assert matchgraph.player_icon({"botId": "b1"}) == ":robot:"
    assert matchgraph.player_icon({"ghostReplayId": "r1"}) == ":ghost:"
    assert matchgraph.player_icon({"userId": "u1"}) == ""
