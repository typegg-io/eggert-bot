"""Tests for the nWPM ratchet, a port of recomputeStats in typegg's leaderboard/model.go."""

from utils.nwpm import CALIBRATION_MIN_QUOTES, NWPM_BRIDGE_A, NWPM_BRIDGE_B, NwpmState


def calibrate(state: NwpmState, ratio: float, prefix: str = "q") -> None:
    """Give the state enough ranked quotes at one ratio to calibrate it."""
    for i in range(CALIBRATION_MIN_QUOTES):
        state.skill.update(f"{prefix}{i}", ratio)


def test_nwpm_never_falls_once_calibrated():
    state = NwpmState()
    calibrate(state, 1.5)
    peak = state.recompute()

    calibrate(state, 1.0, prefix="new")
    state.skill.update("one_more", 1.0)

    assert state.skill.value == 1.0
    assert state.recompute() == peak


def test_ratchet_ignores_a_spike_before_calibration():
    state = NwpmState()
    state.skill.update("spike", 3.0)
    assert state.recompute() == 0.0

    calibrate(state, 1.0)

    assert state.recompute() == round(NWPM_BRIDGE_A + NWPM_BRIDGE_B * 1.0, 2)
