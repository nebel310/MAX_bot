from database import new_session
from models.city import CityOrm
from schemas.city import SCityCreate
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError




class CityRepository:
    @classmethod
    async def get_all_cities(cls, page: int, page_size: int):
        """Получить список городов с пагинацией"""
        async with new_session() as session:
            offset = (page - 1) * page_size
            query = select(CityOrm).offset(offset).limit(page_size)
            result = await session.execute(query)
            cities = result.scalars().all()
            return cities
    
    
    @classmethod
    async def get_city_by_id(cls, city_id: int):
        """Получить город по ID"""
        async with new_session() as session:
            query = select(CityOrm).where(CityOrm.id == city_id)
            result = await session.execute(query)
            city = result.scalars().first()
            return city
    
    
    @classmethod
    async def create_city(cls, city_data: SCityCreate):
        """Создать новый город"""
        async with new_session() as session:
            city = CityOrm(name=city_data.name)
            session.add(city)
            try:
                await session.commit()
                await session.refresh(city)
                return city
            except IntegrityError:
                await session.rollback()
                raise ValueError("Город с таким названием уже существует")
    
    
    @classmethod
    async def get_total_count(cls):
        """Получить общее количество городов"""
        async with new_session() as session:
            query = select(CityOrm)
            result = await session.execute(query)
            return len(result.scalars().all())