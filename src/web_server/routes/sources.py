from json import JSONDecodeError

from aiohttp import web

from database.typegg.sources import add_source, get_source, update_source, delete_source
from utils.logging import log_server
from web_server.utils import validate_authorization, error_response


async def create_source(request: web.Request):
    """Create a new source (POST /sources)."""
    auth_error = validate_authorization(request)
    if auth_error:
        return auth_error

    try:
        data = await request.json()
    except JSONDecodeError:
        return error_response("Invalid JSON data.", 400)

    required_fields = ["sourceId", "title", "author", "type", "thumbnailUrl", "publicationYear"]
    for field in required_fields:
        if field not in data:
            return error_response(f"Missing required field: {field}", 400)

    source_id = data["sourceId"]

    if get_source(source_id):
        return error_response(f"Source {source_id} already exists.", 409)

    try:
        add_source(data)
        log_server(f"Created source {source_id}")
        return web.json_response({
            "success": True,
            "message": f"Source {source_id} created successfully.",
        }, status=201)
    except Exception as e:
        return error_response(f"Failed to create source: {e}", 500)


async def patch_source(request: web.Request):
    """Update a source (PATCH /sources/{sourceId})."""
    auth_error = validate_authorization(request)
    if auth_error:
        return auth_error

    source_id = request.match_info.get("sourceId")
    if not source_id:
        return error_response("Missing sourceId in URL.", 400)

    try:
        data = await request.json()
    except JSONDecodeError:
        return error_response("Invalid JSON data.", 400)

    if not data:
        return error_response("No fields to update.", 400)

    if not get_source(source_id):
        return error_response(f"Source {source_id} not found.", 404)

    try:
        update_source(source_id, data)
        log_server(f"Updated source {source_id}")
        return web.json_response({
            "success": True,
            "message": f"Source {source_id} updated successfully.",
        })
    except Exception as e:
        return error_response(f"Failed to update source: {e}", 500)


async def remove_source(request: web.Request):
    """Delete a source (DELETE /sources/{sourceId})."""
    auth_error = validate_authorization(request)
    if auth_error:
        return auth_error

    source_id = request.match_info.get("sourceId")
    if not source_id:
        return error_response("Missing sourceId in URL.", 400)

    if not get_source(source_id):
        return error_response(f"Source {source_id} not found.", 404)

    try:
        delete_source(source_id)
        log_server(f"Deleted source {source_id}")
        return web.json_response({
            "success": True,
            "message": f"Source {source_id} deleted successfully.",
        })
    except Exception as e:
        return error_response(f"Failed to delete source: {e}", 500)
