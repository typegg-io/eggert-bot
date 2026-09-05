"""Shared fixtures for the test suite."""

import sqlite3

import pytest

from commands.base import Command
from database.bot import db
from utils.files import get_command_modules


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
