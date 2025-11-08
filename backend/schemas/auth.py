from pydantic import BaseModel, ConfigDict
from datetime import datetime




class SUserAuth(BaseModel):
    max_user_id: str
    username: str


class SUser(BaseModel):
    id: int
    max_user_id: str
    username: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SUserSession(BaseModel):
    session_token: str
    user: SUser