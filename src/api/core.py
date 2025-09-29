from config import SECRET

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
