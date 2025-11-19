import asyncio
import os

import aiohttp
from aiohttp import ContentTypeError

from config import SECRET
from utils.errors import APIError
from utils.logging import log

API_URL = os.getenv("API_URL")
AUTH_HEADERS = {
    "Authorization": SECRET,
}


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


async def request(
    url: str,
    params: dict = {},
    exceptions: dict = None,
):
    """
    Send an asynchronous aiohttp request given a URL, parameters, and headers.

    Args:
        url (str): The endpoint to request
        params (dict, optional): A dictionary of parameters for the request
        exceptions (dict[int, Exception], optional): A mapping of HTTP status
            codes to custom exceptions to raise if matched.
    """
    params = get_params(params)

    async def do_request():
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, headers=AUTH_HEADERS) as response:
                status = response.status
                try:
                    json = await response.json()
                    message = json.get("message", "No message provided.")
                except ContentTypeError:
                    raise APIError(response.status, "TypeGG is likely down, try again later.")

                return status, json, message

    status, json, message = await do_request()

    if status == 200:
        return json

    if status == 429:
        log(f"Rate limit exceeded, retrying in 1s...")
        await asyncio.sleep(1)

        status, json, message = await do_request()

        if status == 200:
            return json

    if exceptions and status in exceptions:
        raise exceptions[status]

    raise APIError(status, message)
