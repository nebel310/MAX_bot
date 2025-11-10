from repositories.user import UserProfileRepository
from repositories.event import EventRepository




async def calculate_tag_match_percentage(user_id: int, event_id: int) -> float:
    """Рассчитать процент совпадения тегов пользователя и события"""
    try:
        user_interests = await UserProfileRepository.get_user_interests(user_id)
        event_tags = await EventRepository.get_event_tags(event_id)
        
        if not user_interests or not event_tags:
            return 0.0
        
        user_interest_names = set(user_interests)
        event_tag_names = set(event_tags)
        
        common_tags = user_interest_names.intersection(event_tag_names)
        
        if not event_tag_names:
            return 0.0
        
        match_percentage = (len(common_tags) / len(event_tag_names)) * 100
        return round(match_percentage, 2)
    except Exception:
        return 0.0