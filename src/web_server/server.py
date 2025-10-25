from aiohttp import web
from aiohttp.web_exceptions import HTTPNotFound
from discord.ext import commands

from config import SOURCE_DIR, STAGING
from utils.logging import log
from web_server.routes.stats import stats_page
from web_server.routes.verify import verify_user
from web_server.tasks import teardown_tasks, setup_tasks


@web.middleware
async def error_middleware(request, handler):
    from utils.logging import log_error
    try:
        return await handler(request)
    except Exception as e:
        if type(e) == HTTPNotFound:
            return web.Response(
                text=f"<h1>404 - Page Not Found</h1>",
                content_type="text/html",
                status=404,
            )

        log_error("WebServer Error", e)

        if request.path.startswith("/api/"):
            return web.json_response(
                {"error": str(e), "type": type(e).__name__},
                status=500
            )

        return web.Response(
            text=f"<h1>500 - Internal Server Error</h1><p>{type(e).__name__}: {e}</p>",
            content_type="text/html",
            status=500,
        )


class WebServer(commands.Cog):
    """Cog to manage the aiohttp web server and its background tasks."""

    def __init__(self, bot):
        self.bot = bot
        self.app = web.Application(middlewares=[error_middleware])
        self.runner = None
        self.site = None

        self.nwpm_roles = []
        self.used_tokens = {}

        # Routes
        self.app.router.add_post("/verify", verify_user)
        self.app.router.add_get("/stats/{username}", stats_page)

        # Styles
        self.app.router.add_static("/static", path=str(SOURCE_DIR / "web_server" / "static"), name="static")

        # Background tasks
        if not STAGING:
            setup_tasks(self)

        self.bot.loop.create_task(self.start_web_server())

    async def cog_unload(self):
        teardown_tasks(self)
        await self.stop_web_server()

    async def start_web_server(self):
        """Start the web server."""
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, host="0.0.0.0", port=8888)
        await self.site.start()

        log("Web server started on port 8888")

    async def stop_web_server(self):
        """Stop the web server."""
        if self.runner:
            await self.runner.cleanup()

        log("Web server stopped")


async def setup(bot):
    await bot.add_cog(WebServer(bot))
