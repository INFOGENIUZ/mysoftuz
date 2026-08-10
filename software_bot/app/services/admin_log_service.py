import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models import AdminLog

logger = logging.getLogger(__name__)


class AdminLogService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def log_action(
        self,
        admin_id: int,
        action: str,
        entity_type: Optional[str] = None,
        entity_id: Optional[int] = None,
        details: Optional[str] = None
    ) -> AdminLog:
        """Records an administrative audit log into database."""
        log_entry = AdminLog(
            admin_id=admin_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details
        )
        self.session.add(log_entry)
        await self.session.commit()
        await self.session.refresh(log_entry)
        logger.info(f"AuditLog: Admin {admin_id} executed action '{action}' on {entity_type}:{entity_id}")
        return log_entry
