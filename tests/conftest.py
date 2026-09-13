"""Shared fixtures for the test suite."""

import gc
import glob
import os
import sqlite3

import pytest

from commands.base import Command
from database.bot import db
from utils import nwpm
from utils.files import get_command_modules

# The real parameters are private to src/data, so a checkout without them runs on placeholders.
if nwpm.PARAMS is None:
    nwpm.PARAMS = {
        "ref_pwpm": 100.0, "adj_clip_lo": 0.5, "adj_clip_hi": 1.5, "window": 40, "bridge_a": 0.0, "bridge_b": 100.0,
    }


@pytest.fixture(scope="session", autouse=True)
def clean_rendered_images():
    """Delete the PNGs the slow suite renders, which no send path is there to remove."""
    before = set(glob.glob("*.png"))
    yield

    # Windows will not unlink a PNG a discord.File still holds open.
    gc.collect()

    for file in set(glob.glob("*.png")) - before:
        try:
            os.remove(file)
        except OSError:
            pass


@pytest.fixture
def scratch_db(tmp_path, monkeypatch):
    """Point users.db queries at an empty database carrying the real schema."""
    schema = db.connection.execute("""
        SELECT sql FROM sqlite_master
        WHERE sql IS NOT NULL AND name NOT LIKE 'sqlite_%'
    """).fetchall()

    connection = sqlite3.connect(tmp_path / "users.db")
    connection.row_factory = sqlite3.Row
    for (statement,) in schema:
        connection.execute(statement)
    connection.commit()

    monkeypatch.setattr(db, "connection", connection)
    yield connection
    connection.close()


@pytest.fixture(scope="session")
def command_modules():
    """Return every command module as a list of (group, filename, module)."""
    return list(get_command_modules())


@pytest.fixture(scope="session")
def command_classes(command_modules):
    """Return the Command subclass declared by each command module."""
    classes = {}
    for group, file, module in command_modules:
        found = [
            obj for obj in module.__dict__.values()
            if isinstance(obj, type) and issubclass(obj, Command) and obj is not Command
        ]
        classes[f"{group}/{file}"] = found
    return classes
