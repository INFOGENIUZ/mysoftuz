from aiogram.fsm.state import StatesGroup, State


class ReviewStates(StatesGroup):
    """FSM states for user program review creation."""
    waiting_for_text = State()
