import tempfile
import time
import traceback

import requests

from config import STAGING, MESSAGE_WEBHOOK, ERROR_WEBHOOK
from database.bot.users import get_user

# Constants

start = 0

ADMIN_ALIASES = {
    155481579005804544: "K\u200beegan",
    87926662364160000: "E\u200biko",
    808803618005188651: "A\u200bevistar",
}


# Performance Timing

def time_start():
    """Start the performance timer."""
    global start
    start = time.time()


def time_split():
    """Stop the current timer, print elapsed time, and start a new timer."""
    time_stop()
    time_start()


def time_stop():
    """Stop the performance timer and print the elapsed time in milliseconds."""
    end = time.time() - start
    print(f"Took {end * 1000:,.0f}ms")


# Message Formatting

def get_log_message(message):
    """Format a Discord message into a log string with link, user info, and content."""
    message_link = "[DM]"
    if message.guild:
        message_id = message.id
        message_link = f"https://discord.com/channels/{message.guild.id}/{message.channel.id}/{message_id}"

    author = message.author.id
    user = get_user(author)
    admin = ADMIN_ALIASES.get(author, None)
    mention = f"**{admin}**" if admin else f"<@{author}>"
    user_id = user["userId"]
    linked_account = f" ({user_id})" if user_id else ""
    content = message.content

    flag_parts = []
    if hasattr(message, "flags"):
        if message.flags.metric and message.flags.metric != "pp":
            flag_parts.append(f"-{message.flags.metric}")
        if message.flags.raw:
            flag_parts.append("-raw")
        if message.flags.gamemode:
            flag_parts.append(f"-{message.flags.gamemode}")
        if message.flags.status:
            flag_parts.append(f"-{message.flags.status}")
        if message.flags.language:
            flag_parts.append(f"-{message.flags.language}")

    flags_str = " " + " ".join(flag_parts) if flag_parts else ""

    return f"{message_link} {mention}{linked_account}: `{content}{flags_str}`"


# Logging Functions

def send_log(webhook, message, file=None):
    """Send a log message to a Discord webhook, optionally with a file attachment."""
    payload = {
        "content": message,
        "allowed_mentions": {"parse": ["users"]}
    }

    if file:
        return requests.post(webhook, data=payload, files={"file": file})

    return requests.post(webhook, json=payload)


def log(message, file=None):
    """Log a message to the console (staging) or Discord webhook (production)."""
    if STAGING:
        return print(message)

    send_log(MESSAGE_WEBHOOK, message, file)


def log_error(command_message, error):
    """Log an error with traceback to console (staging) or Discord webhook (production)."""
    if STAGING:
        return traceback.print_exception(type(error), error, error.__traceback__)

    log_message = f"<@155481579005804544>\n{command_message}\n"
    error_traceback = traceback.format_exception(type(error), error, error.__traceback__)
    traceback_string = "".join([line for line in error_traceback])

    if len(traceback_string) >= 1800:
        with tempfile.NamedTemporaryFile(mode="w+", suffix=".txt", delete=True) as temp_file:
            temp_file.write(traceback_string)
            temp_file.flush()
            temp_file.seek(0)
            send_log(ERROR_WEBHOOK, log_message, temp_file)

    log_message += f"```ansi\n\u001B[2;31m{traceback_string}\u001B[0m```"
    send_log(ERROR_WEBHOOK, log_message)
