"""
Loads the username -> user_slot mapping from the users config file.
Not secret - just identity mapping, safe to commit. The password
itself is handled separately (shared, hashed, kept in .env - see
hashing.py) and never lives in this file.
"""
import json
from pathlib import Path

from step6_auth.models import User


def load_users(path: Path) -> list[User]:
    if not path.exists():
        raise FileNotFoundError(
            f"User config not found at {path} - create it with the real "
            f"volunteer usernames before running auth."
        )
    raw = json.loads(path.read_text(encoding="utf-8"))
    users = [User(**u) for u in raw.get("users", [])]

    slots = [u.user_slot for u in users if u.user_slot]
    if len(slots) != len(set(slots)):
        raise ValueError(
            "Duplicate user_slot in users config - each slot must map to exactly one username"
        )

    return users


def find_user(username: str, path: Path) -> User | None:
    for u in load_users(path):
        if u.username == username:
            return u
    return None
