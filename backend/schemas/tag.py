from pydantic import BaseModel, ConfigDict




class STag(BaseModel):
    id: int
    name: str
    
    model_config = ConfigDict(from_attributes=True)


class STagCreate(BaseModel):
    name: str