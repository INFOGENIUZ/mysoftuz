from dataclasses import dataclass
from typing import Optional
from datetime import datetime

# Re-export ORM models from software_bot package
from software_bot.app.database.models import (
    User,
    Admin,
    Category,
    Program,
    Download,
    BotSetting,
    AdminLog,
    Favorite,
    RecentlyViewed,
    ProgramRating,
    ProgramReview,
    ReviewReport,
    ProgramKeyword,
    SearchEvent,
    ProgramVersion,
    ProgramSubscription,
    UserNotificationSetting,
    ProgramUpdateEvent,
    NotificationJob,
    UserNotification,
    PremiumPlan,
    Subscription,
    Order,
    ProgramEntitlement,
    PromoCode,
    PromoUsage,
    RevenueEvent,
)


@dataclass
class UserDTO:
    id: int
    telegram_id: int
    full_name: str
    username: Optional[str]
    created_at: datetime


__all__ = [
    "User",
    "Admin",
    "Category",
    "Program",
    "Download",
    "BotSetting",
    "AdminLog",
    "Favorite",
    "RecentlyViewed",
    "ProgramRating",
    "ProgramReview",
    "ReviewReport",
    "ProgramKeyword",
    "SearchEvent",
    "ProgramVersion",
    "ProgramSubscription",
    "UserNotificationSetting",
    "ProgramUpdateEvent",
    "NotificationJob",
    "UserNotification",
    "PremiumPlan",
    "Subscription",
    "Order",
    "ProgramEntitlement",
    "PromoCode",
    "PromoUsage",
    "RevenueEvent",
    "UserDTO",
]
