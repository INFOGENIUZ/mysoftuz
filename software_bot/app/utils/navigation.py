import logging
from typing import Dict, Any, Optional
from aiogram.fsm.context import FSMContext

logger = logging.getLogger(__name__)


class NavigationContext:
    """Helper class to manage user navigation stack and return sources in FSM context."""

    @staticmethod
    async def save_nav_context(state: FSMContext, source: str, **kwargs) -> None:
        """
        Saves navigation source context into FSM data.
        Supported sources: 'category', 'search', 'popular', 'new', 'downloads', 'admin_category'
        """
        nav_data = {
            "source": source,
            **kwargs
        }
        await state.update_data(nav_context=nav_data)

    @staticmethod
    async def get_nav_context(state: FSMContext) -> Dict[str, Any]:
        """Fetches current navigation context dictionary from FSM data."""
        data = await state.get_data()
        return data.get("nav_context", {})

    @staticmethod
    async def clear_nav_context(state: FSMContext) -> None:
        """Clears navigation context from FSM data."""
        data = await state.get_data()
        if "nav_context" in data:
            data.pop("nav_context")
            await state.set_data(data)
