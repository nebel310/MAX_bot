from pydantic import BaseModel, ConfigDict




class SCity(BaseModel):
    id: int
    name: str
    
    model_config = ConfigDict(from_attributes=True)


class SCityCreate(BaseModel):
    name: str