import asyncio
import importlib
import sys
import threading
import types

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from commands.base import Command
from config import SOURCE_DIR


class ReloadHandler(FileSystemEventHandler):
    def __init__(self, bot, loop):
        self.bot = bot
        self.loop = loop
        self.debounce_timers = {}

    def on_modified(self, event):
        if not event.src_path.endswith(".py"):
            return

        # Debounce: ignore if same file modified within 0.5s
        if event.src_path in self.debounce_timers:
            self.debounce_timers[event.src_path].cancel()

        timer = threading.Timer(0.5, lambda: self._handle_change(event.src_path))
        self.debounce_timers[event.src_path] = timer
        timer.start()

    def _handle_change(self, file_path):
        parts = file_path.replace("\\", "/").split("/")

        if "commands" in parts:
            # Command file changed - reload specific cog
            group_index = parts.index("commands") + 1
            try:
                group = parts[group_index]
                file = parts[group_index + 1][:-3]
                print(f"[Watcher] Detected change: commands/{group}/{file}")
                self.loop.call_soon_threadsafe(
                    asyncio.create_task, reload_cog(self.bot, group, file)
                )
            except IndexError:
                pass
        elif "src" in parts:
            # Non-command file changed - reload module and all cogs
            src_index = parts.index("src") + 1
            try:
                module_parts = []
                for part in parts[src_index:]:
                    if part.endswith(".py"):
                        module_parts.append(part[:-3])
                    else:
                        module_parts.append(part)

                module_path = ".".join(module_parts)
                print(f"[Watcher] Detected change: {module_path}")
                self.loop.call_soon_threadsafe(
                    asyncio.create_task, reload_module_and_cogs(self.bot, module_path)
                )
            except (IndexError, ValueError):
                pass


async def reload_cog(bot, group, name):
    """Reload a specific command cog."""
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
                print(f"[Watcher] ✓ Reloaded cog: {group}/{name}")
                return
        print(f"[Watcher] ✗ No cog class found in {group}/{name}")
    except Exception as e:
        print(f"[Watcher] ✗ Failed to reload {group}/{name}: {e}")


def module_depends_on(module, dependency_path):
    """Check if a module depends on another module (directly or indirectly)."""
    if not hasattr(module, "__dict__"):
        return False

    # Check direct imports in module's globals
    for value in module.__dict__.values():
        # Check if value is a module object itself
        if isinstance(value, types.ModuleType):
            if value.__name__ == dependency_path or value.__name__.startswith(dependency_path + "."):
                return True
        # Check if value is an object from the dependency module
        elif hasattr(value, "__module__"):
            obj_module = value.__module__
            if obj_module == dependency_path or obj_module.startswith(dependency_path + "."):
                return True

    return False


def find_all_dependents(module_path, visited=None):
    """Find all modules that depend on module_path, recursively."""
    if visited is None:
        visited = set()

    if module_path in visited:
        return set()

    visited.add(module_path)
    dependents = set()

    # Look through all loaded modules
    for mod_name, mod in sys.modules.items():
        if mod is None:
            continue
        # Only check our project modules
        if not any(mod_name.startswith(prefix) for prefix in ["commands.", "graphs.", "utils.", "database.", "api."]):
            continue

        if module_depends_on(mod, module_path):
            dependents.add(mod_name)
            # Recursively find dependents of this module
            dependents.update(find_all_dependents(mod_name, visited))

    return dependents


async def reload_module_and_cogs(bot, module_path):
    """Reload a non-command module and all cogs that might depend on it."""
    try:
        # Reload the changed module
        if module_path not in sys.modules:
            print(f"[Watcher] Module {module_path} not yet imported, skipping")
            return

        importlib.reload(sys.modules[module_path])
        print(f"[Watcher] ✓ Reloaded module: {module_path}")

        # Find all modules that transitively depend on this module
        all_dependents = find_all_dependents(module_path)

        # Reload all dependent modules (excluding command cogs, we'll handle those separately)
        non_command_dependents = [mod for mod in all_dependents if not mod.startswith("commands.")]
        for dep_module_path in non_command_dependents:
            if dep_module_path in sys.modules:
                try:
                    importlib.reload(sys.modules[dep_module_path])
                    print(f"[Watcher] ✓ Reloaded dependent module: {dep_module_path}")
                except Exception as e:
                    print(f"[Watcher] ✗ Failed to reload {dep_module_path}: {e}")

        # Now reload all cogs that depend on the changed module or any of its dependents
        modules_to_check = {module_path} | all_dependents
        cogs_to_reload = []

        for cog_name in bot.cogs.keys():
            cog = bot.get_cog(cog_name)
            if cog and hasattr(cog, "__module__"):
                cog_module_path = cog.__module__
                if cog_module_path in sys.modules:
                    cog_module = sys.modules[cog_module_path]
                    # Check if this cog depends on any of the affected modules
                    for affected_module in modules_to_check:
                        if module_depends_on(cog_module, affected_module):
                            cogs_to_reload.append((cog_name, cog_module_path))
                            break

        if not cogs_to_reload:
            print(f"[Watcher] No cogs depend on {module_path}")
            return

        reloaded_count = 0
        for cog_name, cog_module_path in cogs_to_reload:
            try:
                # Reload the cog's module
                importlib.reload(sys.modules[cog_module_path])

                # Re-instantiate the cog
                module = sys.modules[cog_module_path]
                for obj in module.__dict__.values():
                    if (
                        isinstance(obj, type)
                        and issubclass(obj, Command)
                        and obj is not Command
                        and obj.__name__ == cog_name
                    ):
                        await bot.remove_cog(cog_name)
                        await bot.add_cog(obj(bot))
                        reloaded_count += 1
                        break
            except Exception as e:
                print(f"[Watcher] ✗ Failed to reload cog {cog_name}: {e}")

        print(f"[Watcher] ✓ Reloaded {reloaded_count}/{len(cogs_to_reload)} dependent cog(s)")
    except Exception as e:
        print(f"[Watcher] ✗ Failed to reload {module_path}: {e}")


def start_watcher(bot, loop):
    observer = Observer()
    # Watch entire src directory for project-wide hot reloading
    observer.schedule(ReloadHandler(bot, loop), path=SOURCE_DIR, recursive=True)
    thread = threading.Thread(target=observer.start, daemon=True)
    thread.start()
    print(f"[Watcher] Watching {SOURCE_DIR} for changes...")
