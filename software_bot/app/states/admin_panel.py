from aiogram.fsm.state import StatesGroup, State


class AdminUserSearchStates(StatesGroup):
    """FSM state for Admin user search."""
    waiting_for_query = State()


class AdminSettingsEditState(StatesGroup):
    """FSM state for Admin settings field editing."""
    waiting_for_value = State()


class AdminBroadcastState(StatesGroup):
    """FSM states for Admin Broadcast creation flow."""
    waiting_for_message = State()
    waiting_for_confirm = State()


class AdminVersionStates(StatesGroup):
    """FSM states for Admin Program Version creation flow."""
    waiting_for_version = State()
    waiting_for_release_notes = State()
    waiting_for_official_url = State()
    waiting_for_file = State()


class AdminAnalyticsStates(StatesGroup):
    """FSM states for Admin Analytics Custom Date range input."""
    waiting_for_start_date = State()
    waiting_for_end_date = State()
