from sqlalchemy.orm import Mapped, mapped_column
from database import Model




class UserProfileOrm(Model):
    __tablename__ = "user_profiles"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(nullable=False, unique=True)
    city_id: Mapped[int] = mapped_column(nullable=True)
    about_me: Mapped[str] = mapped_column(nullable=True)
    rating: Mapped[int] = mapped_column(default=0)
    participation_count: Mapped[int] = mapped_column(default=0)


class UserInterestOrm(Model):
    __tablename__ = "user_interests"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(nullable=False)
    tag_id: Mapped[int] = mapped_column(nullable=False)