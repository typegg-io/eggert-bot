import glob
import importlib
import os

from config import SOURCE_DIR
from utils.logging import log


def get_command_groups():
    """Return a list of command groups."""
    groups = []
    for dir in os.listdir(SOURCE_DIR / "commands"):
        if not dir.startswith("_") and os.path.isdir(SOURCE_DIR / "commands" / dir):
            groups.append(dir)

    return sorted(groups)


def get_command_modules():
    """Yield (group, file, module) for each command module."""
    for group in get_command_groups():
        for file in os.listdir(SOURCE_DIR / "commands" / group):
            if file.endswith(".py") and not file.startswith("_"):
                module = importlib.import_module(f"commands.{group}.{file[:-3]}")
                yield group, file, module


def remove_file(file_name: str):
    """Remove a file if it exists."""
    try:
        os.remove(file_name)
    except FileNotFoundError:
        log(f"File {file_name} not found.")


def clear_image_cache():
    """Removes any lingering PNG files from the source directory."""
    for file in glob.glob("*.png"):
        try:
            os.remove(file)
        except Exception:
            pass
