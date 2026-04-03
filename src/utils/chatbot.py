from pathlib import Path

from utils.files import get_command_modules

MODEL = "claude-haiku-4-5-20251001"
MAX_HISTORY = 10  # messages (5 turns)

_system_prompt: str = None
_PROMPT_FILE = Path(__file__).resolve().parents[1] / "data" / "system_prompt.txt"


def build_system_prompt() -> str:
    by_group = {}
    for group, file, module in get_command_modules():
        info = module.info
        if group in ("unlisted", "admin"):
            continue
        if group not in by_group:
            by_group[group] = []
        line = f"-{info['name']}"
        if info.get("aliases"):
            line += f" (aliases: {', '.join('-' + a for a in info['aliases'])})"
        if info.get("parameters"):
            line += f" {info['parameters']}"
        line += f"\n  {info['description'].strip()}"
        if info.get("examples"):
            line += f"\n  e.g. {', '.join(info['examples'])}"
        by_group[group].append(line)

    command_list = ""
    for group, entries in by_group.items():
        command_list += f"### {group.title()}\n"
        command_list += "\n\n".join(entries)
        command_list += "\n\n"

    template = _PROMPT_FILE.read_text(encoding="utf-8")
    return template.format(command_list=command_list)


def get_system_prompt() -> str:
    """Returns a cached system prompt, building it on first call."""
    global _system_prompt
    if _system_prompt is None:
        _system_prompt = build_system_prompt()
    return _system_prompt
