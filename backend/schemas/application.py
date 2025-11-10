from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import Optional, List




class SApplicationBase(BaseModel):
    event_id: int = Field(description="ID события")
    status: str = Field(description="Статус заявки")
    rejection_reason: Optional[str] = Field(None, description="Причина отказа")


class SApplicationCreate(BaseModel):
    event_id: int = Field(description="ID события")


class SApplicationUpdate(BaseModel):
    status: str = Field(description="Статус заявки")
    rejection_reason: Optional[str] = Field(None, description="Причина отказа")


class SApplication(SApplicationBase):
    id: int
    user_id: int
    applied_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class SApplicationWithUser(SApplication):
    user_username: str = Field(description="Имя пользователя")
    user_rating: int = Field(description="Рейтинг пользователя")
    user_participation_count: int = Field(description="Количество участий пользователя")
    user_city_id: Optional[int] = Field(None, description="ID города пользователя")
    user_about_me: Optional[str] = Field(None, description="Описание пользователя")
    user_interests: List[str] = Field(default_factory=list, description="Интересы пользователя")
    match_percentage: float = Field(description="Процент совпадения тегов пользователя и события")


class SApplicationWithEvent(SApplication):
    event_title: str = Field(description="Название события")
    event_date: datetime = Field(description="Дата события")
    event_address: str = Field(description="Адрес события")
    event_creator_username: str = Field(description="Имя создателя события")


class SApplicationListResponse(BaseModel):
    applications: List[SApplicationWithEvent]
    total_count: int
    page: int
    page_size: int
    total_pages: int