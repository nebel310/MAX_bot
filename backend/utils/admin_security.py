from fastapi import Depends, HTTPException, status
from repositories.admin import AdminRepository
from models.auth import UserOrm
from utils.security import get_current_user




async def get_current_admin(current_user: UserOrm = Depends(get_current_user)):
    """Получить текущего пользователя, если он является администратором"""
    is_admin = await AdminRepository.is_user_admin(current_user.max_user_id)
    if not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав. Требуются права администратора"
        )
    return current_user


async def get_user_with_role(current_user: UserOrm = Depends(get_current_user)):
    """Получить пользователя с указанием роли"""
    return await AdminRepository.get_user_with_role(current_user)