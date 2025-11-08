import uvicorn
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from database import create_tables, delete_tables
from router.auth import router as auth_router

from fastapi import APIRouter
from repositories.auth import UserRepository
from schemas.auth import SUserRegister




@asynccontextmanager
async def lifespan(app: FastAPI):
    await delete_tables()
    print('База очищена')
    await create_tables()
    print('База готова к работе')
    yield
    print('Выключение')


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="Your App",
        version="1.0.0",
        description="Base nebel's FastApi template with JWT Auth",
        routes=app.routes,
    )
    openapi_schema["components"]["securitySchemes"] = {
        "Bearer": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT"
        }
    }
    
    secured_paths = {
        #Авторизация
        "/auth/me": {"method": "get", "security": [{"Bearer": []}]},
        "/auth/logout": {"method": "post", "security": [{"Bearer": []}]},
    }
    
    for path, config in secured_paths.items():
        if path in openapi_schema["paths"]:
            openapi_schema["paths"][path][config["method"]]["security"] = config["security"]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app = FastAPI(lifespan=lifespan)
app.openapi = custom_openapi
app.include_router(auth_router)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5500"],  # Тут адрес фронтенда
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


init_router = APIRouter()

@init_router.post("/init-test-data")
async def init_test_data():
    test_users = [
        {
            "username": "string",
            "email": "user@example.com", 
            "password": "string",
            "password_confirm": "string"
        },
        {
            "username": "admin",
            "email": "admin@admin.com",
            "password": "admin",
            "password_confirm": "admin"
        }
    ]
    
    for user in test_users:
        # Преобразуем словарь в SUserRegister
        user_data = SUserRegister(**user)
        await UserRepository.register_user(user_data)
    
    return {"message": "Тестовые данные созданы"}

app.include_router(init_router)



#Раскоментить, когда будешь писать докер.
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        reload=True,
        port=3001,
        host="0.0.0.0"
    )