import asyncio
import importlib
import sys
import threading

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from commands.base import Command
from config import SOURCE_DIR


class ReloadHandler(FileSystemEventHandler):
    def __init__(self, bot, loop):
        self.bot = bot
        self.loop = loop

    def on_modified(self, event):
        if not event.src_path.endswith(".py"):
            return

        parts = event.src_path.replace("\\", "/").split("/")
        if "commands" in parts:
            group_index = parts.index("commands") + 1
            try:
                group = parts[group_index]
                file = parts[group_index + 1][:-3]
                print(f"[Watcher] Detected change: {group}/{file}")
                self.loop.call_soon_threadsafe(
                    asyncio.create_task, reload_cog(self.bot, group, file)
                )
            except IndexError:
                pass


async def reload_cog(bot, group, name):
    try:
        module_path = f"commands.{group}.{name}"
        if module_path in sys.modules:
            importlib.reload(sys.modules[module_path])
        else:
            importlib.import_module(module_path)

        module = sys.modules[module_path]

        for obj in module.__dict__.values():
            if (
                isinstance(obj, type)
                and issubclass(obj, Command)
                and obj is not Command
            ):
                await bot.remove_cog(obj.__name__)
                await bot.add_cog(obj(bot))
                print(f"[Watcher] Reloaded {group}/{name}")
                return
        print(f"[Watcher] No cog class found in {group}/{name}")
    except Exception as e:
        print(f"[Watcher] Failed to reload {group}/{name}: {e}")


def start_watcher(bot, loop):
    observer = Observer()
    observer.schedule(ReloadHandler(bot, loop), path=SOURCE_DIR / "commands", recursive=True)
    thread = threading.Thread(target=observer.start, daemon=True)
    thread.start()
