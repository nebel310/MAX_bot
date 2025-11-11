from database import new_session
from models.application import ApplicationOrm
from models.event import EventOrm, EventTagOrm
from models.auth import UserOrm
from models.user_profile import UserProfileOrm, UserInterestOrm
from models.tag import TagOrm
from sqlalchemy import select, func
from sqlalchemy.orm import aliased




class AdminApplicationRepository:
    @classmethod
    async def get_application_statistics(cls, admin_user_id: int):
        """Получить статистику по откликам для администратора"""
        async with new_session() as session:
            status_stats_query = (
                select(
                    ApplicationOrm.status,
                    func.count(ApplicationOrm.id).label("count")
                )
                .select_from(ApplicationOrm)
                .join(EventOrm, ApplicationOrm.event_id == EventOrm.id)
                .where(EventOrm.created_by == admin_user_id)
                .group_by(ApplicationOrm.status)
            )
            
            status_stats_result = await session.execute(status_stats_query)
            status_stats = status_stats_result.all()
            
            total_applications_query = (
                select(func.count(ApplicationOrm.id))
                .select_from(ApplicationOrm)
                .join(EventOrm, ApplicationOrm.event_id == EventOrm.id)
                .where(EventOrm.created_by == admin_user_id)
            )
            
            total_applications_result = await session.execute(total_applications_query)
            total_applications = total_applications_result.scalar()
            
            return {
                "status_stats": dict(status_stats),
                "total_applications": total_applications
            }