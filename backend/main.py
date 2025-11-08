import uvicorn
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from database import create_tables, delete_tables
from router.auth import router as auth_router
from router.city import router as city_router
from router.tag import router as tag_router




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
        {"path": "/user/interests", "method": "post", "security": [{"Bearer": []}]},
        {"path": "/user/my-applications", "method": "get", "security": [{"Bearer": []}]},
        {"path": "/user/leaderboard", "method": "get", "security": [{"Bearer": []}]},
        {"path": "/events/create", "method": "post", "security": [{"Bearer": []}]},
        {"path": "/events/my-events", "method": "get", "security": [{"Bearer": []}]},
        {"path": "/events/{event_id}/update", "method": "put", "security": [{"Bearer": []}]},
        {"path": "/events/{event_id}/delete", "method": "delete", "security": [{"Bearer": []}]},
        {"path": "/applications/create", "method": "post", "security": [{"Bearer": []}]},
        {"path": "/admin/applications", "method": "get", "security": [{"Bearer": []}]},
        {"path": "/admin/applications/{application_id}/update", "method": "put", "security": [{"Bearer": []}]},
        {"path": "/admin/admin-events", "method": "get", "security": [{"Bearer": []}]},
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