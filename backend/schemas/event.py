from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import Optional, List




class SEventBase(BaseModel):
    title: str = Field(
        description="Название события",
        examples=["Помощь бездомным животным", "Уборка парка"],
        json_schema_extra={"example": "Помощь бездомным животным"}
    )
    description: str = Field(
        description="Описание события",
        examples=["Нужна помощь в уходе за животными в приюте"],
        json_schema_extra={"example": "Нужна помощь в уходе за животными в приюте"}
    )
    address: str = Field(
        description="Адрес проведения события",
        examples=["ул. Ленина, д. 10", "Центральный парк"],
        json_schema_extra={"example": "ул. Ленина, д. 10"}
    )
    contact: str = Field(
        description="Контактная информация",
        examples=["+79991234567", "example@mail.ru"],
        json_schema_extra={"example": "+79991234567"}
    )
    what_to_do: str = Field(
        description="Что нужно делать",
        examples=["Кормить животных, убирать вольеры"],
        json_schema_extra={"example": "Кормить животных, убирать вольеры"}
    )
    date: datetime = Field(
        description="Дата и время события",
        examples=["2024-01-15T10:00:00Z"],
        json_schema_extra={"example": "2024-01-15T10:00:00Z"}
    )
    city_id: int = Field(
        description="ID города",
        examples=[1, 2, 3],
        json_schema_extra={"example": 1}
    )


class SEventCreate(SEventBase):
    tag_ids: List[int] = Field(
        description="Список ID тегов события",
        examples=[[1, 2, 3], [4, 5]],
        json_schema_extra={"example": [1, 2, 3]}
    )


class SEventUpdate(BaseModel):
    title: Optional[str] = Field(
        None,
        description="Название события",
        examples=["Помощь бездомным животным", "Уборка парка"],
        json_schema_extra={"example": "Помощь бездомным животным"}
    )
    description: Optional[str] = Field(
        None,
        description="Описание события",
        examples=["Нужна помощь в уходе за животными в приюте"],
        json_schema_extra={"example": "Нужна помощь в уходе за животными в приюте"}
    )
    address: Optional[str] = Field(
        None,
        description="Адрес проведения события",
        examples=["ул. Ленина, д. 10", "Центральный парк"],
        json_schema_extra={"example": "ул. Ленина, д. 10"}
    )
    contact: Optional[str] = Field(
        None,
        description="Контактная информация",
        examples=["+79991234567", "example@mail.ru"],
        json_schema_extra={"example": "+79991234567"}
    )
    what_to_do: Optional[str] = Field(
        None,
        description="Что нужно делать",
        examples=["Кормить животных, убирать вольеры"],
        json_schema_extra={"example": "Кормить животных, убирать вольеры"}
    )
    date: Optional[datetime] = Field(
        None,
        description="Дата и время события",
        examples=["2024-01-15T10:00:00Z"],
        json_schema_extra={"example": "2024-01-15T10:00:00Z"}
    )
    city_id: Optional[int] = Field(
        None,
        description="ID города",
        examples=[1, 2, 3],
        json_schema_extra={"example": 1}
    )
    tag_ids: Optional[List[int]] = Field(
        None,
        description="Список ID тегов события",
        examples=[[1, 2, 3], [4, 5]],
        json_schema_extra={"example": [1, 2, 3]}
    )


class SEvent(BaseModel):
    id: int
    title: str
    description: str
    address: str
    contact: str
    what_to_do: str
    date: datetime
    city_id: int
    created_by: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class SEventWithTags(SEvent):
    tags: List[str] = Field(default_factory=list)
    creator_username: str


class SEventWithMatch(SEventWithTags):
    match_percentage: float = Field(ge=0, le=100)


class SEventFeedResponse(BaseModel):
    events: List[SEventWithMatch]
    total_count: int
    page: int
    page_size: int
    total_pages: int


class SEventListResponse(BaseModel):
    events: List[SEventWithTags]
    total_count: int
    page: int
    page_size: int
    total_pages: int