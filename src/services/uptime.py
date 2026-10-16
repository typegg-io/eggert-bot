"""Decides what the uptime watcher posts. Knows nothing of HTTP or Discord."""

from dataclasses import dataclass, field

# Consecutive failed checks before a target counts as down. One check is a minute.
DOWN_AFTER = 2


@dataclass
class Alert:
    """One message for the uptime channel."""

    text: str
    ping: bool = False


@dataclass
class TargetState:
    """What the watcher remembers about one checked URL."""

    failures: int = 0
    down_since: float | None = None


def format_duration(seconds: float) -> str:
    """Render a downtime as 45s, 12m or 1h 5m."""
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds}s"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes}m"
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h {minutes}m" if minutes else f"{hours}h"


@dataclass
class UptimeMonitor:
    """Turns each minute's check results into the alerts worth posting."""

    targets: list[str]
    states: dict[str, TargetState] = field(default_factory=dict)
    maintenance: bool = False
    muted_until: float = 0.0
    muted_by: str = ""
    _was_muted: bool = False

    def __post_init__(self) -> None:
        """Start every target as up."""
        self.states = {name: TargetState() for name in self.targets}

    def mute(self, until: float, by: str) -> None:
        """Silence alerts until the given time."""
        self.muted_until = until
        self.muted_by = by

    def unmute(self) -> None:
        """Lift a mute now."""
        self.muted_until = 0.0

    def is_muted(self, now: float) -> bool:
        """Report whether a mute is in force."""
        return now < self.muted_until

    def _reset(self) -> None:
        """Forget failures, so a target must fail afresh to alert."""
        for state in self.states.values():
            state.failures = 0
            state.down_since = None

    def observe(self, now: float, maintenance: bool | None, results: dict[str, str | None]) -> list[Alert]:
        """
        Record one minute of checks and return what to post.

        Args:
            now: The check time, in seconds.
            maintenance: The site's maintenance switch, or None when it could not be read.
            results: Each target's failure reason, or None when it answered.
        """
        alerts = []

        if maintenance and not self.maintenance:
            self.maintenance = True
            self._reset()
            return [Alert("🛠️ TypeGG is in maintenance mode. Uptime alerts are paused until it ends.")]
        if self.maintenance:
            # Unknown is not over: the switch is read from the site that may be down.
            if maintenance is False:
                self.maintenance = False
                alerts.append(Alert("✅ Maintenance mode is off. Watching again."))
            else:
                return []

        muted = self.is_muted(now)
        if muted:
            self._was_muted = True
            return alerts
        if self._was_muted:
            self._was_muted = False
            self._reset()
            alerts.append(Alert("🔊 The uptime mute has ended. Watching again."))
            return alerts

        for name, reason in results.items():
            state = self.states[name]
            if reason is None:
                if state.down_since is not None:
                    downtime = format_duration(now - state.down_since)
                    alerts.append(Alert(f"🟢 **{name}** is back up after {downtime}."))
                state.failures = 0
                state.down_since = None
                continue

            state.failures += 1
            if state.failures == DOWN_AFTER:
                # It went down at the first failed check, a minute before this one.
                state.down_since = now - 60
                alerts.append(Alert(f"🔴 **{name}** is down: {reason}", ping=True))

        return alerts
