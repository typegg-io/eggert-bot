"""How the keystroke decoder handles actions it cannot parse."""

import pytest

from utils.keystroke_codec import decode_keystroke_data


@pytest.mark.parametrize("action", ["-", ">x,q", "=,q", "~"])
def test_an_action_with_no_position_is_skipped_like_go(action):
    """Go's strconv.Atoi fails on these, and Go skips the keystroke but keeps its time."""
    decoded = decode_keystroke_data([2, "ab", 0, f"100+a|50{action}|60+b"])

    assert [keystroke.action.key for keystroke in decoded.keystrokes] == ["a", "b"]
    assert [keystroke.time for keystroke in decoded.keystrokes] == [100, 210]
