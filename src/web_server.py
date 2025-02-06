import discord
import jwt
from aiohttp import web
from discord import Embed

from config import secret, home_guild_id
from database import users

app = web.Application()

async def start_web_server(bot):
    app["bot"] = bot
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=8888)
    await site.start()
    print("Server started.")


async def verify_user(request: web.Request):
    try:
        data = await request.json()
        token = data.get("token")

        try:
            decoded_token = jwt.decode(token, secret, algorithms=["HS256"])
            discord_id = decoded_token.get("discordId")
            user_id = decoded_token.get("userId")

            if not discord_id or not user_id:
                return web.json_response({"error": "Invalid token."}, status=400)

            guild = app["bot"].get_guild(home_guild_id)
            member = guild.get_member(int(discord_id))
            role = discord.utils.get(guild.roles, name="Verified")

            await member.add_roles(role)
            users.link_user(discord_id, user_id)

            user = await app["bot"].fetch_user(discord_id)
            await user.send(embed=Embed(
                title="Verification Successful",
                description="Successfully verified your account.",
                color=1673044,
            ))

            return web.json_response({"success": True, "message": "User verified successfully."})

        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
            return web.json_response({"error": "Token expired or invalid."}, status=401)
    except Exception as e:
        print("Server Error:", e)
        return web.json_response({"error": "Internal server error."}, status=500)

app.router.add_post("/verify", verify_user)
