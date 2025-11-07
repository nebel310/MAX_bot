"""Stub service for user role persistence via JSON.

This acts as a temporary replacement for a future external backend.
All data is kept in-memory and can be exported/imported as JSON.
Later you can replace implementations of the public functions with real
HTTP requests to your backend.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from enum import Enum
from typing import Dict, Any
import json
import time

class UserRole(str, Enum):
    NEED_HELP = "need_help"
    WANT_HELP = "want_help"

@dataclass
class UserRoleRecord:
    user_id: int
    role: UserRole
    updated_at: float

# In-memory store: user_id -> record
_store: Dict[int, UserRoleRecord] = {}
_start_message_ids: Dict[int, int] = {}

# ---------- Public API (replace these later) ---------- #

def set_role(user_id: int, role: UserRole) -> UserRoleRecord:
    rec = UserRoleRecord(user_id=user_id, role=role, updated_at=time.time())
    _store[user_id] = rec
    return rec

def get_role(user_id: int) -> UserRole | None:
    rec = _store.get(user_id)
    return rec.role if rec else None

def set_start_message_id(user_id: int, message_id: int) -> None:
    _start_message_ids[user_id] = message_id

def get_start_message_id(user_id: int) -> int | None:
    return _start_message_ids.get(user_id)

def to_json() -> str:
    payload = [asdict(r) for r in _store.values()]
    return json.dumps(payload, ensure_ascii=False, indent=2)

def load_json(data: str) -> None:
    loaded = json.loads(data)
    for item in loaded:
        role = UserRole(item["role"])  # validate
        rec = UserRoleRecord(user_id=int(item["user_id"]), role=role, updated_at=float(item["updated_at"]))
        _store[rec.user_id] = rec

# Convenience sample for manual testing
if __name__ == "__main__":
    set_role(123, UserRole.NEED_HELP)
    set_role(777, UserRole.WANT_HELP)
    print(to_json())
