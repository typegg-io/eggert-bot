"""The watcher reloads on an edit, and on nothing else.

Windows reports attribute and access changes as modifications, so an event alone proves nothing.
"""

import time
from types import SimpleNamespace

from watchdog.events import FileModifiedEvent, FileMovedEvent

from watcher import ReloadHandler, watched_files


def build_handler() -> tuple[ReloadHandler, list]:
    """Return a handler wired to a list that collects everything it queues."""
    queued = []
    loop = SimpleNamespace(call_soon_threadsafe=lambda fn, path: fn(path))
    queue = SimpleNamespace(put_nowait=queued.append)

    return ReloadHandler(bot=None, loop=loop, queue=queue), queued


def test_an_event_on_unchanged_contents_queues_nothing() -> None:
    """A metadata-only event must not reload the module it names."""
    handler, queued = build_handler()
    path = watched_files()[0]

    handler.on_modified(FileModifiedEvent(str(path)))
    time.sleep(0.7)

    assert queued == []


def test_an_event_on_changed_contents_queues_one_reload() -> None:
    """An edit must reload exactly once."""
    handler, queued = build_handler()
    path = watched_files()[0]
    handler.file_hashes[str(path)] = "stale"

    handler.on_modified(FileModifiedEvent(str(path)))
    time.sleep(0.7)

    assert queued == [path]


def test_an_atomic_save_queues_one_reload() -> None:
    """An editor that renames a temp file over the module must still reload it."""
    handler, queued = build_handler()
    path = watched_files()[0]
    handler.file_hashes[str(path)] = "stale"

    handler.on_moved(FileMovedEvent(f"{path}.tmp.1612.7a50f7429bdf", str(path)))
    time.sleep(0.7)

    assert queued == [path]


def test_a_pycache_file_is_ignored() -> None:
    """A compiled module lands beside its source and must not reload anything."""
    handler, queued = build_handler()
    path = watched_files()[0].parent / "__pycache__" / "module.py"

    handler.on_modified(FileModifiedEvent(str(path)))
    time.sleep(0.7)

    assert queued == []
