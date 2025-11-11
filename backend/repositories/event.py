from database import new_session
from models.event import EventOrm, EventTagOrm
from models.auth import UserOrm
from models.user_profile import UserProfileOrm
from models.tag import TagOrm
from schemas.event import SEventCreate, SEventUpdate, SEventFilter
from sqlalchemy import select, delete, update, and_, func, distinct, not_
from sqlalchemy.exc import IntegrityError




class EventRepository:
    @classmethod
    async def create_event(cls, event_data: SEventCreate, user_id: int):
        """Создать новое событие"""
        async with new_session() as session:
            event = EventOrm(
                title=event_data.title,
                description=event_data.description,
                address=event_data.address,
                contact=event_data.contact,
                what_to_do=event_data.what_to_do,
                date=event_data.date,
                city_id=event_data.city_id,
                created_by=user_id
            )
            session.add(event)
            await session.flush()
            
            for tag_id in event_data.tag_ids:
                event_tag = EventTagOrm(
                    event_id=event.id,
                    tag_id=tag_id
                )
                session.add(event_tag)
            
            await session.commit()
            await session.refresh(event)
            return event
    
    
    @classmethod
    async def get_event_by_id(cls, event_id: int):
        """Получить событие по ID"""
        async with new_session() as session:
            query = select(EventOrm).where(EventOrm.id == event_id)
            result = await session.execute(query)
            return result.scalars().first()
    
    
    @classmethod
    async def get_event_with_details(cls, event_id: int):
        """Получить событие с деталями (теги, имя создателя)"""
        async with new_session() as session:
            event_query = select(EventOrm).where(EventOrm.id == event_id)
            event_result = await session.execute(event_query)
            event = event_result.scalars().first()
            
            if not event:
                return None
            
            creator_query = select(UserOrm.username).where(UserOrm.id == event.created_by)
            creator_result = await session.execute(creator_query)
            creator_username = creator_result.scalar()
            
            tags = await cls.get_event_tags(event_id)
            
            return {
                "event": event,
                "creator_username": creator_username,
                "tags": tags
            }
    
    
    @classmethod
    async def update_event(cls, event_id: int, event_data: SEventUpdate):
        """Обновить событие"""
        async with new_session() as session:
            update_data = {}
            if event_data.title is not None:
                update_data["title"] = event_data.title
            if event_data.description is not None:
                update_data["description"] = event_data.description
            if event_data.address is not None:
                update_data["address"] = event_data.address
            if event_data.contact is not None:
                update_data["contact"] = event_data.contact
            if event_data.what_to_do is not None:
                update_data["what_to_do"] = event_data.what_to_do
            if event_data.date is not None:
                update_data["date"] = event_data.date
            if event_data.city_id is not None:
                update_data["city_id"] = event_data.city_id
            
            if update_data:
                stmt = (
                    update(EventOrm)
                    .where(EventOrm.id == event_id)
                    .values(**update_data)
                )
                await session.execute(stmt)
            
            if event_data.tag_ids is not None:
                delete_query = delete(EventTagOrm).where(EventTagOrm.event_id == event_id)
                await session.execute(delete_query)
                
                for tag_id in event_data.tag_ids:
                    event_tag = EventTagOrm(
                        event_id=event_id,
                        tag_id=tag_id
                    )
                    session.add(event_tag)
            
            await session.commit()
            return await cls.get_event_by_id(event_id)
    
    
    @classmethod
    async def delete_event(cls, event_id: int):
        """Удалить событие"""
        async with new_session() as session:
            delete_tags_query = delete(EventTagOrm).where(EventTagOrm.event_id == event_id)
            await session.execute(delete_tags_query)
            
            delete_event_query = delete(EventOrm).where(EventOrm.id == event_id)
            result = await session.execute(delete_event_query)
            await session.commit()
            
            return result.rowcount > 0
    
    
    @classmethod
    async def get_event_tags(cls, event_id: int):
        """Получить теги события"""
        async with new_session() as session:
            query = (
                select(TagOrm.name)
                .select_from(EventTagOrm)
                .join(TagOrm, EventTagOrm.tag_id == TagOrm.id)
                .where(EventTagOrm.event_id == event_id)
            )
            result = await session.execute(query)
            return result.scalars().all()
    
    
    @classmethod
    async def get_events_feed(cls, user_id: int, page: int, page_size: int, event_filter: SEventFilter = None):
        """Получить ленту событий для пользователя с пагинацией и фильтрацией"""
        async with new_session() as session:
            user_profile_query = select(UserProfileOrm).where(UserProfileOrm.user_id == user_id)
            user_profile_result = await session.execute(user_profile_query)
            user_profile = user_profile_result.scalars().first()
            
            if not user_profile or not user_profile.city_id:
                return [], 0
            
            base_query = (
                select(EventOrm, UserOrm.username)
                .join(UserOrm, EventOrm.created_by == UserOrm.id)
                .where(EventOrm.city_id == user_profile.city_id)
            )
            
            count_query = select(func.count()).select_from(EventOrm).where(EventOrm.city_id == user_profile.city_id)
            
            if event_filter:
                if event_filter.include_tags:
                    events_with_include_tags = (
                        select(EventTagOrm.event_id)
                        .where(EventTagOrm.tag_id.in_(event_filter.include_tags))
                        .distinct()
                    )
                    base_query = base_query.where(EventOrm.id.in_(events_with_include_tags))
                    count_query = count_query.where(EventOrm.id.in_(events_with_include_tags))
                
                if event_filter.exclude_tags:
                    events_with_exclude_tags = (
                        select(EventTagOrm.event_id)
                        .where(EventTagOrm.tag_id.in_(event_filter.exclude_tags))
                        .distinct()
                    )
                    base_query = base_query.where(not_(EventOrm.id.in_(events_with_exclude_tags)))
                    count_query = count_query.where(not_(EventOrm.id.in_(events_with_exclude_tags)))
            
            total_count_result = await session.execute(count_query)
            total_count = total_count_result.scalar()
            
            offset = (page - 1) * page_size
            events_query = base_query.offset(offset).limit(page_size)
            events_result = await session.execute(events_query)
            events_data = events_result.all()
            
            events_with_details = []
            for event, creator_username in events_data:
                tags = await cls.get_event_tags(event.id)
                events_with_details.append({
                    "event": event,
                    "creator_username": creator_username,
                    "tags": tags
                })
            
            return events_with_details, total_count
    
    
    @classmethod
    async def get_user_events(cls, user_id: int, page: int, page_size: int):
        """Получить события созданные пользователем"""
        async with new_session() as session:
            base_query = (
                select(EventOrm, UserOrm.username)
                .join(UserOrm, EventOrm.created_by == UserOrm.id)
                .where(EventOrm.created_by == user_id)
            )
            
            count_query = select(func.count()).select_from(EventOrm).where(EventOrm.created_by == user_id)
            total_count_result = await session.execute(count_query)
            total_count = total_count_result.scalar()
            
            offset = (page - 1) * page_size
            events_query = base_query.offset(offset).limit(page_size)
            events_result = await session.execute(events_query)
            events_data = events_result.all()
            
            events_with_details = []
            for event, creator_username in events_data:
                tags = await cls.get_event_tags(event.id)
                events_with_details.append({
                    "event": event,
                    "creator_username": creator_username,
                    "tags": tags
                })
            
            return events_with_details, total_count
    
    
    @classmethod
    async def is_event_owner(cls, event_id: int, user_id: int):
        """Проверить, является ли пользователь создателем события"""
        async with new_session() as session:
            query = select(EventOrm).where(
                and_(EventOrm.id == event_id, EventOrm.created_by == user_id)
            )
            result = await session.execute(query)
            return result.scalars().first() is not None