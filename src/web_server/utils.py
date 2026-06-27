import asyncio

import aiohttp
import discord
from aiohttp import web

from api.core import API_URL
from config import SECRET, VERIFIED_ROLE_NAME, LANGUAGE_ROLE_IDS
from utils.logging import log_server


# Request Utilities

def error_response(message: str, status: int = 500):
    """Create a JSON error response."""
    log_server(f"Error response ({status}): {message}")
    return web.json_response({"error": message}, status=status)


def validate_authorization(request: web.Request):
    """Validate the Authorization header with Bearer token, returns error response or None."""
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return error_response("Missing Authorization header.", 401)

    token = auth_header.removeprefix("Bearer ").strip()
    if token != SECRET:
        return error_response("Token is invalid.", 401)

    return None


# Discord Role Management

COUNTRY_LANGUAGE_ROLES = {
    # French
    "fr": "french",
    "mc": "french",

    # German
    "de": "german",
    "at": "german",
    "li": "german",

    # Italian
    "it": "italian",
    "sm": "italian",
    "va": "italian",

    # Spanish
    "es": "spanish", "mx": "spanish", "ar": "spanish", "co": "spanish",
    "pe": "spanish", "ve": "spanish", "cl": "spanish", "ec": "spanish",
    "gt": "spanish", "cu": "spanish", "bo": "spanish", "do": "spanish",
    "hn": "spanish", "py": "spanish", "sv": "spanish", "ni": "spanish",
    "cr": "spanish", "pa": "spanish", "uy": "spanish",

    # Portuguese
    "pt": "portuguese",
    "br": "portuguese",

    # Russian
    "ru": "russian",

    # Turkish
    "tr": "turkish",

    # Indonesian
    "id": "indonesian",

    # Vietnamese
    "vn": "vietnamese",
}


def get_language_key(country):
    """Get the supported language key for an ISO country code, or None."""
    if not country:
        return None
    return COUNTRY_LANGUAGE_ROLES.get(country.lower())


async def assign_language_role(guild: discord.Guild, discord_id: int, country: str):
    """Assign a language role based on the user's country, if it maps to one."""
    key = get_language_key(country)
    if not key:
        log_server(f"No language role for country '{country}'")
        return

    role_id = LANGUAGE_ROLE_IDS.get(key)
    if not role_id:
        raise ValueError(f"No role ID configured for language '{key}'")

    member = guild.get_member(discord_id)
    if not member:
        raise ValueError(f"Member with ID {discord_id} not found in guild")

    role = guild.get_role(role_id)
    if not role:
        raise ValueError(f"Language role '{key}' (ID {role_id}) not found in guild")

    if role in member.roles:
        log_server(f"Member {member.name} already has language role '{role.name}'")
        return

    try:
        await member.add_roles(role, reason="Assigning language role")
        log_server(f"Assigned {role.name} role to {member.name}")
    except (discord.Forbidden, discord.HTTPException) as e:
        raise RuntimeError(f"Failed to assign language role to {member.name}: {e}")


def get_nwpm_role_name(nwpm):
    """Get the role name for a given nWPM value."""
    if nwpm is None:
        return None
    if nwpm >= 250:
        return "250+"
    lower_bound = int((nwpm // 10) * 10)
    upper_bound = lower_bound + 9
    return f"{lower_bound}-{upper_bound}"


async def update_nwpm_role(cog, guild: discord.Guild, discord_id: int, nwpm: float):
    """Update a given user's nWPM role."""
    member = guild.get_member(discord_id)
    if not member:
        raise ValueError(f"Member with ID {discord_id} not found in guild")

    role_name = get_nwpm_role_name(nwpm)
    if not role_name:
        log_server(f"No nWPM role needed for nwpm={nwpm}")
        return

    new_role = discord.utils.get(guild.roles, name=role_name)
    if not new_role:
        raise ValueError(f"nWPM role '{role_name}' not found in guild")

    # Find all nWPM roles the member currently has
    current_roles = [
        role for role in member.roles
        if role.name == "250+" or (
            "-" in role.name and
            role.name.split("-")[0].isdigit() and
            len(role.name.split("-")) == 2 and
            role.name.split("-")[1].isdigit()
        )
    ]

    if len(current_roles) == 1 and current_roles[0] == new_role:
        log_server(f"Member {member.name} already has correct nWPM role '{role_name}'")
        return

    try:
        if current_roles:
            await member.remove_roles(*current_roles, reason="Updating nWPM role")
            await asyncio.sleep(0.5)

        await member.add_roles(new_role, reason="Assigning nWPM role")
        log_server(f"Assigned {role_name} role to {member.name}")
        await asyncio.sleep(1)
    except (discord.Forbidden, discord.HTTPException) as e:
        raise RuntimeError(f"Failed to update nWPM role for {member.name}: {e}")


async def assign_user_roles(cog, guild: discord.Guild, discord_id: int, user_id: str):
    """Fetch user profile and assign all roles (verified, nWPM, GG+)."""
    from database.bot.users import update_gg_plus_status, update_theme
    from utils.colors import GG_PLUS_THEME

    member = guild.get_member(discord_id)
    if not member:
        raise ValueError(f"Member with ID {discord_id} not found in guild")

    # Assign verified role
    verified_role = discord.utils.get(guild.roles, name=VERIFIED_ROLE_NAME)
    if not verified_role:
        raise ValueError(f"'{VERIFIED_ROLE_NAME}' role not found in guild")

    try:
        await member.add_roles(verified_role)
        log_server(f"Assigned '{VERIFIED_ROLE_NAME}' role to {member.name}")
    except (discord.Forbidden, discord.HTTPException) as e:
        raise RuntimeError(f"Failed to assign verification role: {e}")

    # Fetch profile data and assign roles
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{API_URL}/v1/users/{user_id}") as response:
            if response.status != 200:
                raise RuntimeError(f"Failed to fetch profile for user {user_id}: HTTP {response.status}")

            profile_data = await response.json()

            # Get nWPM and assign nWPM role
            nwpm = profile_data.get("stats", {}).get("nWpm")
            if nwpm is not None:
                await update_nwpm_role(cog, guild, discord_id, nwpm)
            else:
                log_server(f"No nWPM data available for user {user_id}")

            # Assign language role based on country (best-effort, never blocking)
            try:
                await assign_language_role(guild, discord_id, profile_data.get("country"))
            except Exception as e:
                log_server(f"Failed to assign language role for user {user_id}: {e}")

            # Get GG+ status
            is_gg_plus = profile_data.get("isGgPlus", False)

            # Update database
            update_gg_plus_status(user_id, is_gg_plus)
            if is_gg_plus:
                update_theme(discord_id, GG_PLUS_THEME)
            log_server(f"Updated GG+ status in database for user {user_id}: {is_gg_plus}")

            # Assign GG+ role if applicable
            if is_gg_plus:
                gg_plus_role = discord.utils.get(guild.roles, name="GG+")
                if not gg_plus_role:
                    raise ValueError("GG+ role not found in guild")

                try:
                    await member.add_roles(gg_plus_role)
                    log_server(f"Assigned GG+ role to {member.name}")
                except (discord.Forbidden, discord.HTTPException) as e:
                    raise RuntimeError(f"Failed to assign GG+ role to {member.name}: {e}")
