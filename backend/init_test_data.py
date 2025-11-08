from database import new_session
from models.city import CityOrm
from models.tag import TagOrm




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


async def init_all_test_data():
    """Инициализация всех тестовых данных"""
    await init_cities()
    await init_tags()
    print("Тестовые данные созданы")