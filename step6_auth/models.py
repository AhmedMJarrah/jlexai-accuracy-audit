"""
User identity - maps a login username to the internal user_slot_N
used throughout sampling/assignment. Admin accounts have no slot -
they're not assigned sample records themselves.
"""
from typing import Optional

from pydantic import BaseModel


class User(BaseModel):
    username: str
    display_name: str = ""
    is_admin: bool = False
    user_slot: Optional[str] = None  # None for admin; "user_slot_1".."user_slot_5" for volunteers
