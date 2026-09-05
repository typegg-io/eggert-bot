"""The public help page route."""

import aiohttp_jinja2
from aiohttp import web

from config import BOT_PREFIX
from utils.files import get_command_groups, get_command_modules

HIDDEN_GROUPS = {"unlisted", "admin"}


@aiohttp_jinja2.template("help.html")
async def help_page(request: web.Request) -> dict:
    """Return the template context listing every visible command."""
    groups = [g for g in get_command_groups() if g not in HIDDEN_GROUPS]

    modules_by_group = {g: [] for g in groups}
    for group, file, module in get_command_modules():
        if group not in modules_by_group:
            continue
        info = module.info
        modules_by_group[group].append({
            "name": info.name,
            "aliases": info.aliases,
            "description": info.description,
            "parameters": info.parameters,
            "examples": info.examples,
            "plus": info.plus,
            "prefix": BOT_PREFIX,
        })

    for group in modules_by_group:
        modules_by_group[group].sort(key=lambda c: c["name"])

    sections = [
        {"group": group, "commands": modules_by_group[group]}
        for group in groups
        if modules_by_group[group]
    ]

    return {"sections": sections}
