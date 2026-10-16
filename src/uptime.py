"""Checks TypeGG once a minute and posts outages to #errors."""

import asyncio
import time

import aiohttp
from discord.ext import commands, tasks

from config import DEVELOPER_ROLE_ID, MAINTENANCE_URL, UPTIME_TARGETS, UPTIME_WEBHOOK
from services.uptime import Alert, UptimeMonitor
from utils.logging import log_error

TIMEOUT = aiohttp.ClientTimeout(total=10)

# The command module reads and mutes this same monitor.
MONITOR = UptimeMonitor(targets=list(UPTIME_TARGETS))


async def check(session: aiohttp.ClientSession, url: str) -> str | None:
    """Return why the URL failed, or None when it answered."""
    try:
        async with session.get(url) as response:
            if response.status >= 400:
                return f"HTTP {response.status}"
            return None
    except TimeoutError:
        return "no answer in 10s"
    except aiohttp.ClientError as error:
        return type(error).__name__


async def read_maintenance(session: aiohttp.ClientSession) -> bool | None:
    """Return the site's maintenance switch, or None when it cannot be read."""
    try:
        async with session.get(MAINTENANCE_URL) as response:
            if response.status != 200:
                return None
            body = await response.json(content_type=None)
            return bool(body.get("maintenance"))
    except (TimeoutError, aiohttp.ClientError, ValueError, AttributeError):
        return None


def webhook_payload(alert: Alert) -> dict:
    """Build the webhook body. Only a ping may mention Developer, and nothing else ever can."""
    if not alert.ping:
        return {"content": alert.text, "allowed_mentions": {"parse": []}}
    return {
        "content": f"<@&{DEVELOPER_ROLE_ID}> {alert.text}",
        "allowed_mentions": {"roles": [str(DEVELOPER_ROLE_ID)]},
    }


async def post(session: aiohttp.ClientSession, alert: Alert) -> None:
    """Send one alert to the webhook."""
    if not UPTIME_WEBHOOK:
        return
    async with session.post(UPTIME_WEBHOOK, json=webhook_payload(alert)) as response:
        if response.status >= 400:
            log_error("Uptime post", RuntimeError(f"webhook answered HTTP {response.status}"))


class UptimeWatcher(commands.Cog):
    """Runs the minute check loop."""

    def __init__(self, bot) -> None:
        """Start the loop."""
        self.bot = bot
        self.check_loop.start()

    def cog_unload(self) -> None:
        """Stop the loop."""
        self.check_loop.cancel()

    @tasks.loop(minutes=1)
    async def check_loop(self) -> None:
        """Check every target and post what changed."""
        async with aiohttp.ClientSession(timeout=TIMEOUT) as session:
            names = list(UPTIME_TARGETS)
            reasons, maintenance = await asyncio.gather(
                asyncio.gather(*(check(session, UPTIME_TARGETS[name]) for name in names)),
                read_maintenance(session),
            )
            alerts = MONITOR.observe(time.time(), maintenance, dict(zip(names, reasons, strict=True)))
            for alert in alerts:
                await post(session, alert)

    @check_loop.error
    async def check_loop_error(self, error) -> None:
        """Log anything the loop raises."""
        log_error("Uptime loop", error)


async def setup(bot) -> None:
    """Register the uptime cog."""
    await bot.add_cog(UptimeWatcher(bot))
