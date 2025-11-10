from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List




class SUserProfileBase(BaseModel):
    city_id: Optional[int] = Field(
        None, 
        description="ID города пользователя",
        examples=[1, 2, 3],
        json_schema_extra={"example": 1}
    )
    about_me: Optional[str] = Field(
        None, 
        description="Описание пользователя о себе",
        examples=["Люблю помогать людям", "Активный волонтер с 2020 года"],
        json_schema_extra={"example": "Люблю помогать людям и животным"}
    )


class SUserProfileCreate(SUserProfileBase):
    user_id: int
    rating: int = Field(
        default=0,
        description="Рейтинг пользователя",
        json_schema_extra={"example": 0}
    )
    participation_count: int = Field(
        default=0,
        description="Количество участий в мероприятиях",
        json_schema_extra={"example": 0}
    )


class SUserProfileUpdate(SUserProfileBase):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "city_id": 1,
                    "about_me": "Новое описание о себе"
                },
                {
                    "city_id": 2
                },
                {
                    "about_me": "Обновил только описание"
                },
                {}
            ]
        }
    )


class SUserProfileFullUpdate(BaseModel):
    """Полная схема обновления профиля (все поля опциональны)"""
    city_id: Optional[int] = Field(
        None, 
        description="ID города пользователя",
        examples=[1, 2, 3],
        json_schema_extra={"example": 1}
    )
    about_me: Optional[str] = Field(
        None, 
        description="Описание пользователя о себе",
        examples=["Люблю помогать людям", "Активный волонтер с 2020 года"],
        json_schema_extra={"example": "Люблю помогать людям и животным"}
    )
    rating: Optional[int] = Field(
        None,
        description="Рейтинг пользователя (системное поле)",
        examples=[10, 50, 100],
        json_schema_extra={"example": 50}
    )
    participation_count: Optional[int] = Field(
        None,
        description="Количество участий в мероприятиях (системное поле)",
        examples=[1, 5, 10],
        json_schema_extra={"example": 5}
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "city_id": 1,
                    "about_me": "Новое описание о себе"
                },
                {
                    "rating": 100,
                    "participation_count": 10
                },
                {
                    "city_id": 2,
                    "rating": 50
                },
                {
                    "about_me": "Только описание"
                },
                {}
            ]
        }
    )


class SUserProfile(SUserProfileBase):
    id: int
    user_id: int
    rating: int = Field(description="Рейтинг пользователя")
    participation_count: int = Field(description="Количество участий в мероприятиях")
    
    model_config = ConfigDict(from_attributes=True)


class SUserInterestCreate(BaseModel):
    tag_ids: List[int] = Field(
        description="Список ID тегов интересов",
        examples=[[1, 2, 3], [4, 5]],
        json_schema_extra={"example": [1, 2, 3]}
    )


class SUserInterest(BaseModel):
    id: int
    user_id: int
    tag_id: int
    
    model_config = ConfigDict(from_attributes=True)


class SUserProfileWithInterests(SUserProfile):
    interests: List[str] = Field(
        default=[],
        description="Список названий интересов пользователя"
    )


class SLeaderboardItem(BaseModel):
    user_id: int
    username: str
    rating: int
    participation_count: int
    position: int
    
    model_config = ConfigDict(from_attributes=True)


class SLeaderboard(BaseModel):
    top_users: List[SLeaderboardItem]
    current_user_position: Optional[SLeaderboardItem] = None