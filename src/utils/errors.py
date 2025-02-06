from discord import Embed

from config import bot_prefix as prefix

red = 0xFF0000

def missing_parameter(info):
    return Embed(
        title="Missing Parameter",
        description="One or more parameters is missing\n"
                    f"Usage: `{prefix}{info['name']} {info['parameters']}`",
        color=red,
    )


def unknown_command():
    return Embed(
        title="Command Not Found",
        description=f"`{prefix}help` for a list of commands",
        color=red,
    )

def invalid_number():
    return Embed(
        title="Invalid Number",
        description="Number provided is invalid",
        color=red,
    )

def unexpected_error():
    return Embed(
        title="Unexpected Error",
        description="An unexpected error occurred.",
        color=red,
    )