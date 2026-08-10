from aiogram.fsm.state import StatesGroup, State


class UserSearchState(StatesGroup):
    """FSM states for user program search flow."""
    waiting_for_query = State()


SearchStates = UserSearchState

