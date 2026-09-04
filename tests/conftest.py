"""Shared fixtures for the test suite."""

import pytest

from commands.base import Command
from utils.files import get_command_modules


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
