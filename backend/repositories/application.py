from database import new_session
from models.application import ApplicationOrm
from models.event import EventOrm, EventTagOrm
from models.auth import UserOrm
from models.user_profile import UserProfileOrm, UserInterestOrm
from models.tag import TagOrm
from schemas.application import SApplicationCreate, SApplicationUpdate
from sqlalchemy import select, delete, update, and_, func
from sqlalchemy.exc import IntegrityError




class ApplicationRepository:
    @classmethod
    async def create_application(cls, application_data: SApplicationCreate, user_id: int):
        """Создать отклик на событие"""
        async with new_session() as session:
            event_query = select(EventOrm).where(EventOrm.id == application_data.event_id)
            event_result = await session.execute(event_query)
            event = event_result.scalars().first()
            
            if not event:
                raise ValueError("Событие не найдено")
            
            existing_application_query = select(ApplicationOrm).where(
                and_(
                    ApplicationOrm.user_id == user_id,
                    ApplicationOrm.event_id == application_data.event_id
                )
            )
            existing_application_result = await session.execute(existing_application_query)
            existing_application = existing_application_result.scalars().first()
            
            if existing_application:
                raise ValueError("Вы уже подали заявку на это событие")
            
            application = ApplicationOrm(
                user_id=user_id,
                event_id=application_data.event_id,
                status="pending"
            )
            session.add(application)
            await session.commit()
            await session.refresh(application)
            return application
    
    
    @classmethod
    async def get_application_by_id(cls, application_id: int):
        """Получить отклик по ID"""
        async with new_session() as session:
            query = select(ApplicationOrm).where(ApplicationOrm.id == application_id)
            result = await session.execute(query)
            return result.scalars().first()
    
    
    @classmethod
    async def get_user_applications(cls, user_id: int, page: int, page_size: int):
        """Получить отклики пользователя с пагинацией"""
        async with new_session() as session:
            base_query = (
                select(ApplicationOrm, EventOrm.title, EventOrm.date, EventOrm.address, UserOrm.username)
                .join(EventOrm, ApplicationOrm.event_id == EventOrm.id)
                .join(UserOrm, EventOrm.created_by == UserOrm.id)
                .where(ApplicationOrm.user_id == user_id)
            )
            
            count_query = select(func.count()).select_from(ApplicationOrm).where(ApplicationOrm.user_id == user_id)
            total_count_result = await session.execute(count_query)
            total_count = total_count_result.scalar()
            
            offset = (page - 1) * page_size
            applications_query = base_query.offset(offset).limit(page_size)
            applications_result = await session.execute(applications_query)
            applications_data = applications_result.all()
            
            applications = []
            for app, event_title, event_date, event_address, event_creator_username in applications_data:
                applications.append({
                    "application": app,
                    "event_title": event_title,
                    "event_date": event_date,
                    "event_address": event_address,
                    "event_creator_username": event_creator_username
                })
            
            return applications, total_count
    
    
    @classmethod
    async def get_event_applications(cls, event_id: int, user_id: int):
        """Получить отклики на событие (только для создателя события)"""
        async with new_session() as session:
            event_query = select(EventOrm).where(EventOrm.id == event_id)
            event_result = await session.execute(event_query)
            event = event_result.scalars().first()
            
            if not event or event.created_by != user_id:
                raise ValueError("Недостаточно прав для просмотра откликов на это событие")
            
            applications_query = (
                select(ApplicationOrm)
                .where(ApplicationOrm.event_id == event_id)
            )
            applications_result = await session.execute(applications_query)
            applications = applications_result.scalars().all()
            
            return applications
    
    
    @classmethod
    async def get_approved_applications_for_event(cls, event_id: int, user_id: int):
        """Получить подтвержденные отклики на событие (для подтверждения участия)"""
        async with new_session() as session:
            event_query = select(EventOrm).where(EventOrm.id == event_id)
            event_result = await session.execute(event_query)
            event = event_result.scalars().first()
            
            if not event or event.created_by != user_id:
                raise ValueError("Недостаточно прав для просмотра откликов на это событие")
            
            applications_query = (
                select(ApplicationOrm, UserOrm.username)
                .join(UserOrm, ApplicationOrm.user_id == UserOrm.id)
                .where(
                    and_(
                        ApplicationOrm.event_id == event_id,
                        ApplicationOrm.status == "approved"
                    )
                )
            )
            applications_result = await session.execute(applications_query)
            applications_data = applications_result.all()
            
            applications = []
            for app, username in applications_data:
                user_profile_query = select(UserProfileOrm).where(UserProfileOrm.user_id == app.user_id)
                user_profile_result = await session.execute(user_profile_query)
                user_profile = user_profile_result.scalars().first()
                
                current_rating = user_profile.rating if user_profile else 0
                current_participation_count = user_profile.participation_count if user_profile else 0
                
                applications.append({
                    "application": app,
                    "username": username,
                    "current_rating": current_rating,
                    "current_participation_count": current_participation_count
                })
            
            return applications
    
    
    @classmethod
    async def confirm_participation(cls, event_id: int, user_ids: list[int], rating_points: int, admin_user_id: int):
        """Подтвердить участие волонтеров в событии"""
        async with new_session() as session:
            event_query = select(EventOrm).where(EventOrm.id == event_id)
            event_result = await session.execute(event_query)
            event = event_result.scalars().first()
            
            if not event or event.created_by != admin_user_id:
                raise ValueError("Недостаточно прав для подтверждения участия в этом событии")
            
            updated_users = []
            
            for user_id in user_ids:
                application_query = select(ApplicationOrm).where(
                    and_(
                        ApplicationOrm.event_id == event_id,
                        ApplicationOrm.user_id == user_id,
                        ApplicationOrm.status == "approved"
                    )
                )
                application_result = await session.execute(application_query)
                application = application_result.scalars().first()
                
                if not application:
                    continue
                
                application.status = "participated"
                
                user_profile_query = select(UserProfileOrm).where(UserProfileOrm.user_id == user_id)
                user_profile_result = await session.execute(user_profile_query)
                user_profile = user_profile_result.scalars().first()
                
                if user_profile:
                    user_profile.participation_count += 1
                    user_profile.rating += rating_points
                else:
                    user_profile = UserProfileOrm(
                        user_id=user_id,
                        participation_count=1,
                        rating=rating_points
                    )
                    session.add(user_profile)
                
                updated_users.append(user_id)
            
            await session.commit()
            return updated_users
    
    
    @classmethod
    async def get_application_with_details(cls, application_id: int, current_user_id: int):
        """Получить отклик с деталями (для админа)"""
        async with new_session() as session:
            application_query = select(ApplicationOrm).where(ApplicationOrm.id == application_id)
            application_result = await session.execute(application_query)
            application = application_result.scalars().first()
            
            if not application:
                return None
            
            event_query = select(EventOrm).where(EventOrm.id == application.event_id)
            event_result = await session.execute(event_query)
            event = event_result.scalars().first()
            
            if not event or event.created_by != current_user_id:
                raise ValueError("Недостаточно прав для просмотра этого отклика")
            
            user_query = select(UserOrm).where(UserOrm.id == application.user_id)
            user_result = await session.execute(user_query)
            user = user_result.scalars().first()
            
            user_profile_query = select(UserProfileOrm).where(UserProfileOrm.user_id == application.user_id)
            user_profile_result = await session.execute(user_profile_query)
            user_profile = user_profile_result.scalars().first()
            
            user_interests_query = (
                select(TagOrm.name)
                .select_from(UserInterestOrm)
                .join(TagOrm, UserInterestOrm.tag_id == TagOrm.id)
                .where(UserInterestOrm.user_id == application.user_id)
            )
            user_interests_result = await session.execute(user_interests_query)
            user_interests = user_interests_result.scalars().all()
            
            event_tags_query = (
                select(TagOrm.name)
                .select_from(EventTagOrm)
                .join(TagOrm, EventTagOrm.tag_id == TagOrm.id)
                .where(EventTagOrm.event_id == application.event_id)
            )
            event_tags_result = await session.execute(event_tags_query)
            event_tags = event_tags_result.scalars().all()
            
            user_interest_set = set(user_interests)
            event_tag_set = set(event_tags)
            common_tags = user_interest_set.intersection(event_tag_set)
            match_percentage = (len(common_tags) / len(event_tag_set)) * 100 if event_tag_set else 0
            
            return {
                "application": application,
                "user_username": user.username,
                "user_rating": user_profile.rating if user_profile else 0,
                "user_participation_count": user_profile.participation_count if user_profile else 0,
                "user_city_id": user_profile.city_id if user_profile else None,
                "user_about_me": user_profile.about_me if user_profile else None,
                "user_interests": user_interests,
                "match_percentage": round(match_percentage, 2)
            }
    
    
    @classmethod
    async def update_application(cls, application_id: int, application_data: SApplicationUpdate, current_user_id: int):
        """Обновить отклик (только создатель события)"""
        async with new_session() as session:
            application = await cls.get_application_by_id(application_id)
            if not application:
                raise ValueError("Отклик не найден")
            
            event_query = select(EventOrm).where(EventOrm.id == application.event_id)
            event_result = await session.execute(event_query)
            event = event_result.scalars().first()
            
            if not event or event.created_by != current_user_id:
                raise ValueError("Недостаточно прав для обновления этого отклика")
            
            update_data = {}
            if application_data.status is not None:
                update_data["status"] = application_data.status
            if application_data.rejection_reason is not None:
                update_data["rejection_reason"] = application_data.rejection_reason
            
            if update_data:
                stmt = (
                    update(ApplicationOrm)
                    .where(ApplicationOrm.id == application_id)
                    .values(**update_data)
                )
                await session.execute(stmt)
                await session.commit()
            
            return await cls.get_application_by_id(application_id)
    
    
    @classmethod
    async def delete_application(cls, application_id: int, user_id: int):
        """Удалить отклик (только владелец отклика)"""
        async with new_session() as session:
            application = await cls.get_application_by_id(application_id)
            if not application:
                raise ValueError("Отклик не найден")
            
            if application.user_id != user_id:
                raise ValueError("Недостаточно прав для удаления этого отклика")
            
            delete_query = delete(ApplicationOrm).where(ApplicationOrm.id == application_id)
            await session.execute(delete_query)
            await session.commit()
            
            return True