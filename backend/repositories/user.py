from database import new_session
from models.user_profile import UserProfileOrm, UserInterestOrm
from models.auth import UserOrm
from models.tag import TagOrm
from schemas.user import SUserProfileCreate, SUserProfileUpdate, SUserProfileFullUpdate, SUserInterestCreate
from sqlalchemy import select, delete, update, func, and_
from sqlalchemy.exc import IntegrityError




class UserProfileRepository:
    @classmethod
    async def get_profile_by_user_id(cls, user_id: int):
        """Получить профиль пользователя по user_id"""
        async with new_session() as session:
            query = select(UserProfileOrm).where(UserProfileOrm.user_id == user_id)
            result = await session.execute(query)
            return result.scalars().first()
    
    
    @classmethod
    async def create_or_update_profile(cls, profile_data: SUserProfileCreate):
        """Создать или обновить профиль пользователя"""
        async with new_session() as session:
            existing_profile = await cls.get_profile_by_user_id(profile_data.user_id)
            
            if existing_profile:
                stmt = (
                    update(UserProfileOrm)
                    .where(UserProfileOrm.user_id == profile_data.user_id)
                    .values(
                        city_id=profile_data.city_id,
                        about_me=profile_data.about_me
                    )
                )
                await session.execute(stmt)
            else:
                profile = UserProfileOrm(
                    user_id=profile_data.user_id,
                    city_id=profile_data.city_id,
                    about_me=profile_data.about_me,
                    rating=profile_data.rating,
                    participation_count=profile_data.participation_count
                )
                session.add(profile)
            
            await session.commit()
            
            if not existing_profile:
                await session.refresh(profile)
                return profile
            return await cls.get_profile_by_user_id(profile_data.user_id)
    
    
    @classmethod
    async def update_profile(cls, user_id: int, profile_data: SUserProfileUpdate):
        """Обновить профиль пользователя (только разрешенные поля)"""
        async with new_session() as session:
            update_data = {}
            if profile_data.city_id is not None:
                update_data["city_id"] = profile_data.city_id
            if profile_data.about_me is not None:
                update_data["about_me"] = profile_data.about_me
            
            if update_data:
                stmt = (
                    update(UserProfileOrm)
                    .where(UserProfileOrm.user_id == user_id)
                    .values(**update_data)
                )
                await session.execute(stmt)
                await session.commit()
            
            return await cls.get_profile_by_user_id(user_id)
    
    
    @classmethod
    async def partial_update_profile(cls, user_id: int, profile_data: SUserProfileUpdate):
        """Частичное обновление профиля пользователя"""
        return await cls.update_profile(user_id, profile_data)
    
    
    @classmethod
    async def full_update_profile(cls, user_id: int, profile_data: SUserProfileFullUpdate):
        """Полное обновление профиля пользователя (все поля)"""
        async with new_session() as session:
            update_data = {}
            
            if profile_data.city_id is not None:
                update_data["city_id"] = profile_data.city_id
            if profile_data.about_me is not None:
                update_data["about_me"] = profile_data.about_me
            if profile_data.rating is not None:
                update_data["rating"] = profile_data.rating
            if profile_data.participation_count is not None:
                update_data["participation_count"] = profile_data.participation_count
            
            if update_data:
                stmt = (
                    update(UserProfileOrm)
                    .where(UserProfileOrm.user_id == user_id)
                    .values(**update_data)
                )
                await session.execute(stmt)
                await session.commit()
            
            return await cls.get_profile_by_user_id(user_id)
    
    
    @classmethod
    async def update_user_interests(cls, user_id: int, interest_data: SUserInterestCreate):
        """Обновить интересы пользователя"""
        async with new_session() as session:
            delete_query = delete(UserInterestOrm).where(UserInterestOrm.user_id == user_id)
            await session.execute(delete_query)
            
            for tag_id in interest_data.tag_ids:
                interest = UserInterestOrm(user_id=user_id, tag_id=tag_id)
                session.add(interest)
            
            await session.commit()
    
    
    @classmethod
    async def get_user_interests(cls, user_id: int):
        """Получить интересы пользователя"""
        async with new_session() as session:
            query = (
                select(TagOrm.name)
                .select_from(UserInterestOrm)
                .join(TagOrm, UserInterestOrm.tag_id == TagOrm.id)
                .where(UserInterestOrm.user_id == user_id)
            )
            result = await session.execute(query)
            return result.scalars().all()
    
    
    @classmethod
    async def get_profile_with_interests(cls, user_id: int):
        """Получить профиль пользователя с интересами"""
        profile = await cls.get_profile_by_user_id(user_id)
        interests = await cls.get_user_interests(user_id)
        
        return profile, interests
    
    
    @classmethod
    async def get_leaderboard(cls, top_n: int, current_user_id: int = None):
        """Получить лидерборд пользователей"""
        async with new_session() as session:
            subquery = (
                select(
                    UserOrm.id.label("user_id"),
                    UserOrm.username,
                    UserProfileOrm.rating,
                    UserProfileOrm.participation_count,
                    func.row_number().over(order_by=UserProfileOrm.rating.desc()).label("position")
                )
                .select_from(UserProfileOrm)
                .join(UserOrm, UserProfileOrm.user_id == UserOrm.id)
                .subquery()
            )
            
            top_users_query = (
                select(subquery)
                .order_by(subquery.c.rating.desc())
                .limit(top_n)
            )
            
            result = await session.execute(top_users_query)
            top_users = result.mappings().all()
            
            current_user_position = None
            if current_user_id:
                current_user_query = (
                    select(subquery)
                    .where(subquery.c.user_id == current_user_id)
                )
                result = await session.execute(current_user_query)
                current_user_data = result.mappings().first()
                
                if current_user_data:
                    current_user_position = {
                        "user_id": current_user_data.user_id,
                        "username": current_user_data.username,
                        "rating": current_user_data.rating,
                        "participation_count": current_user_data.participation_count,
                        "position": current_user_data.position
                    }
            
            return top_users, current_user_position
    
    
    @classmethod
    async def update_rating(cls, user_id: int, rating_change: int):
        """Обновить рейтинг пользователя (внутренний метод)"""
        async with new_session() as session:
            stmt = (
                update(UserProfileOrm)
                .where(UserProfileOrm.user_id == user_id)
                .values(rating=UserProfileOrm.rating + rating_change)
            )
            await session.execute(stmt)
            await session.commit()
    
    
    @classmethod
    async def increment_participation_count(cls, user_id: int):
        """Увеличить счетчик участий пользователя (внутренний метод)"""
        async with new_session() as session:
            stmt = (
                update(UserProfileOrm)
                .where(UserProfileOrm.user_id == user_id)
                .values(participation_count=UserProfileOrm.participation_count + 1)
            )
            await session.execute(stmt)
            await session.commit()