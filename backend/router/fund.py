from fastapi import APIRouter, HTTPException, Depends, Query
from repositories.fund import FundRepository
from repositories.user import UserProfileRepository
from schemas.fund import (
    SFundCreate, SFundUpdate, SFundWithTags, 
    SFundWithMatch, SFundFeedResponse, SFundListResponse,
    SDonationCreate, SDonation, SDonationWithFund
)
from models.auth import UserOrm
from utils.security import get_current_user
from utils.admin_security import get_current_admin
from utils.fund_matching import calculate_fund_tag_match_percentage




router = APIRouter(
    prefix="/funds",
    tags=["Фонды"]
)


@router.post("/create", response_model=SFundWithTags)
async def create_fund(
    fund_data: SFundCreate,
    current_admin: UserOrm = Depends(get_current_admin)
):
    """Создать новый фонд (только для админов)"""
    try:
        fund = await FundRepository.create_fund(fund_data, current_admin.id)
        
        fund_details = await FundRepository.get_fund_with_details(fund.id)
        if not fund_details:
            raise HTTPException(status_code=404, detail="Фонд не найден")
        
        fund_response = SFundWithTags(
            id=fund_details["fund"].id,
            title=fund_details["fund"].title,
            description=fund_details["fund"].description,
            requisites=fund_details["fund"].requisites,
            target_amount=fund_details["fund"].target_amount,
            collected_amount=fund_details["fund"].collected_amount,
            rating_per_100=fund_details["fund"].rating_per_100,
            created_by=fund_details["fund"].created_by,
            created_at=fund_details["fund"].created_at,
            end_date=fund_details["fund"].end_date,
            status=fund_details["fund"].status,
            creator_username=fund_details["creator_username"],
            tags=fund_details["tags"]
        )
        
        return fund_response
    except Exception as e:
        raise HTTPException(status_code=500, detail="Ошибка при создании фонда")


@router.get("/feed", response_model=SFundFeedResponse)
async def get_funds_feed(
    page: int = Query(1, ge=1, description="Номер страницы"),
    page_size: int = Query(20, ge=1, le=100, description="Размер страницы"),
    current_user: UserOrm = Depends(get_current_user)
):
    """Получить ленту активных фондов с пагинацией и процентом совпадения"""
    try:
        funds_with_details, total_count = await FundRepository.get_active_funds_feed(
            current_user.id, page, page_size
        )
        
        funds_with_match = []
        for fund_data in funds_with_details:
            match_percentage = await calculate_fund_tag_match_percentage(
                current_user.id, fund_data["fund"].id
            )
            
            fund_response = SFundWithMatch(
                id=fund_data["fund"].id,
                title=fund_data["fund"].title,
                description=fund_data["fund"].description,
                requisites=fund_data["fund"].requisites,
                target_amount=fund_data["fund"].target_amount,
                collected_amount=fund_data["fund"].collected_amount,
                rating_per_100=fund_data["fund"].rating_per_100,
                created_by=fund_data["fund"].created_by,
                created_at=fund_data["fund"].created_at,
                end_date=fund_data["fund"].end_date,
                status=fund_data["fund"].status,
                creator_username=fund_data["creator_username"],
                tags=fund_data["tags"],
                match_percentage=match_percentage
            )
            
            funds_with_match.append(fund_response)
        
        total_pages = (total_count + page_size - 1) // page_size if page_size > 0 else 0
        
        return SFundFeedResponse(
            funds=funds_with_match,
            total_count=total_count,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail="Ошибка при получении ленты фондов")


@router.get("/my-funds", response_model=SFundListResponse)
async def get_my_funds(
    page: int = Query(1, ge=1, description="Номер страницы"),
    page_size: int = Query(20, ge=1, le=100, description="Размер страницы"),
    current_admin: UserOrm = Depends(get_current_admin)
):
    """Получить фонды созданные текущим администратором"""
    try:
        funds_with_details, total_count = await FundRepository.get_user_funds(
            current_admin.id, page, page_size
        )
        
        funds_with_tags = []
        for fund_data in funds_with_details:
            fund_response = SFundWithTags(
                id=fund_data["fund"].id,
                title=fund_data["fund"].title,
                description=fund_data["fund"].description,
                requisites=fund_data["fund"].requisites,
                target_amount=fund_data["fund"].target_amount,
                collected_amount=fund_data["fund"].collected_amount,
                rating_per_100=fund_data["fund"].rating_per_100,
                created_by=fund_data["fund"].created_by,
                created_at=fund_data["fund"].created_at,
                end_date=fund_data["fund"].end_date,
                status=fund_data["fund"].status,
                creator_username=fund_data["creator_username"],
                tags=fund_data["tags"]
            )
            
            funds_with_tags.append(fund_response)
        
        total_pages = (total_count + page_size - 1) // page_size if page_size > 0 else 0
        
        return SFundListResponse(
            funds=funds_with_tags,
            total_count=total_count,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail="Ошибка при получении фондов")


