from typing import Optional, Any


def discord_timestamp(timestamp: float, style: Optional[str] = "R"):
    return f"<t:{int(timestamp)}:{style}>"


def get_key_by_alias(alias_dict, alias):
    for name, aliases in alias_dict.items():
        if alias in [name] + aliases:
            return name

    return None
