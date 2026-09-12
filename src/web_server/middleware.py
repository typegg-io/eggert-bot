"""The aiohttp middlewares wrapping every request."""

import aiohttp_jinja2
from aiohttp import web

from utils.errors import ProfileNotFound
from utils.logging import log_error, log_server
from utils.strings import compact_pretty_print

ERROR_PAGES = {
    403: ("Forbidden", "You don't have access to this."),
    404: ("Page Not Found", "This page doesn't exist."),
    405: ("Method Not Allowed", "This page doesn't accept that request."),
}


def error_page(request: web.Request, status: int, error: str, message: str = "") -> web.Response:
    """Render the error template for one status."""
    return aiohttp_jinja2.render_template(
        template_name="error.html",
        request=request,
        context={
            "status": status,
            "error": error,
            "message": message,
        },
        status=status,
    )


@web.middleware
async def request_logging_middleware(request, handler) -> web.StreamResponse:
    """Log all incoming requests."""
    if request.path.startswith(("/static/", "/assets/")) or request.path == "/member-count":
        return await handler(request)

    ip = (
        request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
        or request.headers.get("X-Real-IP")
        or request.remote
        or "unknown"
    )

    log_message = f"`{request.method} {request.path}` | `IP: {ip}`"

    if request.method in ("POST", "PATCH", "PUT"):
        try:
            body = await request.json()
            text = body.get("text")
            if text and len(text) > 1000:
                body["text"] = text[:1000] + "..."
            log_message += f" | `Body:`\n```{compact_pretty_print(body)}```"
        except Exception:
            pass

    log_server(log_message)

    return await handler(request)


@web.middleware
async def security_headers_middleware(request, handler) -> web.StreamResponse:
    """Attach the content security, framing and caching headers to a response."""
    resp = await handler(request)

    # aiohttp sends no Cache-Control, so a browser caches an edited asset heuristically.
    if request.path.startswith(("/static/", "/assets/")):
        resp.headers["Cache-Control"] = "no-cache"

    csp = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data:; "
        "object-src 'none';"
    )
    resp.headers['Content-Security-Policy'] = csp
    resp.headers['X-Content-Type-Options'] = "nosniff"
    resp.headers['X-Frame-Options'] = "DENY"
    resp.headers['Referrer-Policy'] = "no-referrer-when-downgrade"

    return resp


@web.middleware
async def error_middleware(request, handler) -> web.StreamResponse:
    """Render an error page for anything a handler raises."""
    try:
        return await handler(request)

    except ProfileNotFound as e:
        return error_page(request, 404, "User Not Found", str(e))

    except web.HTTPError as e:
        # A client error is the router refusing a bad request, so only a server error is worth reporting.
        if e.status >= 500:
            log_error("WebServer Error", e)

        error, message = ERROR_PAGES.get(e.status, (e.reason, ""))

        return error_page(request, e.status, error, message)

    except Exception as e:
        log_error("WebServer Error", e)

        return error_page(request, 500, "Internal Server Error")
