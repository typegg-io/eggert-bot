"""The shared request helper every other API module calls."""

import asyncio
from typing import Any

import aiohttp
from aiohttp import ContentTypeError

from config import SECRET
from utils.errors import APIError, APIUnavailable
from utils.logging import log

AUTH_HEADERS = {
    "Authorization": SECRET,
}


def get_params(raw_params) -> dict:
    """Prepare and return API parameters."""
    params = {}
    for key, value in (raw_params or {}).items():
        if value is None:
            continue
        if isinstance(value, bool):
            value = str(value).lower()
        params[key] = value
    return params


async def request(
    url: str,
    params: dict = None,
    json_data: dict = None,
    exceptions: dict = None,
    method: str = "GET",
) -> dict[str, Any]:
    """
    Send an asynchronous aiohttp request given a URL, parameters, and headers.

    Args:
        url (str): The endpoint to request
        params (dict, optional): A dictionary of parameters for the request
        json_data (dict, optional): JSON data for the body of the request
        exceptions (dict[int, Exception], optional): A mapping of HTTP status
            codes to custom exceptions to raise if matched.
        method (str): The HTTP method to send the request with
    """
    params = get_params(params)
    json_data = get_params(json_data)
    method = method.lower()

    async def do_request() -> tuple[int, dict[str, Any], str, str | None]:
        """Return the status, body, message and Retry-After header of one attempt."""
        async with aiohttp.ClientSession() as session:
            async with session.request(
                method,
                url,
                json=json_data,
                params=params,
                headers=AUTH_HEADERS
            ) as response:
                status = response.status
                try:
                    json = await response.json()
                    message = json.get("message", "No message provided.")
                except ContentTypeError:
                    raise APIError(response.status, "TypeGG is likely down, try again later.")

                return status, json, message, response.headers.get("Retry-After")

    status, json, message, retry_after = await do_request()

    if status == 200:
        return json

    if status == 429:
        log("Rate limit exceeded, retrying in 3s...")
        await asyncio.sleep(3)

        status, json, message, retry_after = await do_request()

        if status == 200:
            return json

    if exceptions and status in exceptions:
        raise exceptions[status]

    # TypeGG sends whole seconds, though the header also allows an HTTP date.
    if status == 503 and retry_after and retry_after.isdigit():
        raise APIUnavailable(message, int(retry_after))

    raise APIError(status, message)
