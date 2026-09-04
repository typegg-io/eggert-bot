"""Contract tests for the dynamically loaded command modules.

Commands are discovered by walking src/commands/*/, so a file is registered purely by existing.
Nothing checks the shape of what it declares until the bot starts. These tests do.
"""

import pytest

from utils.flags import Flags

REQUIRED_INFO_KEYS = ("name", "aliases", "description")

KNOWN_FLAGS = set(Flags().__dict__)


def test_modules_were_discovered(command_modules):
    """Guard against a discovery change that silently finds nothing."""
    assert len(command_modules) > 50


def test_every_module_declares_info(command_modules):
    """Every command module exposes an info dict."""
    missing = [f"{g}/{f}" for g, f, m in command_modules if not isinstance(getattr(m, "info", None), dict)]
    assert missing == []


@pytest.mark.parametrize("key", REQUIRED_INFO_KEYS)
def test_info_has_required_keys(command_modules, key):
    """Every info dict carries the keys that help and the error handler read."""
    missing = [f"{g}/{f}" for g, f, m in command_modules if key not in m.info]
    assert missing == []


def test_info_name_matches_filename(command_modules):
    """A command's name matches its file, which is what -help <name> relies on."""
    mismatched = [
        f"{g}/{f}: info name is {m.info['name']!r}"
        for g, f, m in command_modules
        if m.info["name"] != f[:-3]
    ]
    assert mismatched == []


def test_aliases_are_a_list_of_strings(command_modules):
    """Aliases are passed straight to discord.py, which requires a sequence of strings."""
    bad = [
        f"{g}/{f}"
        for g, f, m in command_modules
        if not isinstance(m.info["aliases"], list)
        or not all(isinstance(a, str) for a in m.info["aliases"])
    ]
    assert bad == []


def test_names_and_aliases_are_globally_unique(command_modules):
    """A collision means one command silently shadows another at registration."""
    seen = {}
    collisions = []
    for group, file, module in command_modules:
        for token in [module.info["name"], *module.info["aliases"]]:
            if token in seen:
                collisions.append(f"{token!r} in {group}/{file} and {seen[token]}")
            seen[token] = f"{group}/{file}"
    assert collisions == []


def test_each_module_declares_exactly_one_command_class(command_classes):
    """load_commands registers the first Command subclass it finds and stops."""
    wrong = {path: len(found) for path, found in command_classes.items() if len(found) != 1}
    assert wrong == {}


def test_supported_flags_are_sets_of_known_flags(command_classes):
    """An unknown or non-set value silently rejects every flag a user passes."""
    problems = []
    for path, (cls,) in ((p, c) for p, c in command_classes.items() if len(c) == 1):
        flags = cls.supported_flags
        if not isinstance(flags, set):
            problems.append(f"{path}: supported_flags is {type(flags).__name__}, not set")
            continue
        unknown = flags - KNOWN_FLAGS
        if unknown:
            problems.append(f"{path}: unknown flags {sorted(unknown)}")
    assert problems == []


def test_command_groups_are_not_empty(command_modules):
    """An empty directory under commands/ becomes an empty group in -help."""
    from utils.files import get_command_groups

    populated = {group for group, _, _ in command_modules}
    empty = sorted(set(get_command_groups()) - populated)
    assert empty == []
