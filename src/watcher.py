import asyncio
import importlib
import sys
import threading
import types
from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from config import SOURCE_DIR


def _get_command_class():
    return sys.modules["commands.base"].Command


class ReloadHandler(FileSystemEventHandler):
    def __init__(self, bot, loop):
        self.bot = bot
        self.loop = loop
        self.debounce_timers = {}

    def on_modified(self, event):
        path = Path(event.src_path)

        if event.is_directory:
            return

        if path.suffix != ".py":
            return

        if any(part in "__pycache__" for part in path.parts):
            return

        if event.src_path in self.debounce_timers:
            self.debounce_timers[event.src_path].cancel()

        timer = threading.Timer(0.5, lambda: self._handle_change(path))
        self.debounce_timers[event.src_path] = timer
        timer.start()

    def _handle_change(self, path: Path):
        try:
            parts = path.relative_to(SOURCE_DIR).parts
        except ValueError:
            return

        if parts[0] == "commands" and len(parts) >= 3:
            group, file = parts[1], parts[2].removesuffix(".py")
            print(f"[Watcher] Detected change: commands/{group}/{file}")
            self.loop.call_soon_threadsafe(
                asyncio.create_task, reload_cog(self.bot, group, file)
            )
        else:
            module_path = ".".join(p.removesuffix(".py") for p in parts)
            print(f"[Watcher] Detected change: {module_path}")
            self.loop.call_soon_threadsafe(
                asyncio.create_task, reload_module_and_cogs(self.bot, module_path)
            )


async def reload_cog(bot, group, name):
    """Reload a specific command cog."""
    module_path = f"commands.{group}.{name}"
    try:
        if module_path in sys.modules:
            importlib.reload(sys.modules[module_path])
        else:
            importlib.import_module(module_path)

        module = sys.modules[module_path]
        Command = _get_command_class()
        for obj in module.__dict__.values():
            if isinstance(obj, type) and issubclass(obj, Command) and obj is not Command:
                await bot.remove_cog(obj.__name__)
                await bot.add_cog(obj(bot))
                print(f"[Watcher] ✓ Reloaded cog: {group}/{name}")
                return

        print(f"[Watcher] ✗ No cog found in {group}/{name}")
    except Exception as e:
        print(f"[Watcher] ✗ Failed to reload {group}/{name}: {e}")


def module_depends_on(module, dependency_path):
    """Check if a module directly imports from a given module path."""
    for value in module.__dict__.values():
        if isinstance(value, types.ModuleType):
            if value.__name__ == dependency_path or value.__name__.startswith(dependency_path + "."):
                return True
        elif hasattr(value, "__module__"):
            mod = value.__module__ or ""
            if mod == dependency_path or mod.startswith(dependency_path + "."):
                return True
    return False


def find_all_dependents(module_path, visited=None):
    """Recursively find all loaded project modules that depend on module_path."""
    if visited is None:
        visited = set()
    if module_path in visited:
        return set()

    visited.add(module_path)
    dependents = set()

    project_prefixes = ("commands.", "graphs.", "utils.", "database.", "api.", "web_server.")
    for mod_name, mod in sys.modules.items():
        if mod is None or not any(mod_name.startswith(p) for p in project_prefixes):
            continue
        if module_depends_on(mod, module_path):
            dependents.add(mod_name)
            dependents.update(find_all_dependents(mod_name, visited))

    return dependents


async def reload_module_and_cogs(bot, module_path):
    """Reload a non-command module and any cogs that transitively depend on it."""
    if module_path not in sys.modules:
        print(f"[Watcher] Module {module_path} not imported, skipping")
        return

    try:
        importlib.reload(sys.modules[module_path])
        print(f"[Watcher] ✓ Reloaded module: {module_path}")
    except Exception as e:
        print(f"[Watcher] ✗ Failed to reload {module_path}: {e}")
        return

    all_dependents = find_all_dependents(module_path)
    affected = {module_path} | all_dependents

    # Reload non-command dependent modules first
    for dep in all_dependents:
        if dep.startswith("commands.") or dep not in sys.modules:
            continue
        try:
            importlib.reload(sys.modules[dep])
        except Exception as e:
            print(f"[Watcher] ✗ Failed to reload {dep}: {e}")

    # Reload cogs that depend on any affected module
    cogs_to_reload = []
    for cog_name, cog in [(n, bot.get_cog(n)) for n in list(bot.cogs)]:
        if not cog or not hasattr(cog, "__module__"):
            continue
        cog_module = sys.modules.get(cog.__module__)
        if cog_module and any(module_depends_on(cog_module, m) for m in affected):
            cogs_to_reload.append((cog_name, cog.__module__))

    if not cogs_to_reload:
        print(f"[Watcher] No cogs depend on {module_path}")
        return

    reloaded = 0
    for cog_name, cog_module_path in cogs_to_reload:
        if cog_module_path not in sys.modules:
            continue
        try:
            importlib.reload(sys.modules[cog_module_path])
            module = sys.modules[cog_module_path]
            Command = _get_command_class()
            for obj in module.__dict__.values():
                if (
                    isinstance(obj, type)
                    and issubclass(obj, Command)
                    and obj is not Command
                    and obj.__name__ == cog_name
                ):
                    await bot.remove_cog(cog_name)
                    await bot.add_cog(obj(bot))
                    reloaded += 1
                    break
        except Exception as e:
            print(f"[Watcher] ✗ Failed to reload cog {cog_name}: {e}")

    print(f"[Watcher] ✓ Reloaded {reloaded}/{len(cogs_to_reload)} dependent cog(s)")


def start_watcher(bot, loop):
    observer = Observer()
    observer.schedule(ReloadHandler(bot, loop), path=SOURCE_DIR, recursive=True)
    thread = threading.Thread(target=observer.start, daemon=True)
    thread.start()
    print(f"[Watcher] Watching {SOURCE_DIR} for changes...")
