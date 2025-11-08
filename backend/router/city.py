from fastapi import APIRouter, HTTPException, Query
from repositories.city import CityRepository
from schemas.city import SCity, SCityCreate




router = APIRouter(
    prefix="/cities",
    tags=["Города"]
)


@router.get("", response_model=list[SCity])
async def get_cities(
    page: int = Query(1, ge=1, description="Номер страницы"),
    page_size: int = Query(20, ge=1, le=100, description="Размер страницы")
):
    """Получить список городов с пагинацией"""
    try:
        cities = await CityRepository.get_all_cities(page, page_size)
        return cities
    except Exception as e:
        raise HTTPException(status_code=500, detail="Ошибка при получении списка городов")


@router.get("/{city_id}", response_model=SCity)
async def get_city(city_id: int):
    """Получить город по ID"""
    try:
        city = await CityRepository.get_city_by_id(city_id)
        if not city:
            raise HTTPException(status_code=404, detail="Город не найден")
        return city
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Ошибка при получении города")


@router.post("", response_model=SCity)
async def create_city(city_data: SCityCreate):
    """Создать новый город (для админов)"""
    try:
        city = await CityRepository.create_city(city_data)
        return city
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Ошибка при создании города")