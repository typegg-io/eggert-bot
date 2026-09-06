"""The single-use tokens already redeemed by the verify and dashboard routes."""

from datetime import datetime

from utils.dates import now


class UsedTokens:
    """Spent tokens, each remembered only until its own signature expires."""

    def __init__(self) -> None:
        """Start with nothing spent."""
        self.expiries: dict[str, datetime] = {}

    def __contains__(self, token: str) -> bool:
        """Return whether a token has already been redeemed."""
        self.prune()

        return token in self.expiries

    def __setitem__(self, token: str, expires: datetime) -> None:
        """Mark a token redeemed until the moment it expires."""
        self.expiries[token] = expires

    def __len__(self) -> int:
        """Return how many spent tokens are still worth remembering."""
        self.prune()

        return len(self.expiries)

    def prune(self) -> None:
        """Forget every token a signature check would now reject on its own."""
        current = now()
        self.expiries = {
            token: expires for token, expires in self.expiries.items()
            if expires > current
        }