@router.get("/my-donations", response_model=list[SDonationWithFund])
async def get_my_donations(
    page: int = Query(1, ge=1, description="Номер страницы"),
    page_size: int = Query(20, ge=1, le=100, description="Размер страницы"),
    current_user: UserOrm = Depends(get_current_user)
):
    """Получить мои донаты"""
    try:
        donations_with_details, total_count = await FundRepository.get_user_donations(current_user.id, page, page_size)
        
        donations = []
        for donation_data in donations_with_details:
            donation_response = SDonationWithFund(
                id=donation_data["donation"].id,
                fund_id=donation_data["donation"].fund_id,
                amount=donation_data["donation"].amount,
                user_id=donation_data["donation"].user_id,
                rating_earned=donation_data["donation"].rating_earned,
                donated_at=donation_data["donation"].donated_at,
                fund_title=donation_data["fund_title"],
                fund_status=donation_data["fund_status"]
            )
            donations.append(donation_response)
        
        return donations
    except Exception as e:
        raise HTTPException(status_code=500, detail="Ошибка при получении донатов")


@router.post("/donate", response_model=SDonationWithFund)
async def make_donation(
    donation_data: SDonationCreate,
    current_user: UserOrm = Depends(get_current_user)
):
    """Сделать донат в фонд"""
    try:
        donation = await FundRepository.make_donation(donation_data, current_user.id)
        
        fund_query = await FundRepository.get_fund_by_id(donation.fund_id)
        if not fund_query:
            raise HTTPException(status_code=404, detail="Фонд не найден")
        
        donation_response = SDonationWithFund(
            id=donation.id,
            fund_id=donation.fund_id,
            amount=donation.amount,
            user_id=donation.user_id,
            rating_earned=donation.rating_earned,
            donated_at=donation.donated_at,
            fund_title=fund_query.title,
            fund_status=fund_query.status
        )
        
        return donation_response
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Ошибка при выполнении доната")


@router.get("/{fund_id}", response_model=SFundWithMatch)
async def get_fund_details(
    fund_id: int,
    current_user: UserOrm = Depends(get_current_user)
):
    """Получить подробную информацию о фонде с процентом совпадения"""
    try:
        fund_details = await FundRepository.get_fund_with_details(fund_id)
        if not fund_details:
            raise HTTPException(status_code=404, detail="Фонд не найден")
        
        match_percentage = await calculate_fund_tag_match_percentage(current_user.id, fund_id)
        
        fund_response = SFundWithMatch(
            id=fund_details["fund"].id,
            title=fund_details["fund"].title,
            description=fund_details["fund"].description,
            requisites=fund_details["fund"].requisites,
            target_amount=fund_details["fund"].target_amount,
            collected_amount=fund_details["fund"].collected_amount,
            rating_per_100=fund_details["fund"].rating_per_100,
            created_by=fund_details["fund"].created_by,
            created_at=fund_details["fund"].created_at,
            end_date=fund_details["fund"].end_date,
            status=fund_details["fund"].status,
            creator_username=fund_details["creator_username"],
            tags=fund_details["tags"],
            match_percentage=match_percentage
        )
        
        return fund_response
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Ошибка при получении фонда")


@router.patch("/{fund_id}/update", response_model=SFundWithTags)
async def update_fund(
    fund_id: int,
    fund_data: SFundUpdate,
    current_admin: UserOrm = Depends(get_current_admin)
):
    """Обновить фонд (только создатель фонда)"""
    try:
        is_owner = await FundRepository.is_fund_owner(fund_id, current_admin.id)
        if not is_owner:
            raise HTTPException(status_code=403, detail="Недостаточно прав для редактирования фонда")
        
        fund = await FundRepository.update_fund(fund_id, fund_data)
        if not fund:
            raise HTTPException(status_code=404, detail="Фонд не найден")
        
        fund_details = await FundRepository.get_fund_with_details(fund_id)
        if not fund_details:
            raise HTTPException(status_code=404, detail="Фонд не найден")
        
        fund_response = SFundWithTags(
            id=fund_details["fund"].id,
            title=fund_details["fund"].title,
            description=fund_details["fund"].description,
            requisites=fund_details["fund"].requisites,
            target_amount=fund_details["fund"].target_amount,
            collected_amount=fund_details["fund"].collected_amount,
            rating_per_100=fund_details["fund"].rating_per_100,
            created_by=fund_details["fund"].created_by,
            created_at=fund_details["fund"].created_at,
            end_date=fund_details["fund"].end_date,
            status=fund_details["fund"].status,
            creator_username=fund_details["creator_username"],
            tags=fund_details["tags"]
        )
        
        return fund_response
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Ошибка при обновлении фонда")


@router.delete("/{fund_id}/delete")
async def delete_fund(
    fund_id: int,
    current_admin: UserOrm = Depends(get_current_admin)
):
    """Удалить фонд (только создатель фонда)"""
    try:
        is_owner = await FundRepository.is_fund_owner(fund_id, current_admin.id)
        if not is_owner:
            raise HTTPException(status_code=403, detail="Недостаточно прав для удаления фонда")
        
        success = await FundRepository.delete_fund(fund_id)
        if not success:
            raise HTTPException(status_code=404, detail="Фонд не найден")
        
        return {"success": True, "message": "Фонд удален"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Ошибка при удалении фонда")