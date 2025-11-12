from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import Optional, List




class SFundBase(BaseModel):
    title: str = Field(
        description="Название фонда",
        examples=["Помощь детям-сиротам", "Защита окружающей среды"],
        json_schema_extra={"example": "Помощь детям-сиротам"}
    )
    description: str = Field(
        description="Описание фонда",
        examples=["Сбор средств на образовательные программы для детей-сирот"],
        json_schema_extra={"example": "Сбор средств на образовательные программы для детей-сирот"}
    )
    requisites: str = Field(
        description="Реквизиты для доната",
        examples=["СБЕР 2202 2002 2002 2002", "Тинькофф 5536 9138 1234 5678"],
        json_schema_extra={"example": "СБЕР 2202 2002 2002 2002"}
    )
    target_amount: int = Field(
        description="Целевая сумма для сбора",
        examples=[100000, 50000, 200000],
        json_schema_extra={"example": 100000}
    )
    rating_per_100: int = Field(
        description="Рейтинг за каждые 100 рублей доната",
        examples=[1, 2, 5],
        json_schema_extra={"example": 1}
    )
    end_date: Optional[datetime] = Field(
        None,
        description="Дата окончания сбора (null = бессрочно)",
        examples=["2024-12-31T23:59:59Z"],
        json_schema_extra={"example": "2024-12-31T23:59:59Z"}
    )


class SFundCreate(SFundBase):
    tag_ids: List[int] = Field(
        description="Список ID тегов фонда",
        examples=[[1, 2, 3], [4, 5]],
        json_schema_extra={"example": [1, 2, 3]}
    )


class SFundUpdate(BaseModel):
    title: Optional[str] = Field(
        None,
        description="Название фонда",
        examples=["Помощь детям-сиротам", "Защита окружающей среды"],
        json_schema_extra={"example": "Помощь детям-сиротам"}
    )
    description: Optional[str] = Field(
        None,
        description="Описание фонда",
        examples=["Сбор средств на образовательные программы для детей-сирот"],
        json_schema_extra={"example": "Сбор средств на образовательные программы для детей-сирот"}
    )
    requisites: Optional[str] = Field(
        None,
        description="Реквизиты для доната",
        examples=["СБЕР 2202 2002 2002 2002", "Тинькофф 5536 9138 1234 5678"],
        json_schema_extra={"example": "СБЕР 2202 2002 2002 2002"}
    )
    target_amount: Optional[int] = Field(
        None,
        description="Целевая сумма для сбора",
        examples=[100000, 50000, 200000],
        json_schema_extra={"example": 100000}
    )
    collected_amount: Optional[int] = Field(
        None,
        description="Собранная сумма",
        examples=[50000, 75000, 100000],
        json_schema_extra={"example": 50000}
    )
    rating_per_100: Optional[int] = Field(
        None,
        description="Рейтинг за каждые 100 рублей доната",
        examples=[1, 2, 5],
        json_schema_extra={"example": 1}
    )
    end_date: Optional[datetime] = Field(
        None,
        description="Дата окончания сбора (null = бессрочно)",
        examples=["2024-12-31T23:59:59Z"],
        json_schema_extra={"example": "2024-12-31T23:59:59Z"}
    )
    status: Optional[str] = Field(
        None,
        description="Статус фонда",
        examples=["active", "completed"],
        json_schema_extra={"example": "active"}
    )
    tag_ids: Optional[List[int]] = Field(
        None,
        description="Список ID тегов фонда",
        examples=[[1, 2, 3], [4, 5]],
        json_schema_extra={"example": [1, 2, 3]}
    )


class SFund(BaseModel):
    id: int
    title: str
    description: str
    requisites: str
    target_amount: int
    collected_amount: int
    rating_per_100: int
    created_by: int
    created_at: datetime
    end_date: Optional[datetime]
    status: str
    
    model_config = ConfigDict(from_attributes=True)


class SFundWithTags(SFund):
    tags: List[str] = Field(default_factory=list)
    creator_username: str


class SFundWithMatch(SFundWithTags):
    match_percentage: float = Field(ge=0, le=100)


class SFundFeedResponse(BaseModel):
    funds: List[SFundWithMatch]
    total_count: int
    page: int
    page_size: int
    total_pages: int


class SFundListResponse(BaseModel):
    funds: List[SFundWithTags]
    total_count: int
    page: int
    page_size: int
    total_pages: int


class SDonationCreate(BaseModel):
    fund_id: int = Field(description="ID фонда")
    amount: int = Field(description="Сумма доната в рублях")


class SDonation(SDonationCreate):
    id: int
    user_id: int
    rating_earned: int
    donated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class SDonationWithFund(SDonation):
    fund_title: str
    fund_status: str