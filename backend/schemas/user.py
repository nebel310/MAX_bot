from pydantic import BaseModel, ConfigDict
from typing import Optional, List




class SUserProfileBase(BaseModel):
    city_id: Optional[int] = None
    about_me: Optional[str] = None


class SUserProfileCreate(SUserProfileBase):
    user_id: int
    rating: int = 0
    participation_count: int = 0


class SUserProfileUpdate(SUserProfileBase):
    pass


class SUserProfile(SUserProfileBase):
    id: int
    user_id: int
    rating: int
    participation_count: int
    
    model_config = ConfigDict(from_attributes=True)


class SUserInterestCreate(BaseModel):
    tag_ids: List[int]


class SUserInterest(BaseModel):
    id: int
    user_id: int
    tag_id: int
    
    model_config = ConfigDict(from_attributes=True)


class SUserProfileWithInterests(SUserProfile):
    interests: List[str] = []


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