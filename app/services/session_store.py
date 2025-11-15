_session_tokens: dict[int, str] = {}

def set_session_token(user_id: int, token: str):
    _session_tokens[user_id] = token

def get_session_token(user_id: int) -> str | None:
    return _session_tokens.get(user_id)

def clear_session_token(user_id: int):
    _session_tokens.pop(user_id, None)