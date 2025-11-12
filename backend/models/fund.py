from datetime import datetime
from sqlalchemy import DateTime
from sqlalchemy.orm import Mapped, mapped_column
from database import Model




class FundOrm(Model):
    __tablename__ = "funds"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(nullable=False)
    description: Mapped[str] = mapped_column(nullable=False)
    requisites: Mapped[str] = mapped_column(nullable=False)
    target_amount: Mapped[int] = mapped_column(nullable=False)  # надо накопить
    collected_amount: Mapped[int] = mapped_column(default=0)  # накопили
    rating_per_100: Mapped[int] = mapped_column(nullable=False)  # рейтинг за 100 рублей
    created_by: Mapped[int] = mapped_column(nullable=False)  # ID админа-создателя
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now())
    end_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)  # дата конца (null = бессрочно)
    status: Mapped[str] = mapped_column(default="active")  # active, completed


class FundTagOrm(Model):
    __tablename__ = "fund_tags"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    fund_id: Mapped[int] = mapped_column(nullable=False)
    tag_id: Mapped[int] = mapped_column(nullable=False)


class DonationOrm(Model):
    __tablename__ = "donations"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(nullable=False)
    fund_id: Mapped[int] = mapped_column(nullable=False)
    amount: Mapped[int] = mapped_column(nullable=False)  # сумма доната
    rating_earned: Mapped[int] = mapped_column(nullable=False)  # полученный рейтинг
    donated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now())