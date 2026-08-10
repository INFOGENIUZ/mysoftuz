import logging
from typing import Optional, Dict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models import BotSetting

logger = logging.getLogger(__name__)

# Global in-memory cache for fast lookups
_SETTINGS_CACHE: Dict[str, str] = {}
_CACHE_INITIALIZED: bool = False


class SettingsService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def _populate_cache_if_needed(self):
        global _CACHE_INITIALIZED, _SETTINGS_CACHE
        if not _CACHE_INITIALIZED:
            stmt = select(BotSetting)
            res = await self.session.execute(stmt)
            settings = res.scalars().all()
            _SETTINGS_CACHE = {s.key: s.value for s in settings}
            _CACHE_INITIALIZED = True

    async def get_setting(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Fetch setting value with in-memory caching."""
        await self._populate_cache_if_needed()
        if key in _SETTINGS_CACHE:
            return _SETTINGS_CACHE[key]

        stmt = select(BotSetting).where(BotSetting.key == key)
        res = await self.session.execute(stmt)
        setting = res.scalar_one_or_none()
        if setting:
            _SETTINGS_CACHE[key] = setting.value
            return setting.value
        return default

    async def set_setting(self, key: str, value: str, description: Optional[str] = None) -> BotSetting:
        """Sets/updates a setting in database and invalidates in-memory cache."""
        global _SETTINGS_CACHE
        stmt = select(BotSetting).where(BotSetting.key == key)
        res = await self.session.execute(stmt)
        setting = res.scalar_one_or_none()

        if setting:
            setting.value = str(value)
            if description:
                setting.description = description
        else:
            setting = BotSetting(key=key, value=str(value), description=description)
            self.session.add(setting)

        await self.session.commit()
        await self.session.refresh(setting)

        # Update/Invalidate in-memory cache
        _SETTINGS_CACHE[key] = str(value)
        return setting

    async def get_bool_setting(self, key: str, default: bool = False) -> bool:
        """Fetch boolean setting value."""
        val = await self.get_setting(key)
        if val is None:
            return default
        return val.strip().lower() in ("true", "1", "yes", "on")

    async def get_int_setting(self, key: str, default: int = 0) -> int:
        """Fetch integer setting value."""
        val = await self.get_setting(key)
        if val is None:
            return default
        try:
            return int(val.strip())
        except ValueError:
            return default

    @staticmethod
    def invalidate_cache():
        """Clears global in-memory settings cache."""
        global _CACHE_INITIALIZED, _SETTINGS_CACHE
        _SETTINGS_CACHE.clear()
        _CACHE_INITIALIZED = False
