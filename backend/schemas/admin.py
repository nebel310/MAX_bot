from pydantic import BaseModel, ConfigDict, Field




class SAdminBase(BaseModel):
    max_user_id: str = Field(description="MAX user ID администратора")


class SAdminCreate(SAdminBase):
    pass


class SAdmin(SAdminBase):
    id: int
    
    model_config = ConfigDict(from_attributes=True)


class SUserWithRole(BaseModel):
    id: int
    max_user_id: str
    username: str
    role: str = Field(description="Роль пользователя: user или admin")
    
    model_config = ConfigDict(from_attributes=True)