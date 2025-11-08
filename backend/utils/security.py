import os
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from repositories.auth import UserRepository




load_dotenv()

security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Получить текущего пользователя по токену сессии"""
    session_token = credentials.credentials
    
    user = await UserRepository.get_user_by_session_token(session_token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный или просроченный токен сессии",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user


async def get_session_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Получить токен сессии для использования в logout"""
    return credentials.credentials