import os

from config import SOURCE_DIR
from utils.logging import log


def get_command_groups():
    groups = []
    for dir in os.listdir(SOURCE_DIR / "commands"):
        if not dir.startswith("_") and os.path.isdir(SOURCE_DIR / "commands" / dir):
            groups.append(dir)

    return groups


def remove_file(file_name: str):
    """Remove a file if it exists."""
    try:
        os.remove(file_name)
    except FileNotFoundError:
        log("File not found.")
