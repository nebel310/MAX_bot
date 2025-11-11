from fastapi import APIRouter, HTTPException, Depends, Query
from repositories.admin import AdminRepository
from repositories.admin_application import AdminApplicationRepository
from repositories.event import EventRepository
from repositories.application import ApplicationRepository
from schemas.admin import SAdminCreate, SAdmin, SUserWithRole
from schemas.event import SEventListResponse, SEventWithTags
from schemas.application import SParticipationConfirm
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


@router.get("/events/{event_id}/approved-volunteers")
async def get_approved_volunteers(
    event_id: int,
    current_admin: UserOrm = Depends(get_current_admin)
):
    """Получить список подтвержденных волонтеров для события"""
    try:
        approved_applications = await ApplicationRepository.get_approved_applications_for_event(event_id, current_admin.id)
        
        volunteers = []
        for app_data in approved_applications:
            volunteers.append({
                "user_id": app_data["application"].user_id,
                "username": app_data["username"],
                "application_id": app_data["application"].id,
                "current_rating": app_data["current_rating"],
                "current_participation_count": app_data["current_participation_count"],
                "applied_at": app_data["application"].applied_at
            })
        
        return {
            "event_id": event_id,
            "volunteers": volunteers,
            "total_count": len(volunteers)
        }
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Ошибка при получении списка волонтеров")


@router.post("/events/{event_id}/confirm-participation")
async def confirm_participation(
    event_id: int,
    participation_data: SParticipationConfirm,
    current_admin: UserOrm = Depends(get_current_admin)
):
    """Подтвердить участие волонтеров в событии и начислить рейтинг"""
    try:
        if not participation_data.user_ids:
            raise HTTPException(status_code=400, detail="Список пользователей не может быть пустым")
        
        updated_users = await ApplicationRepository.confirm_participation(
            event_id, 
            participation_data.user_ids, 
            participation_data.rating_points,
            current_admin.id
        )
        
        return {
            "success": True,
            "message": f"Участие подтверждено для {len(updated_users)} волонтеров",
            "updated_users": updated_users,
            "rating_points_added": participation_data.rating_points
        }
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Ошибка при подтверждении участия")


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