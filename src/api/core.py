import os

from aiohttp import ClientResponse

from config import SECRET
from utils.errors import APIError

API_URL = os.getenv("API_URL")
API_RATE_LIMIT = 0.5  # seconds between requests

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


async def get_response(
    response: ClientResponse,
    exceptions: dict = None
):
    """
    Process an aiohttp response, returning its JSON body or raising an error.

    Args:
        response (ClientResponse): The aiohttp response object to process.
        exceptions (dict[int, Exception], optional): A mapping of HTTP status
            codes to custom exceptions to raise if matched.
    """
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
