import re
from typing import Type, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


def slugify(text: str) -> str:
    """
    Converts string to a clean, URL-friendly slug.
    Transliterates common special characters and removes invalid symbols.
    """
    text = text.lower().strip()
    
    # Transliterate Uzbek / Cyrillic common chars
    char_map = {
        'o‘': 'o', 'o`': 'o', 'g‘': 'g', 'g`': 'g', 'sh': 'sh', 'ch': 'ch',
        'о': 'o', 'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e',
        'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
        'н': 'n', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u', 'ф': 'f',
        'х': 'h', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'shch', 'ъ': '', 'ы': 'y',
        'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya'
    }
    for k, v in char_map.items():
        text = text.replace(k, v)

    # Replace non-alphanumeric characters with hyphens
    text = re.sub(r'[^a-z0-9]+', '-', text)
    # Remove leading and trailing hyphens
    text = text.strip('-')
    return text or 'item'


async def generate_unique_slug(session: AsyncSession, model: Type[Any], name: str) -> str:
    """
    Generates a unique slug for a given model and name.
    If 'grafik-dizayn' exists, generates 'grafik-dizayn-2', etc.
    """
    base_slug = slugify(name)
    slug = base_slug
    counter = 1

    while True:
        stmt = select(model).where(model.slug == slug)
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()
        if not existing:
            return slug
        counter += 1
        slug = f"{base_slug}-{counter}"
