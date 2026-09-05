"""The command metadata type, kept in a leaf module so importing it costs nothing."""

from dataclasses import dataclass, field

from config import BOT_PREFIX


@dataclass
class CommandInfo:
    """The help metadata every command module declares at the top of its file."""
    name: str
    aliases: list[str]
    description: str
    parameters: str = ""
    examples: list[str] = field(default_factory=list)
    author: int | None = None
    privacy: bool = False
    plus: bool = False

    @property
    def all_names(self) -> list[str]:
        """Return the command's name followed by its aliases."""
        return [self.name, *self.aliases]

    @property
    def usage(self) -> str:
        """Return the usage line, prefixed and carrying any parameters."""
        return f"{BOT_PREFIX}{self.name} {self.parameters}".rstrip()
