from sqlalchemy.orm import Mapped, mapped_column
from database import Model




class AdminOrm(Model):
    __tablename__ = "admins"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    max_user_id: Mapped[str] = mapped_column(nullable=False, unique=True)