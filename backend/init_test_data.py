from database import new_session
from models.city import CityOrm
from models.tag import TagOrm
from models.admin import AdminOrm
from sqlalchemy import select




async def init_cities():
    """Инициализация тестовых городов"""
    async with new_session() as session:
        cities = [
            CityOrm(name="Москва"),
            CityOrm(name="Санкт-Петербург"),
            CityOrm(name="Новосибирск")
        ]
        
        session.add_all(cities)
        await session.commit()


async def init_tags():
    """Инициализация тестовых тегов"""
    async with new_session() as session:
        tags = [
            TagOrm(name="Экология"),
            TagOrm(name="Образование"),
            TagOrm(name="Медицина"),
            TagOrm(name="Дети"),
            TagOrm(name="Животные")
        ]
        
        session.add_all(tags)
        await session.commit()


async def init_admins():
    """Инициализация тестовых админов"""
    async with new_session() as session:
        existing_admins = await session.execute(select(AdminOrm))
        if existing_admins.scalars().first():
            return
        
        admins = [
            AdminOrm(max_user_id="admin1"),
            AdminOrm(max_user_id="admin2"),
            AdminOrm(max_user_id="89408765")
        ]
        
        session.add_all(admins)
        await session.commit()


async def init_all_test_data():
    """Инициализация всех тестовых данных"""
    await init_cities()
    await init_tags()
    await init_admins()
    print("Тестовые данные созданы")