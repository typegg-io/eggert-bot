from pprint import pformat

import aiohttp_jinja2
from aiohttp import web

from utils.errors import ProfileNotFound
from utils.logging import log_error, log_server


@web.middleware
async def request_logging_middleware(request, handler):
    """Log all incoming requests."""
    ip = request.remote or "unknown"
    log_message = f"`{request.method} {request.path}` | `IP: {ip}`"

    if request.method in ("POST", "PATCH", "PUT"):
        try:
            body = await request.json()
            text = body.get("text")
            if text and len(text) > 1000:
                body["text"] = text[:1000] + "..."
            log_message += f" | `Body:`\n```{pformat(body, width=120)}```"
        except Exception:
            pass

    log_server(log_message)

    return await handler(request)


@web.middleware
async def security_headers_middleware(request, handler):
    resp = await handler(request)

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
async def error_middleware(request, handler):
    try:
        return await handler(request)

    except web.HTTPNotFound:
        return aiohttp_jinja2.render_template(
            template_name="error.html",
            request=request,
            context={
                "status": 404,
                "error": "Page Not Found",
                "message": "This page doesn't exist.",
            },
            status=404,
        )

    except ProfileNotFound as e:
        return aiohttp_jinja2.render_template(
            "error.html",
            request=request,
            context={
                "status": 404,
                "error": f"User Not Found",
                "message": str(e),
            },
            status=404,
        )

    except Exception as e:
        log_error("WebServer Error", e)

        return aiohttp_jinja2.render_template(
            template_name="error.html",
            request=request,
            context={
                "status": 500,
                "error": "Internal Server Error",
            },
            status=500,
        )
