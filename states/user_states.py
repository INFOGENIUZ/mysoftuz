from aiogram.fsm.state import StatesGroup, State
from software_bot.app.states.user_panel import SearchStates, ReviewStates, RatingStates
from software_bot.app.states.admin_panel import (
    AdminUserSearchStates,
    AdminSettingsEditState,
    AdminBroadcastState,
    AdminVersionStates,
    AdminAnalyticsStates,
)


class UserStates(StatesGroup):
    """FSM States for regular users."""
    search_query = State()
    waiting_for_review = State()
    waiting_for_rating = State()


__all__ = [
    "UserStates",
    "SearchStates",
    "ReviewStates",
    "RatingStates",
    "AdminUserSearchStates",
    "AdminSettingsEditState",
    "AdminBroadcastState",
    "AdminVersionStates",
    "AdminAnalyticsStates",
]
