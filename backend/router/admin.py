from fastapi import APIRouter, HTTPException, Depends, Query
from repositories.admin import AdminRepository
from repositories.admin_application import AdminApplicationRepository
from repositories.event import EventRepository
from schemas.admin import SAdminCreate, SAdmin, SUserWithRole
from schemas.event import SEventListResponse, SEventWithTags
from models.auth import UserOrm
from utils.security import get_current_user
from utils.admin_security import get_current_admin, get_user_with_role




router = APIRouter(
    prefix="/admin",
    tags=["Администратор"]
)


@router.get("/check-role", response_model=SUserWithRole)
async def check_user_role(current_user_with_role: dict = Depends(get_user_with_role)):
    """Проверить роль текущего пользователя"""
    return current_user_with_role


@router.get("/applications/statistics")
async def get_applications_statistics(current_admin: UserOrm = Depends(get_current_admin)):
    """Получить статистику по откликам"""
    try:
        statistics = await AdminApplicationRepository.get_application_statistics(current_admin.id)
        return statistics
    except Exception as e:
        raise HTTPException(status_code=500, detail="Ошибка при получении статистики")


@router.get("/my-events", response_model=SEventListResponse)
async def get_admin_events(
    page: int = Query(1, ge=1, description="Номер страницы"),
    page_size: int = Query(20, ge=1, le=100, description="Размер страницы"),
    current_admin: UserOrm = Depends(get_current_admin)
):
    """Получить события администратора"""
    try:
        events_with_details, total_count = await EventRepository.get_user_events(
            current_admin.id, page, page_size
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


@router.post("/admins/create", response_model=SAdmin)
async def create_admin(
    admin_data: SAdminCreate,
    current_admin: UserOrm = Depends(get_current_admin)
):
    """Создать нового администратора"""
    try:
        admin = await AdminRepository.create_admin(admin_data)
        return admin
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Ошибка при создании администратора")


@router.delete("/admins/{max_user_id}/delete")
async def delete_admin(
    max_user_id: str,
    current_admin: UserOrm = Depends(get_current_admin)
):
    """Удалить администратора"""
    try:
        success = await AdminRepository.delete_admin(max_user_id)
        if not success:
            raise HTTPException(status_code=404, detail="Администратор не найден")
        
        return {"success": True, "message": "Администратор удален"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Ошибка при удалении администратора")


@router.get("/admins", response_model=list[SAdmin])
async def get_all_admins(current_admin: UserOrm = Depends(get_current_admin)):
    """Получить список всех администраторов"""
    try:
        admins = await AdminRepository.get_all_admins()
        return admins
    except Exception as e:
        raise HTTPException(status_code=500, detail="Ошибка при получении списка администраторов")