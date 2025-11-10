from fastapi import APIRouter, HTTPException, Depends, Query
from repositories.event import EventRepository
from repositories.user import UserProfileRepository
from schemas.event import (
    SEventCreate, SEventUpdate, SEventWithTags, 
    SEventWithMatch, SEventFeedResponse, SEventListResponse
)
from models.auth import UserOrm
from utils.security import get_current_user
from utils.matching import calculate_tag_match_percentage




router = APIRouter(
    prefix="/events",
    tags=["События"]
)


@router.post("/create", response_model=SEventWithTags)
async def create_event(
    event_data: SEventCreate,
    current_user: UserOrm = Depends(get_current_user)
):
    """Создать новое событие"""
    try:
        event = await EventRepository.create_event(event_data, current_user.id)
        
        event_details = await EventRepository.get_event_with_details(event.id)
        if not event_details:
            raise HTTPException(status_code=404, detail="Событие не найдено")
        
        event_response = SEventWithTags(
            id=event_details["event"].id,
            title=event_details["event"].title,
            description=event_details["event"].description,
            address=event_details["event"].address,
            contact=event_details["event"].contact,
            what_to_do=event_details["event"].what_to_do,
            date=event_details["event"].date,
            city_id=event_details["event"].city_id,
            created_by=event_details["event"].created_by,
            created_at=event_details["event"].created_at,
            creator_username=event_details["creator_username"],
            tags=event_details["tags"]
        )
        
        return event_response
    except Exception as e:
        raise HTTPException(status_code=500, detail="Ошибка при создании события")


@router.get("/feed", response_model=SEventFeedResponse)
async def get_events_feed(
    page: int = Query(1, ge=1, description="Номер страницы"),
    page_size: int = Query(20, ge=1, le=100, description="Размер страницы"),
    current_user: UserOrm = Depends(get_current_user)
):
    """Получить ленту событий с пагинацией и процентом совпадения"""
    try:
        events_with_details, total_count = await EventRepository.get_events_feed(
            current_user.id, page, page_size
        )
        
        events_with_match = []
        for event_data in events_with_details:
            match_percentage = await calculate_tag_match_percentage(
                current_user.id, event_data["event"].id
            )
            
            event_response = SEventWithMatch(
                id=event_data["event"].id,
                title=event_data["event"].title,
                description=event_data["event"].description,
                address=event_data["event"].address,
                contact=event_data["event"].contact,
                what_to_do=event_data["event"].what_to_do,
                date=event_data["event"].date,
                city_id=event_data["event"].city_id,
                created_by=event_data["event"].created_by,
                created_at=event_data["event"].created_at,
                creator_username=event_data["creator_username"],
                tags=event_data["tags"],
                match_percentage=match_percentage
            )
            
            events_with_match.append(event_response)
        
        total_pages = (total_count + page_size - 1) // page_size if page_size > 0 else 0
        
        return SEventFeedResponse(
            events=events_with_match,
            total_count=total_count,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail="Ошибка при получении ленты событий")


@router.get("/my-events", response_model=SEventListResponse)
async def get_my_events(
    page: int = Query(1, ge=1, description="Номер страницы"),
    page_size: int = Query(20, ge=1, le=100, description="Размер страницы"),
    current_user: UserOrm = Depends(get_current_user)
):
    """Получить события созданные текущим пользователем"""
    try:
        events_with_details, total_count = await EventRepository.get_user_events(
            current_user.id, page, page_size
        )
        
        events_with_tags = []
        for event_data in events_with_details:
            event_response = SEventWithTags(
                id=event_data["event"].id,
                title=event_data["event"].title,
                description=event_data["event"].description,
                address=event_data["event"].address,
                contact=event_data["event"].contact,
                what_to_do=event_data["event"].what_to_do,
                date=event_data["event"].date,
                city_id=event_data["event"].city_id,
                created_by=event_data["event"].created_by,
                created_at=event_data["event"].created_at,
                creator_username=event_data["creator_username"],
                tags=event_data["tags"]
            )
            
            events_with_tags.append(event_response)
        
        total_pages = (total_count + page_size - 1) // page_size if page_size > 0 else 0
        
        return SEventListResponse(
            events=events_with_tags,
            total_count=total_count,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail="Ошибка при получении событий")


@router.get("/{event_id}", response_model=SEventWithMatch)
async def get_event_details(
    event_id: int,
    current_user: UserOrm = Depends(get_current_user)
):
    """Получить подробную информацию о событии с процентом совпадения"""
    try:
        event_details = await EventRepository.get_event_with_details(event_id)
        if not event_details:
            raise HTTPException(status_code=404, detail="Событие не найдено")
        
        match_percentage = await calculate_tag_match_percentage(current_user.id, event_id)
        
        event_response = SEventWithMatch(
            id=event_details["event"].id,
            title=event_details["event"].title,
            description=event_details["event"].description,
            address=event_details["event"].address,
            contact=event_details["event"].contact,
            what_to_do=event_details["event"].what_to_do,
            date=event_details["event"].date,
            city_id=event_details["event"].city_id,
            created_by=event_details["event"].created_by,
            created_at=event_details["event"].created_at,
            creator_username=event_details["creator_username"],
            tags=event_details["tags"],
            match_percentage=match_percentage
        )
        
        return event_response
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Ошибка при получении события")


@router.put("/{event_id}/update", response_model=SEventWithTags)
async def update_event(
    event_id: int,
    event_data: SEventUpdate,
    current_user: UserOrm = Depends(get_current_user)
):
    """Обновить событие (только создатель события)"""
    try:
        is_owner = await EventRepository.is_event_owner(event_id, current_user.id)
        if not is_owner:
            raise HTTPException(status_code=403, detail="Недостаточно прав для редактирования события")
        
        event = await EventRepository.update_event(event_id, event_data)
        if not event:
            raise HTTPException(status_code=404, detail="Событие не найдено")
        
        event_details = await EventRepository.get_event_with_details(event_id)
        if not event_details:
            raise HTTPException(status_code=404, detail="Событие не найдено")
        
        event_response = SEventWithTags(
            id=event_details["event"].id,
            title=event_details["event"].title,
            description=event_details["event"].description,
            address=event_details["event"].address,
            contact=event_details["event"].contact,
            what_to_do=event_details["event"].what_to_do,
            date=event_details["event"].date,
            city_id=event_details["event"].city_id,
            created_by=event_details["event"].created_by,
            created_at=event_details["event"].created_at,
            creator_username=event_details["creator_username"],
            tags=event_details["tags"]
        )
        
        return event_response
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Ошибка при обновлении события")


@router.delete("/{event_id}/delete")
async def delete_event(
    event_id: int,
    current_user: UserOrm = Depends(get_current_user)
):
    """Удалить событие (только создатель события)"""
    try:
        is_owner = await EventRepository.is_event_owner(event_id, current_user.id)
        if not is_owner:
            raise HTTPException(status_code=403, detail="Недостаточно прав для удаления события")
        
        success = await EventRepository.delete_event(event_id)
        if not success:
            raise HTTPException(status_code=404, detail="Событие не найдено")
        
        return {"success": True, "message": "Событие удалено"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Ошибка при удалении события")