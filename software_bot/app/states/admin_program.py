from aiogram.fsm.state import StatesGroup, State


class AdminProgramCreateState(StatesGroup):
    """FSM states for Admin Program creation flow."""
    waiting_for_name = State()
    waiting_for_short_description = State()
    waiting_for_description = State()
    waiting_for_version = State()
    waiting_for_architecture = State()
    waiting_for_system_requirements = State()
    waiting_for_official_url = State()
    waiting_for_image = State()
    waiting_for_file = State()
    waiting_for_confirm = State()


class AdminProgramEditState(StatesGroup):
    """FSM states for Admin Program editing flow."""
    waiting_for_field_select = State()
    waiting_for_new_value = State()
    waiting_for_category_select = State()
