from typing import Optional, Any


def discord_timestamp(timestamp: float, style: Optional[str] = "R"):
    return f"<t:{int(timestamp)}:{style}>"
