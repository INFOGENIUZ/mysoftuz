from aiogram.fsm.state import StatesGroup, State


class AdminCategoryCreateState(StatesGroup):
    """FSM states for Admin Category creation flow."""
    waiting_for_name = State()
    waiting_for_description = State()
    waiting_for_icon = State()
    waiting_for_image = State()
    waiting_for_sort_order = State()
    waiting_for_confirm = State()


class AdminCategoryEditState(StatesGroup):
    """FSM states for Admin Category field editing flow."""
    waiting_for_field_select = State()
    waiting_for_new_value = State()
