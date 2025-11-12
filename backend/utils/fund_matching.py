from repositories.user import UserProfileRepository
from repositories.fund import FundRepository




async def calculate_fund_tag_match_percentage(user_id: int, fund_id: int) -> float:
    """Рассчитать процент совпадения тегов пользователя и фонда"""
    try:
        user_interests = await UserProfileRepository.get_user_interests(user_id)
        fund_tags = await FundRepository.get_fund_tags(fund_id)
        
        if not user_interests or not fund_tags:
            return 0.0
        
        user_interest_names = set(user_interests)
        fund_tag_names = set(fund_tags)
        
        common_tags = user_interest_names.intersection(fund_tag_names)
        
        if not fund_tag_names:
            return 0.0
        
        match_percentage = (len(common_tags) / len(fund_tag_names)) * 100
        return round(match_percentage, 2)
    except Exception:
        return 0.0