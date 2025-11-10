from fastapi import APIRouter, HTTPException, Depends, Query
from repositories.application import ApplicationRepository
from schemas.application import SApplicationCreate, SApplicationUpdate, SApplication, SApplicationWithEvent, SApplicationWithUser, SApplicationListResponse
from models.auth import UserOrm
from utils.security import get_current_user




router = APIRouter(
    prefix="/applications",
    tags=["Отклики"]
)


@router.post("/create", response_model=SApplication)
async def create_application(
    application_data: SApplicationCreate,
    current_user: UserOrm = Depends(get_current_user)
):
    """Создать отклик на событие"""
    try:
        application = await ApplicationRepository.create_application(application_data, current_user.id)
        return application
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Ошибка при создании отклика")


@router.get("/my-applications", response_model=SApplicationListResponse)
async def get_my_applications(
    page: int = Query(1, ge=1, description="Номер страницы"),
    page_size: int = Query(20, ge=1, le=100, description="Размер страницы"),
    current_user: UserOrm = Depends(get_current_user)
):
    """Получить мои отклики"""
    try:
        applications_with_details, total_count = await ApplicationRepository.get_user_applications(current_user.id, page, page_size)
        
        applications = []
        for app_data in applications_with_details:
            application_response = SApplicationWithEvent(
                id=app_data["application"].id,
                event_id=app_data["application"].event_id,
                status=app_data["application"].status,
                rejection_reason=app_data["application"].rejection_reason,
                user_id=app_data["application"].user_id,
                applied_at=app_data["application"].applied_at,
                event_title=app_data["event_title"],
                event_date=app_data["event_date"],
                event_address=app_data["event_address"],
                event_creator_username=app_data["event_creator_username"]
            )
            applications.append(application_response)
        
        total_pages = (total_count + page_size - 1) // page_size if page_size > 0 else 0
        
        return SApplicationListResponse(
            applications=applications,
            total_count=total_count,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail="Ошибка при получении откликов")


@router.get("/event/{event_id}", response_model=list[SApplicationWithUser])
async def get_event_applications(
    event_id: int,
    current_user: UserOrm = Depends(get_current_user)
):
    """Получить отклики на событие (только для создателя события)"""
    try:
        applications = await ApplicationRepository.get_event_applications(event_id, current_user.id)
        
        applications_with_user = []
        for application in applications:
            application_details = await ApplicationRepository.get_application_with_details(application.id, current_user.id)
            if application_details:
                application_response = SApplicationWithUser(
                    id=application_details["application"].id,
                    event_id=application_details["application"].event_id,
                    status=application_details["application"].status,
                    rejection_reason=application_details["application"].rejection_reason,
                    user_id=application_details["application"].user_id,
                    applied_at=application_details["application"].applied_at,
                    user_username=application_details["user_username"],
                    user_rating=application_details["user_rating"],
                    user_participation_count=application_details["user_participation_count"],
                    user_city_id=application_details["user_city_id"],
                    user_about_me=application_details["user_about_me"],
                    user_interests=application_details["user_interests"],
                    match_percentage=application_details["match_percentage"]
                )
                applications_with_user.append(application_response)
        
        return applications_with_user
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Ошибка при получении откликов")


@router.get("/{application_id}", response_model=SApplicationWithUser)
async def get_application_details(
    application_id: int,
    current_user: UserOrm = Depends(get_current_user)
):
    """Получить подробную информацию об отклике (только для создателя события)"""
    try:
        application_details = await ApplicationRepository.get_application_with_details(application_id, current_user.id)
        if not application_details:
            raise HTTPException(status_code=404, detail="Отклик не найден")
        
        application_response = SApplicationWithUser(
            id=application_details["application"].id,
            event_id=application_details["application"].event_id,
            status=application_details["application"].status,
            rejection_reason=application_details["application"].rejection_reason,
            user_id=application_details["application"].user_id,
            applied_at=application_details["application"].applied_at,
            user_username=application_details["user_username"],
            user_rating=application_details["user_rating"],
            user_participation_count=application_details["user_participation_count"],
            user_city_id=application_details["user_city_id"],
            user_about_me=application_details["user_about_me"],
            user_interests=application_details["user_interests"],
            match_percentage=application_details["match_percentage"]
        )
        
        return application_response
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Ошибка при получении отклика")


@router.put("/{application_id}/update", response_model=SApplication)
async def update_application(
    application_id: int,
    application_data: SApplicationUpdate,
    current_user: UserOrm = Depends(get_current_user)
):
    """Обновить отклик (только создатель события)"""
    try:
        application = await ApplicationRepository.update_application(application_id, application_data, current_user.id)
        return application
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Ошибка при обновлении отклика")


@router.delete("/{application_id}/delete")
async def delete_application(
    application_id: int,
    current_user: UserOrm = Depends(get_current_user)
):
    """Удалить отклик (только владелец отклика)"""
    try:
        success = await ApplicationRepository.delete_application(application_id, current_user.id)
        if not success:
            raise HTTPException(status_code=404, detail="Отклик не найден")
        
        return {"success": True, "message": "Отклик удален"}
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Ошибка при удалении отклика")