from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import BigInteger, String, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.database.base import Base


class AdminLog(Base):
    """
    SQLAlchemy model representing an audit log entry for critical administrative actions.
    """
    __tablename__ = "admin_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    admin_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    entity_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    entity_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )

    def __repr__(self) -> str:
        return f"<AdminLog id={self.id} admin_id={self.admin_id} action='{self.action}'>"
