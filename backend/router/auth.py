from fastapi import APIRouter, HTTPException, Depends
from schemas.auth import SUserAuth, SUserSession, SUser
from schemas.admin import SUserWithRole
from repositories.auth import UserRepository
from repositories.admin import AdminRepository
from models.auth import UserOrm
from utils.security import get_current_user, get_session_token




router = APIRouter(
    prefix="/auth",
    tags=["Аутентификация"]
)


@router.post("/login", response_model=SUserSession)
async def login_user(auth_data: SUserAuth):
    """Вход пользователя через MAX user_id"""
    try:
        user = await UserRepository.get_or_create_user(auth_data.max_user_id, auth_data.username)
        session_token = await UserRepository.create_user_session(user.id)
        
        return SUserSession(
            session_token=session_token,
            user=user
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail="Ошибка при входе в систему")


@router.post("/logout")
async def logout(session_token: str = Depends(get_session_token)):
    """Выход пользователя"""
    try:
        await UserRepository.delete_user_session(session_token)
        return {"success": True, "message": "Вы вышли из системы"}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Ошибка при выходе из системы")


@router.get("/me", response_model=SUserWithRole)
async def get_current_user_info(current_user: UserOrm = Depends(get_current_user)):
    """Получить информацию о текущем пользователе с указанием роли"""
    return await AdminRepository.get_user_with_role(current_user)