import math
from dataclasses import dataclass
from typing import List, Tuple
from aiogram.types import InlineKeyboardButton


@dataclass
class Pagination:
    """Dataclass holding normalized pagination metrics."""
    page: int
    per_page: int
    total_items: int
    total_pages: int
    offset: int
    has_previous: bool
    has_next: bool


def get_pagination(total_items: int, page: int = 1, per_page: int = 10) -> Pagination:
    """
    Central helper that calculates total pages, validates page bounds,
    and returns a normalized Pagination object.
    - Clamps page < 1 to page = 1
    - Clamps page > total_pages to page = total_pages
    - Handles total_items == 0 gracefully
    """
    if per_page < 1:
        per_page = 10

    if total_items <= 0:
        return Pagination(
            page=1,
            per_page=per_page,
            total_items=0,
            total_pages=1,
            offset=0,
            has_previous=False,
            has_next=False
        )

    total_pages = math.ceil(total_items / per_page)
    if total_pages < 1:
        total_pages = 1

    # Bounds clamping
    if page < 1:
        page = 1
    elif page > total_pages:
        page = total_pages

    offset = (page - 1) * per_page

    return Pagination(
        page=page,
        per_page=per_page,
        total_items=total_items,
        total_pages=total_pages,
        offset=offset,
        has_previous=(page > 1),
        has_next=(page < total_pages)
    )


def build_pagination_keyboard_row(
    pagination: Pagination, callback_prefix: str
) -> List[InlineKeyboardButton]:
    """
    Generates a standard inline button row for pagination: [ ◀️ ] 2 / 5 [ ▶️ ]
    Uses callback_prefix formatted as '{prefix}:{page}' (e.g. 'categories:page').
    """
    if pagination.total_pages <= 1:
        return []

    row = []

    # Previous page button
    if pagination.has_previous:
        row.append(
            InlineKeyboardButton(text="◀️", callback_data=f"{callback_prefix}:{pagination.page - 1}")
        )
    else:
        row.append(
            InlineKeyboardButton(text="⏹", callback_data="ignore")
        )

    # Page indicator button
    row.append(
        InlineKeyboardButton(
            text=f"{pagination.page} / {pagination.total_pages}",
            callback_data="ignore"
        )
    )

    # Next page button
    if pagination.has_next:
        row.append(
            InlineKeyboardButton(text="▶️", callback_data=f"{callback_prefix}:{pagination.page + 1}")
        )
    else:
        row.append(
            InlineKeyboardButton(text="⏹", callback_data="ignore")
        )

    return row
