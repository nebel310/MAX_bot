from database import new_session
from models.fund import FundOrm, FundTagOrm, DonationOrm
from models.auth import UserOrm
from models.user_profile import UserProfileOrm
from models.tag import TagOrm
from schemas.fund import SFundCreate, SFundUpdate, SDonationCreate
from sqlalchemy import select, delete, update, and_, func
from sqlalchemy.exc import IntegrityError




class FundRepository:
    @classmethod
    async def create_fund(cls, fund_data: SFundCreate, user_id: int):
        """Создать новый фонд"""
        async with new_session() as session:
            fund = FundOrm(
                title=fund_data.title,
                description=fund_data.description,
                requisites=fund_data.requisites,
                target_amount=fund_data.target_amount,
                rating_per_100=fund_data.rating_per_100,
                created_by=user_id,
                end_date=fund_data.end_date
            )
            session.add(fund)
            await session.flush()
            
            for tag_id in fund_data.tag_ids:
                fund_tag = FundTagOrm(
                    fund_id=fund.id,
                    tag_id=tag_id
                )
                session.add(fund_tag)
            
            await session.commit()
            await session.refresh(fund)
            return fund
    
    
    @classmethod
    async def get_fund_by_id(cls, fund_id: int):
        """Получить фонд по ID"""
        async with new_session() as session:
            query = select(FundOrm).where(FundOrm.id == fund_id)
            result = await session.execute(query)
            return result.scalars().first()
    
    
    @classmethod
    async def get_fund_with_details(cls, fund_id: int):
        """Получить фонд с деталями (теги, имя создателя)"""
        async with new_session() as session:
            fund_query = select(FundOrm).where(FundOrm.id == fund_id)
            fund_result = await session.execute(fund_query)
            fund = fund_result.scalars().first()
            
            if not fund:
                return None
            
            creator_query = select(UserOrm.username).where(UserOrm.id == fund.created_by)
            creator_result = await session.execute(creator_query)
            creator_username = creator_result.scalar()
            
            tags = await cls.get_fund_tags(fund_id)
            
            return {
                "fund": fund,
                "creator_username": creator_username,
                "tags": tags
            }
    
    
    @classmethod
    async def update_fund(cls, fund_id: int, fund_data: SFundUpdate):
        """Обновить фонд"""
        async with new_session() as session:
            update_data = {}
            if fund_data.title is not None:
                update_data["title"] = fund_data.title
            if fund_data.description is not None:
                update_data["description"] = fund_data.description
            if fund_data.requisites is not None:
                update_data["requisites"] = fund_data.requisites
            if fund_data.target_amount is not None:
                update_data["target_amount"] = fund_data.target_amount
            if fund_data.collected_amount is not None:
                update_data["collected_amount"] = fund_data.collected_amount
            if fund_data.rating_per_100 is not None:
                update_data["rating_per_100"] = fund_data.rating_per_100
            if fund_data.end_date is not None:
                update_data["end_date"] = fund_data.end_date
            if fund_data.status is not None:
                update_data["status"] = fund_data.status
            
            if update_data:
                stmt = (
                    update(FundOrm)
                    .where(FundOrm.id == fund_id)
                    .values(**update_data)
                )
                await session.execute(stmt)
            
            if fund_data.tag_ids is not None:
                delete_query = delete(FundTagOrm).where(FundTagOrm.fund_id == fund_id)
                await session.execute(delete_query)
                
                for tag_id in fund_data.tag_ids:
                    fund_tag = FundTagOrm(
                        fund_id=fund_id,
                        tag_id=tag_id
                    )
                    session.add(fund_tag)
            
            await session.commit()
            return await cls.get_fund_by_id(fund_id)
    
    
    @classmethod
    async def delete_fund(cls, fund_id: int):
        """Удалить фонд"""
        async with new_session() as session:
            delete_tags_query = delete(FundTagOrm).where(FundTagOrm.fund_id == fund_id)
            await session.execute(delete_tags_query)
            
            delete_donations_query = delete(DonationOrm).where(DonationOrm.fund_id == fund_id)
            await session.execute(delete_donations_query)
            
            delete_fund_query = delete(FundOrm).where(FundOrm.id == fund_id)
            result = await session.execute(delete_fund_query)
            await session.commit()
            
            return result.rowcount > 0
    
    
    @classmethod
    async def get_fund_tags(cls, fund_id: int):
        """Получить теги фонда"""
        async with new_session() as session:
            query = (
                select(TagOrm.name)
                .select_from(FundTagOrm)
                .join(TagOrm, FundTagOrm.tag_id == TagOrm.id)
                .where(FundTagOrm.fund_id == fund_id)
            )
            result = await session.execute(query)
            return result.scalars().all()
    
    
    @classmethod
    async def get_active_funds_feed(cls, user_id: int, page: int, page_size: int):
        """Получить ленту активных фондов с пагинацией"""
        async with new_session() as session:
            base_query = (
                select(FundOrm, UserOrm.username)
                .join(UserOrm, FundOrm.created_by == UserOrm.id)
                .where(FundOrm.status == "active")
            )
            
            count_query = select(func.count()).select_from(FundOrm).where(FundOrm.status == "active")
            total_count_result = await session.execute(count_query)
            total_count = total_count_result.scalar()
            
            offset = (page - 1) * page_size
            funds_query = base_query.offset(offset).limit(page_size)
            funds_result = await session.execute(funds_query)
            funds_data = funds_result.all()
            
            funds_with_details = []
            for fund, creator_username in funds_data:
                tags = await cls.get_fund_tags(fund.id)
                funds_with_details.append({
                    "fund": fund,
                    "creator_username": creator_username,
                    "tags": tags
                })
            
            return funds_with_details, total_count
    
    
    @classmethod
    async def get_user_funds(cls, user_id: int, page: int, page_size: int):
        """Получить фонды созданные пользователем"""
        async with new_session() as session:
            base_query = (
                select(FundOrm, UserOrm.username)
                .join(UserOrm, FundOrm.created_by == UserOrm.id)
                .where(FundOrm.created_by == user_id)
            )
            
            count_query = select(func.count()).select_from(FundOrm).where(FundOrm.created_by == user_id)
            total_count_result = await session.execute(count_query)
            total_count = total_count_result.scalar()
            
            offset = (page - 1) * page_size
            funds_query = base_query.offset(offset).limit(page_size)
            funds_result = await session.execute(funds_query)
            funds_data = funds_result.all()
            
            funds_with_details = []
            for fund, creator_username in funds_data:
                tags = await cls.get_fund_tags(fund.id)
                funds_with_details.append({
                    "fund": fund,
                    "creator_username": creator_username,
                    "tags": tags
                })
            
            return funds_with_details, total_count
    
    
    @classmethod
    async def is_fund_owner(cls, fund_id: int, user_id: int):
        """Проверить, является ли пользователь создателем фонда"""
        async with new_session() as session:
            query = select(FundOrm).where(
                and_(FundOrm.id == fund_id, FundOrm.created_by == user_id)
            )
            result = await session.execute(query)
            return result.scalars().first() is not None
    
    
    @classmethod
    async def make_donation(cls, donation_data: SDonationCreate, user_id: int):
        """Сделать донат в фонд"""
        async with new_session() as session:
            fund_query = select(FundOrm).where(FundOrm.id == donation_data.fund_id)
            fund_result = await session.execute(fund_query)
            fund = fund_result.scalars().first()
            
            if not fund:
                raise ValueError("Фонд не найден")
            
            if fund.status != "active":
                raise ValueError("Фонд закрыт для донатов")
            
            remaining_amount = fund.target_amount - fund.collected_amount
            if donation_data.amount > remaining_amount:
                raise ValueError(f"Сумма доната превышает оставшуюся сумму для сбора. Максимум: {remaining_amount} руб.")
            
            rating_earned = (donation_data.amount // 100) * fund.rating_per_100
            
            donation = DonationOrm(
                user_id=user_id,
                fund_id=donation_data.fund_id,
                amount=donation_data.amount,
                rating_earned=rating_earned
            )
            session.add(donation)
            
            fund.collected_amount += donation_data.amount
            
            if fund.collected_amount >= fund.target_amount:
                fund.status = "completed"
            
            user_profile_query = select(UserProfileOrm).where(UserProfileOrm.user_id == user_id)
            user_profile_result = await session.execute(user_profile_query)
            user_profile = user_profile_result.scalars().first()
            
            if user_profile:
                user_profile.rating += rating_earned
            else:
                user_profile = UserProfileOrm(
                    user_id=user_id,
                    rating=rating_earned,
                    participation_count=0
                )
                session.add(user_profile)
            
            await session.commit()
            await session.refresh(donation)
            return donation
    
    
    @classmethod
    async def get_user_donations(cls, user_id: int, page: int, page_size: int):
        """Получить донаты пользователя с пагинацией"""
        async with new_session() as session:
            base_query = (
                select(DonationOrm, FundOrm.title, FundOrm.status)
                .join(FundOrm, DonationOrm.fund_id == FundOrm.id)
                .where(DonationOrm.user_id == user_id)
            )
            
            count_query = select(func.count()).select_from(DonationOrm).where(DonationOrm.user_id == user_id)
            total_count_result = await session.execute(count_query)
            total_count = total_count_result.scalar()
            
            offset = (page - 1) * page_size
            donations_query = base_query.offset(offset).limit(page_size)
            donations_result = await session.execute(donations_query)
            donations_data = donations_result.all()
            
            donations = []
            for donation, fund_title, fund_status in donations_data:
                donations.append({
                    "donation": donation,
                    "fund_title": fund_title,
                    "fund_status": fund_status
                })
            
            return donations, total_count