"""
Admin read/write for the volunteer identity mapping - lets the admin
portal edit which real username/display_name occupies each of the
fixed user_slot_1..N slots, without hand-editing config/users.json.
The number of slots is fixed by settings.num_users (it matches how
sampling was stratified) - this does not add new slots, only edits
who occupies an existing one.
"""
import json
from pathlib import Path


def load_raw_users(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8")).get("users", [])


def save_users(path: Path, users: list[dict]) -> None:
    path.write_text(json.dumps({"users": users}, ensure_ascii=False, indent=2), encoding="utf-8")


def update_volunteer(path: Path, user_slot: str, username: str, display_name: str) -> None:
    users = load_raw_users(path)
    found = False
    for u in users:
        if u.get("user_slot") == user_slot:
            u["username"] = username
            u["display_name"] = display_name
            found = True
            break
    if not found:
        raise ValueError(f"No existing entry for {user_slot} - slots are fixed, cannot add new ones here")
    save_users(path, users)
