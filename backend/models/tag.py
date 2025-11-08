from sqlalchemy.orm import Mapped, mapped_column
from database import Model




class TagOrm(Model):
    __tablename__ = "tags"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True, nullable=False)