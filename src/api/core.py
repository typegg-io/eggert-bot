import asyncio
import os
import time
from collections import deque

from aiohttp import ClientResponse

from config import SECRET
from utils.errors import APIError
from utils.logging import log

API_URL = os.getenv("API_URL")
AUTH_HEADERS = {
    "Authorization": SECRET,
}


class RateLimiter:
    """
    Asynchronous sliding-window rate limiter.

    Ensures that no more than `max_rate` requests occur in any rolling `time_window` seconds.

    Args:
        max_rate (int): Maximum number of calls allowed within the time window.
        time_window (float): Time window in seconds.
    """

    def __init__(self, max_rate: int, time_window: float):
        self.max_rate = max_rate
        self.time_window = time_window
        self._timestamps = deque()
        self._lock = asyncio.Lock()

    async def wait(self):
        async with self._lock:
            now = time.monotonic()

            while self._timestamps and self._timestamps[0] <= now - self.time_window:
                self._timestamps.popleft()

            if len(self._timestamps) >= self.max_rate:
                sleep_time = self._timestamps[0] + self.time_window - now
                if sleep_time > 0:
                    log(f"⏳ Rate limit reached - sleeping {self.time_window:.2f}s")
                    await asyncio.sleep(self.time_window)

                now = time.monotonic()
                while self._timestamps and self._timestamps[0] <= now - self.time_window:
                    self._timestamps.popleft()

            self._timestamps.append(now)


limiter = RateLimiter(max_rate=15, time_window=5)


def get_params(raw_params):
    """Prepare and return API parameters."""
    params = {}
    for key, value in raw_params.items():
        if value is None:
            continue
        if isinstance(value, bool):
            value = str(value).lower()
        params[key] = value
    return params


async def get_response(
    response: ClientResponse,
    exceptions: dict = None
):
    """
    Process an aiohttp response, returning its JSON body or raising an error.
    Applies global rate limiting.

    Args:
        response (ClientResponse): The aiohttp response object to process.
        exceptions (dict[int, Exception], optional): A mapping of HTTP status
            codes to custom exceptions to raise if matched.
    """
    await limiter.wait()

    status = response.status
    json = await response.json()
    message = json.get("message", "No message provided.")

    if status == 200:
        return json

    if exceptions:
        for error in exceptions.keys():
            if status == error:
                raise exceptions[error]

    raise APIError(status, message)
