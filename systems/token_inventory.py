"""Token inventory system for managing player progression tokens."""

import re
from typing import List, Optional

from tokens import normalize_token, sort_tokens
from utils import log_event


class TokenInventory:
    """Simple lock/unlock system using tokens."""

    TOKEN_PATTERN = re.compile(r"[A-Z0-9_]+$")

    def __init__(self):
        self.tokens = set()  # Use set for O(1) lookup

    def add_token(self, token: Optional[str]) -> bool:
        code = normalize_token(token)
        if not code:
            return False
        if not self.TOKEN_PATTERN.match(code):
            log_event(f"Attempted to add invalid token '{token}'")
            return False
        if code not in self.tokens:
            self.tokens.add(code)
            return True
        return False

    def has_token(self, token: Optional[str]) -> bool:
        code = normalize_token(token)
        if not code:
            return False
        return code in self.tokens

    def remove_token(self, token: Optional[str]) -> bool:
        code = normalize_token(token)
        if not code:
            return False
        if code in self.tokens:
            self.tokens.remove(code)
            return True
        return False

    def get_all_tokens(self) -> List[str]:
        return list(sort_tokens(self.tokens))

    def clear(self) -> None:
        self.tokens.clear()

