"""The uptime watcher's decisions, driven one minute at a time."""

from services.uptime import Alert, UptimeMonitor, format_duration
from uptime import webhook_payload

UP = {"API": None, "Multiplayer": None}


def down(name: str, reason: str = "HTTP 502") -> dict:
    """Results with one target failing."""
    return {**UP, name: reason}


def texts(alerts) -> list[str]:
    """The alert texts alone."""
    return [a.text for a in alerts]


def monitor() -> UptimeMonitor:
    """A fresh monitor over two targets."""
    return UptimeMonitor(targets=["API", "Multiplayer"])


def test_one_failed_check_is_a_blip():
    m = monitor()
    assert m.observe(0, False, down("API")) == []
    assert m.observe(60, False, UP) == []


def test_two_failed_checks_alert_once_and_ping():
    m = monitor()
    m.observe(0, False, down("API"))
    alerts = m.observe(60, False, down("API"))
    assert texts(alerts) == ["🔴 **API** is down: HTTP 502"]
    assert alerts[0].ping
    assert m.observe(120, False, down("API")) == []


def test_recovery_reports_the_downtime_without_a_ping():
    m = monitor()
    m.observe(0, False, down("API"))
    m.observe(60, False, down("API"))
    m.observe(120, False, down("API"))
    alerts = m.observe(180, False, UP)
    assert texts(alerts) == ["🟢 **API** is back up after 3m."]
    assert not alerts[0].ping


def test_maintenance_silences_failures_and_is_announced_once():
    m = monitor()
    started = m.observe(0, True, down("API"))
    assert len(started) == 1 and "maintenance mode" in started[0].text
    for minute in range(1, 10):
        assert m.observe(minute * 60, True, down("API")) == []


def test_an_unreadable_switch_keeps_maintenance_on():
    m = monitor()
    m.observe(0, True, UP)
    assert m.observe(60, None, down("API")) == []
    assert m.observe(120, None, down("API")) == []


def test_after_maintenance_a_target_must_fail_afresh():
    m = monitor()
    m.observe(0, True, down("API"))
    ended = m.observe(60, False, down("API"))
    assert texts(ended) == ["✅ Maintenance mode is off. Watching again."]
    assert texts(m.observe(120, False, down("API"))) == ["🔴 **API** is down: HTTP 502"]


def test_an_unreadable_switch_outside_maintenance_alerts_normally():
    m = monitor()
    m.observe(0, None, down("Multiplayer"))
    assert texts(m.observe(60, None, down("Multiplayer"))) == ["🔴 **Multiplayer** is down: HTTP 502"]


def test_a_mute_silences_alerts_and_lifts_itself():
    m = monitor()
    m.mute(until=600, by="eiko")
    for minute in range(10):
        assert m.observe(minute * 60, False, down("API")) == []
    resumed = m.observe(600, False, down("API"))
    assert texts(resumed) == ["🔊 The uptime mute has ended. Watching again."]
    assert texts(m.observe(660, False, down("API"))) == []
    assert texts(m.observe(720, False, down("API"))) == ["🔴 **API** is down: HTTP 502"]


def test_unmute_resumes_at_once():
    m = monitor()
    m.mute(until=10_000, by="eiko")
    m.observe(0, False, UP)
    m.unmute()
    assert texts(m.observe(60, False, UP)) == ["🔊 The uptime mute has ended. Watching again."]


def test_format_duration():
    assert format_duration(45) == "45s"
    assert format_duration(12 * 60) == "12m"
    assert format_duration(65 * 60) == "1h 5m"
    assert format_duration(120 * 60) == "2h"


def test_a_down_alert_pings_only_developer():
    body = webhook_payload(Alert("down", ping=True))
    assert body["content"].startswith("<@&703605805815169046>")
    assert body["allowed_mentions"] == {"roles": ["703605805815169046"]}


def test_other_alerts_ping_nobody():
    assert webhook_payload(Alert("back up"))["allowed_mentions"] == {"parse": []}
