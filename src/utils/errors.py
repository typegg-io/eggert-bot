from discord import Embed

from config import bot_prefix as prefix

RED = 0xFF0000

def missing_arguments(info):
    return Embed(
        title="Missing Parameter",
        description="One or more parameters is missing\n"
                    f"Usage: `{prefix}{info['name']} {info['parameters']}`",
        color=RED,
    )

def same_username():
    return Embed(
        title="Same Username",
        description="You cannot compare yourself with yourself",
        color=RED,
    )

def unknown_command():
    return Embed(
        title="Command Not Found",
        description=f"`{prefix}help` for a list of commands",
        color=RED,
    )

def invalid_number():
    return Embed(
        title="Invalid Number",
        description="Number provided is invalid",
        color=RED,
    )

def unexpected_error():
    return Embed(
        title="Unexpected Error",
        description="An unexpected error occurred.",
        color=RED,
    )

def invalid_metric(metric):
    return Embed(
        title="Invalid Metric",
        description=f"'{metric}' is not a valid metric. Please use 'pp' or 'wpm'.",
        color=RED,
    )

def invalid_user(user_arg):
    return Embed(
        title="Invalid User",
        description=f"Could not find user: {user_arg}",
        color=RED,
    )

def api_error(message):
    return Embed(
        title="API Error",
        description=f"Error from API: {message}",
        color=RED,
    )
