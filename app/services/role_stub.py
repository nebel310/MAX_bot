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

class UserRole(str, Enum):
    NEED_HELP = "need_help"
    WANT_HELP = "want_help"

@dataclass
class UserRoleRecord:
    user_id: int
    role: UserRole
    updated_at: float

# ====== IN-MEMORY STORE ======

_store: Dict[int, UserRoleRecord] = {}
_start_message_ids: Dict[int, int] = {}

# ====== MOCK DATA (будет заменено на данные с backend) ======

MOCK_FEED_MESSAGE = """Заявки в Москве по вашим интересам 🌿👶:

📌 Совпадение 95% 

[Экология, Дети] Субботник в детском парке

Фонд: "Город детям", 📅 15 апреля

📌 Совпадение 80%

[Экология] Уборка берега реки

Фонд: "Чистый город", 📅 17 апреля

📌 Совпадение 60% 

[Животные] Помощь в приюте для собак

Фонд: "Лапа друга", 📅 20 апреля"""

MOCK_REQUEST_DETAILS = """🍃 Субботник в парке "Зеленый"

Описание: Нужна помощь в уборке территории, посадке деревьев.

Тип: Волонтеры

Дата: 15 апреля, 10:00

Адрес: ул. Парковая, 15

Контакт: @ecomir_contact

Что делать: Приходите по адресу в указанное время."""

# ====== PUBLIC API ======

def set_role(user_id: int, role: str) -> None:
    import time
    _store[user_id] = UserRoleRecord(
        user_id=user_id,
        role=UserRole(role),
        updated_at=time.time()
    )

def get_role(user_id: int) -> str | None:
    rec = _store.get(user_id)
    return rec.role.value if rec else None

def set_start_message_id(user_id: int, message_id: int) -> None:
    _start_message_ids[user_id] = message_id

def get_start_message_id(user_id: int) -> int | None:
    return _start_message_ids.get(user_id)

def to_json() -> str:
    import json
    return json.dumps([asdict(rec) for rec in _store.values()], indent=2)

def load_json(data: str) -> None:
    import json
    records = json.loads(data)
    for rec in records:
        _store[rec["user_id"]] = UserRoleRecord(**rec)
