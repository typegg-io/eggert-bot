from json import JSONDecodeError

from aiohttp import web

from database.typegg.quotes import add_quote, get_quote, update_quote, delete_quote
from utils.logging import log_server
from web_server.utils import validate_authorization, error_response


async def create_quote(request: web.Request):
    """Create a new quote (POST /quotes)."""
    auth_error = validate_authorization(request)
    if auth_error:
        return auth_error

    try:
        data = await request.json()
    except JSONDecodeError:
        return error_response("Invalid JSON data.", 400)

    required_fields = [
        "quoteId", "sourceId", "text", "explicit", "difficulty", "complexity",
        "submittedByUsername", "ranked", "created", "language", "formatting",
    ]
    for field in required_fields:
        if field not in data:
            return error_response(f"Missing required field: {field}.", 400)

    quote_id = data["quoteId"]

    try:
        add_quote(data)
        log_server(f"Created quote {quote_id}")
        return web.json_response({
            "success": True,
            "message": f"Quote {quote_id} created successfully.",
        }, status=201)
    except Exception as e:
        return error_response(f"Failed to create quote: {e}", 500)


async def patch_quote(request: web.Request):
    """Update a quote (PATCH /quotes/{quoteId})."""
    auth_error = validate_authorization(request)
    if auth_error:
        return auth_error

    quote_id = request.match_info.get("quoteId")
    if not quote_id:
        return error_response("Missing quoteId in URL.", 400)

    try:
        data = await request.json()
    except JSONDecodeError:
        return error_response("Invalid JSON data.", 400)

    if not data:
        return error_response("No fields to update.", 400)

    if not get_quote(quote_id):
        return error_response(f"Quote {quote_id} not found.", 404)

    try:
        await update_quote(quote_id, data)

        log_server(f"Updated quote {quote_id}")
        return web.json_response({
            "success": True,
            "message": f"Quote {quote_id} updated successfully.",
        })
    except Exception as e:
        return error_response(f"Failed to update quote: {e}", 500)


async def remove_quote(request: web.Request):
    """Delete a quote (DELETE /quotes/{quoteId})."""
    auth_error = validate_authorization(request)
    if auth_error:
        return auth_error

    quote_id = request.match_info.get("quoteId")
    if not quote_id:
        return error_response("Missing quoteId in URL.", 400)

    if not get_quote(quote_id):
        return error_response(f"Quote {quote_id} not found.", 404)

    try:
        delete_quote(quote_id)
        log_server(f"Deleted quote {quote_id}")
        return web.json_response({
            "success": True,
            "message": f"Quote {quote_id} deleted successfully.",
        })
    except Exception as e:
        return error_response(f"Failed to delete quote: {e}", 500)
