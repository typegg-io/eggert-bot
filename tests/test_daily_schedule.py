"""Tests that each daily job fires once a day, even when the minute loop runs late."""

from datetime import UTC, datetime

from tasks import BackgroundTasks


class FakeCog:
    """Carry just the last-run state that is_due reads."""

    is_due = BackgroundTasks.is_due

    def __init__(self, last_run=None) -> None:
        """Start with the given last-run dates, or none at all."""
        self._last_run = last_run or {}


def at(hour, minute, day=15):
    """Return a UTC datetime on the given day in October 2026."""
    return datetime(2026, 10, day, hour, minute, tzinfo=UTC)


def test_job_is_due_at_its_scheduled_minute():
    """A job that has not run today is due the minute its time arrives."""
    cog = FakeCog()
    assert cog.is_due("daily", at(0, 5))


def test_job_stays_due_when_the_loop_runs_late():
    """A missed minute does not lose the job for the day."""
    cog = FakeCog()
    assert cog.is_due("daily", at(0, 9))
    assert cog.is_due("daily", at(14, 30))


def test_job_is_not_due_before_its_time():
    """A job does not fire early."""
    cog = FakeCog()
    assert not cog.is_due("daily", at(0, 4))
    assert not cog.is_due("reminder", at(19, 59))


def test_job_runs_once_a_day():
    """A job already marked for today does not fire again."""
    cog = FakeCog({"daily": at(0, 5).date()})
    assert not cog.is_due("daily", at(0, 5))
    assert not cog.is_due("daily", at(23, 59))


def test_job_comes_due_again_the_next_day():
    """Yesterday's run does not satisfy today."""
    cog = FakeCog({"daily": at(0, 5, day=14).date()})
    assert cog.is_due("daily", at(0, 5, day=15))


def test_evening_job_is_not_due_after_midnight():
    """Rolling into a new day does not make the 20:00 job due at once."""
    cog = FakeCog({"reminder": at(20, 0, day=14).date()})
    assert not cog.is_due("reminder", at(0, 5, day=15))
    assert cog.is_due("reminder", at(20, 0, day=15))
