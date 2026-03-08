import asyncio

from aiohttp import web

from commands.account.download import run as download
from database.typegg.users import delete_user_data
from utils.logging import log_server, log_error
from web_server.utils import validate_authorization, error_response


async def import_user(request: web.Request):
    """Import a user's latest races in the background (POST /users/{userId}/import)."""
    auth_error = validate_authorization(request)
    if auth_error:
        return auth_error

    user_id = request.match_info.get("userId")

    async def run_import():
        try:
            await download(user_id=user_id)
            log_server(f"Imported races for user {user_id}")
        except Exception as e:
            log_error("Background import failed", e)

    asyncio.ensure_future(run_import())

    return web.json_response({
        "success": True,
        "message": f"Import started for user {user_id}.",
    }, status=202)


async def delete_user(request: web.Request):
    """Delete a user, removing all their data (DELETE /users/{userId})."""
    auth_error = validate_authorization(request)
    if auth_error:
        return auth_error

    user_id = request.match_info.get("userId")
    if not user_id:
        return error_response("Missing userId in URL.", 400)

    try:
        delete_user_data(user_id)
        log_server(f"Removed all data for {user_id}")
        return web.json_response({
            "success": True,
            "message": f"User {user_id} removed successfully.",
        })
    except Exception as e:
        return error_response(f"Failed to ban user: {e}", 500)
