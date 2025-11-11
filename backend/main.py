import uvicorn
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from database import create_tables, delete_tables
from router.auth import router as auth_router
from router.city import router as city_router
from router.tag import router as tag_router
from router.user import router as user_router
from router.event import router as event_router
from router.application import router as application_router
from router.admin import router as admin_router
from init_test_data import init_all_test_data




@asynccontextmanager
async def lifespan(app: FastAPI):
    await delete_tables()
    print('База очищена')
    await create_tables()
    print('База готова к работе')
    await init_all_test_data()
    yield
    print('Выключение')


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="MAX Bot API",
        version="1.0.0",
        description="Backend for MAX Bot - volunteer management system",
        routes=app.routes,
    )
    openapi_schema["components"]["securitySchemes"] = {
        "Bearer": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT"
        }
    }
    
    secured_paths = [
        {"path": "/auth/me", "method": "get", "security": [{"Bearer": []}]},
        {"path": "/auth/logout", "method": "post", "security": [{"Bearer": []}]},
        {"path": "/user/profile", "method": "get", "security": [{"Bearer": []}]},
        {"path": "/user/profile/update", "method": "put", "security": [{"Bearer": []}]},
        {"path": "/user/profile/update", "method": "patch", "security": [{"Bearer": []}]},
        {"path": "/user/profile/full-update", "method": "patch", "security": [{"Bearer": []}]},
        {"path": "/user/interests", "method": "post", "security": [{"Bearer": []}]},
        {"path": "/user/leaderboard", "method": "get", "security": [{"Bearer": []}]},
        {"path": "/user/my-applications", "method": "get", "security": [{"Bearer": []}]},
        {"path": "/events/create", "method": "post", "security": [{"Bearer": []}]},
        {"path": "/events/feed", "method": "get", "security": [{"Bearer": []}]},
        {"path": "/events/my-events", "method": "get", "security": [{"Bearer": []}]},
        {"path": "/events/{event_id}", "method": "get", "security": [{"Bearer": []}]},
        {"path": "/events/{event_id}/update", "method": "put", "security": [{"Bearer": []}]},
        {"path": "/events/{event_id}/delete", "method": "delete", "security": [{"Bearer": []}]},
        {"path": "/applications/create", "method": "post", "security": [{"Bearer": []}]},
        {"path": "/applications/my-applications", "method": "get", "security": [{"Bearer": []}]},
        {"path": "/applications/event/{event_id}", "method": "get", "security": [{"Bearer": []}]},
        {"path": "/applications/{application_id}", "method": "get", "security": [{"Bearer": []}]},
        {"path": "/applications/{application_id}/update", "method": "put", "security": [{"Bearer": []}]},
        {"path": "/applications/{application_id}/delete", "method": "delete", "security": [{"Bearer": []}]},
        {"path": "/admin/applications/statistics", "method": "get", "security": [{"Bearer": []}]},
        {"path": "/admin/my-events", "method": "get", "security": [{"Bearer": []}]},
        {"path": "/admin/events/{event_id}/approved-volunteers", "method": "get", "security": [{"Bearer": []}]},
        {"path": "/admin/events/{event_id}/confirm-participation", "method": "post", "security": [{"Bearer": []}]},
        {"path": "/admin/admins/create", "method": "post", "security": [{"Bearer": []}]},
        {"path": "/admin/admins/{max_user_id}/delete", "method": "delete", "security": [{"Bearer": []}]},
        {"path": "/admin/admins", "method": "get", "security": [{"Bearer": []}]},
        {"path": "/admin/check-role", "method": "get", "security": [{"Bearer": []}]},
    ]
    
    for item in secured_paths:
        path = item["path"]
        method = item["method"]
        security = item["security"]
        
        if path in openapi_schema["paths"] and method in openapi_schema["paths"][path]:
            openapi_schema["paths"][path][method]["security"] = security
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app = FastAPI(lifespan=lifespan)
app.openapi = custom_openapi

app.include_router(auth_router)
app.include_router(city_router)
app.include_router(tag_router)
app.include_router(user_router)
app.include_router(event_router)
app.include_router(application_router)
app.include_router(admin_router)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5500"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        reload=True,
        port=3001,
        host="0.0.0.0"
    )