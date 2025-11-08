from database import new_session
from models.tag import TagOrm
from schemas.tag import STagCreate
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError




class TagRepository:
    @classmethod
    async def get_all_tags(cls, page: int, page_size: int):
        """Получить список тегов с пагинацией"""
        async with new_session() as session:
            offset = (page - 1) * page_size
            query = select(TagOrm).offset(offset).limit(page_size)
            result = await session.execute(query)
            tags = result.scalars().all()
            return tags
    
    
    @classmethod
    async def get_tag_by_id(cls, tag_id: int):
        """Получить тег по ID"""
        async with new_session() as session:
            query = select(TagOrm).where(TagOrm.id == tag_id)
            result = await session.execute(query)
            tag = result.scalars().first()
            return tag
    
    
    @classmethod
    async def create_tag(cls, tag_data: STagCreate):
        """Создать новый тег"""
        async with new_session() as session:
            tag = TagOrm(name=tag_data.name)
            session.add(tag)
            try:
                await session.commit()
                await session.refresh(tag)
                return tag
            except IntegrityError:
                await session.rollback()
                raise ValueError("Тег с таким названием уже существует")
    
    
    @classmethod
    async def get_total_count(cls):
        """Получить общее количество тегов"""
        async with new_session() as session:
            query = select(TagOrm)
            result = await session.execute(query)
            return len(result.scalars().all())