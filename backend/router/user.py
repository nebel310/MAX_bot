from fastapi import APIRouter, HTTPException, Depends, Query
from repositories.user import UserProfileRepository
from schemas.user import (
    SUserProfile, SUserProfileCreate, SUserProfileUpdate, SUserProfileFullUpdate,
    SUserProfileWithInterests, SUserInterestCreate, SLeaderboard
)
from models.auth import UserOrm
from utils.security import get_current_user




router = APIRouter(
    prefix="/user",
    tags=["Пользователь"]
)


@router.get("/profile", response_model=SUserProfileWithInterests)
async def get_user_profile(current_user: UserOrm = Depends(get_current_user)):
    """Получить профиль текущего пользователя с интересами"""
    try:
        profile, interests = await UserProfileRepository.get_profile_with_interests(current_user.id)
        
        if not profile:
            profile_data = SUserProfileCreate(
                user_id=current_user.id,
                city_id=None,
                about_me=None,
                rating=0,
                participation_count=0
            )
            profile = await UserProfileRepository.create_or_update_profile(profile_data)
            interests = []
        
        profile_dict = SUserProfile.model_validate(profile).model_dump()
        profile_dict["interests"] = interests
        
        return SUserProfileWithInterests(**profile_dict)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Ошибка при получении профиля")


@router.put("/profile/update", response_model=SUserProfile)
async def update_user_profile(
    profile_data: SUserProfileUpdate,
    current_user: UserOrm = Depends(get_current_user)
):
    """Полное обновление профиля пользователя
    
    Обновляет все переданные поля. Поля, которые не переданы, будут установлены в null.
    Доступные поля: city_id, about_me
    """
    try:
        profile = await UserProfileRepository.update_profile(current_user.id, profile_data)
        return profile
    except Exception as e:
        raise HTTPException(status_code=500, detail="Ошибка при обновлении профиля")


@router.patch("/profile/update", response_model=SUserProfile)
async def partial_update_user_profile(
    profile_data: SUserProfileUpdate,
    current_user: UserOrm = Depends(get_current_user)
):
    """Частичное обновление профиля пользователя
    
    Обновляет только переданные поля. Поля, которые не переданы, остаются без изменений.
    Доступные поля: city_id, about_me
    
    Примеры использования:
    - Обновить только город: `{"city_id": 1}`
    - Обновить только описание: `{"about_me": "Новое описание"}`
    - Обновить и город и описание: `{"city_id": 2, "about_me": "Новое описание"}`
    - Оставить без изменений: `{}`
    """
    try:
        profile = await UserProfileRepository.partial_update_profile(current_user.id, profile_data)
        return profile
    except Exception as e:
        raise HTTPException(status_code=500, detail="Ошибка при обновлении профиля")


@router.patch("/profile/full-update", response_model=SUserProfile)
async def full_update_user_profile(
    profile_data: SUserProfileFullUpdate,
    current_user: UserOrm = Depends(get_current_user)
):
    """Полное обновление профиля пользователя (сервисный эндпоинт)
    
    ОБНОВЛЯЕТ ЛЮБЫЕ ПОЛЯ ПРОФИЛЯ, включая системные (рейтинг, счетчик участий).
    Используется для отладки и специальных случаев разработчиком бота.
    
    Все поля опциональны. Если поле не передано, оно остается без изменений.
    
    Доступные поля:
    - city_id: ID города
    - about_me: Описание о себе  
    - rating: Рейтинг пользователя (системное поле)
    - participation_count: Количество участий (системное поле)
    
    Примеры использования:
    - Обновить рейтинг: `{"rating": 100}`
    - Обновить счетчик участий: `{"participation_count": 5}`
    - Обновить все поля: `{"city_id": 1, "about_me": "Новое описание", "rating": 50, "participation_count": 3}`
    - Обновить несколько полей: `{"city_id": 2, "rating": 75}`
    """
    try:
        profile = await UserProfileRepository.full_update_profile(current_user.id, profile_data)
        return profile
    except Exception as e:
        raise HTTPException(status_code=500, detail="Ошибка при обновлении профиля")


@router.post("/interests", response_model=dict)
async def update_user_interests(
    interest_data: SUserInterestCreate,
    current_user: UserOrm = Depends(get_current_user)
):
    """Обновить интересы пользователя"""
    try:
        await UserProfileRepository.update_user_interests(current_user.id, interest_data)
        return {"success": True, "message": "Интересы обновлены"}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Ошибка при обновлении интересов")


@router.get("/leaderboard", response_model=SLeaderboard)
async def get_leaderboard(
    top_n: int = Query(10, ge=1, le=100, description="Количество топовых пользователей"),
    current_user: UserOrm = Depends(get_current_user)
):
    """Получить лидерборд пользователей"""
    try:
        top_users, current_user_position = await UserProfileRepository.get_leaderboard(top_n, current_user.id)
        
        leaderboard_items = []
        for user in top_users:
            leaderboard_items.append({
                "user_id": user.user_id,
                "username": user.username,
                "rating": user.rating,
                "participation_count": user.participation_count,
                "position": user.position
            })
        
        current_user_item = None
        if current_user_position:
            current_user_item = {
                "user_id": current_user_position["user_id"],
                "username": current_user_position["username"],
                "rating": current_user_position["rating"],
                "participation_count": current_user_position["participation_count"],
                "position": current_user_position["position"]
            }
        
        return SLeaderboard(
            top_users=leaderboard_items,
            current_user_position=current_user_item
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail="Ошибка при получении лидерборда")