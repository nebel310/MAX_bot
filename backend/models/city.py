from sqlalchemy.orm import Mapped, mapped_column
from database import Model




class CityOrm(Model):
    __tablename__ = "cities"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True, nullable=False)