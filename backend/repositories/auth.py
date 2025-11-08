import os
import secrets
from dotenv import load_dotenv
from database import new_session
from models.auth import UserOrm, UserSessionOrm
from schemas.auth import SUserAuth
from sqlalchemy import select, delete
from datetime import datetime, timezone, timedelta




load_dotenv()

SESSION_EXPIRE_DAYS = int(os.getenv('SESSION_EXPIRE_DAYS', 30))

class UserRepository:
    @classmethod
    async def get_or_create_user(cls, max_user_id: str, username: str):
        """Создать или получить пользователя по max_user_id"""
        async with new_session() as session:
            query = select(UserOrm).where(UserOrm.max_user_id == max_user_id)
            result = await session.execute(query)
            user = result.scalars().first()
            
            if not user:
                user = UserOrm(
                    max_user_id=max_user_id,
                    username=username
                )
                session.add(user)
                await session.commit()
                await session.refresh(user)
            
            return user
    
    
    @classmethod
    async def get_user_by_id(cls, user_id: int):
        """Получить пользователя по ID"""
        async with new_session() as session:
            query = select(UserOrm).where(UserOrm.id == user_id)
            result = await session.execute(query)
            return result.scalars().first()
    
    
    @classmethod
    async def get_user_by_session_token(cls, session_token: str):
        """Получить пользователя по токену сессии"""
        async with new_session() as session:
            query = select(UserSessionOrm).where(UserSessionOrm.session_token == session_token)
            result = await session.execute(query)
            session_obj = result.scalars().first()
            
            if not session_obj or session_obj.expires_at < datetime.now(timezone.utc):
                return None
            
            return await cls.get_user_by_id(session_obj.user_id)
    
    
    @classmethod
    async def create_user_session(cls, user_id: int):
        """Создать сессию для пользователя"""
        async with new_session() as session:
            session_token = secrets.token_urlsafe(32)
            expires_at = datetime.now(timezone.utc) + timedelta(days=SESSION_EXPIRE_DAYS)
            
            session_obj = UserSessionOrm(
                user_id=user_id,
                session_token=session_token,
                expires_at=expires_at
            )
            session.add(session_obj)
            await session.commit()
            return session_token
    
    
    @classmethod
    async def delete_user_session(cls, session_token: str):
        """Удалить сессию пользователя"""
        async with new_session() as session:
            query = delete(UserSessionOrm).where(UserSessionOrm.session_token == session_token)
            await session.execute(query)
            await session.commit()