from fastapi import APIRouter, HTTPException, Query
from repositories.tag import TagRepository
from schemas.tag import STag, STagCreate




router = APIRouter(
    prefix="/tags",
    tags=["Теги"]
)


@router.get("", response_model=list[STag])
async def get_tags(
    page: int = Query(1, ge=1, description="Номер страницы"),
    page_size: int = Query(20, ge=1, le=100, description="Размер страницы")
):
    """Получить список тегов с пагинацией"""
    try:
        tags = await TagRepository.get_all_tags(page, page_size)
        return tags
    except Exception as e:
        raise HTTPException(status_code=500, detail="Ошибка при получении списка тегов")


@router.get("/{tag_id}", response_model=STag)
async def get_tag(tag_id: int):
    """Получить тег по ID"""
    try:
        tag = await TagRepository.get_tag_by_id(tag_id)
        if not tag:
            raise HTTPException(status_code=404, detail="Тег не найден")
        return tag
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Ошибка при получении тега")


@router.post("", response_model=STag)
async def create_tag(tag_data: STagCreate):
    """Создать новый тег (для админов)"""
    try:
        tag = await TagRepository.create_tag(tag_data)
        return tag
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Ошибка при создании тега")