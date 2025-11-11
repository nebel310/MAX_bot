from database import new_session
from models.admin import AdminOrm
from models.auth import UserOrm
from schemas.admin import SAdminCreate
from sqlalchemy import select, delete
from sqlalchemy.exc import IntegrityError




class AdminRepository:
    @classmethod
    async def is_user_admin(cls, max_user_id: str):
        """Проверить, является ли пользователь админом по max_user_id"""
        async with new_session() as session:
            query = select(AdminOrm).where(AdminOrm.max_user_id == max_user_id)
            result = await session.execute(query)
            return result.scalars().first() is not None
    
    
    @classmethod
    async def create_admin(cls, admin_data: SAdminCreate):
        """Создать администратора"""
        async with new_session() as session:
            admin = AdminOrm(max_user_id=admin_data.max_user_id)
            session.add(admin)
            try:
                await session.commit()
                await session.refresh(admin)
                return admin
            except IntegrityError:
                await session.rollback()
                raise ValueError("Пользователь уже является администратором")
    
    
    @classmethod
    async def delete_admin(cls, max_user_id: str):
        """Удалить администратора по max_user_id"""
        async with new_session() as session:
            query = delete(AdminOrm).where(AdminOrm.max_user_id == max_user_id)
            result = await session.execute(query)
            await session.commit()
            return result.rowcount > 0
    
    
    @classmethod
    async def get_all_admins(cls):
        """Получить всех администраторов"""
        async with new_session() as session:
            query = select(AdminOrm)
            result = await session.execute(query)
            return result.scalars().all()
    
    
    @classmethod
    async def get_user_with_role(cls, user: UserOrm):
        """Получить пользователя с указанием роли"""
        is_admin = await cls.is_user_admin(user.max_user_id)
        role = "admin" if is_admin else "user"
        
        return {
            "id": user.id,
            "max_user_id": user.max_user_id,
            "username": user.username,
            "role": role
        }