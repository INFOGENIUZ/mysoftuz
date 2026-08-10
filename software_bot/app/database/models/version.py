from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import BigInteger, ForeignKey, DateTime, String, Text, Boolean, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base


class ProgramVersion(Base):
    """
    SQLAlchemy model representing a specific version release of a program.
    """
    __tablename__ = "program_versions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    program_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("programs.id", ondelete="CASCADE"), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    file_id: Mapped[str] = mapped_column(String(255), nullable=False)
    file_unique_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    file_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    release_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    official_release_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    program = relationship("Program", backref="versions")

    def __repr__(self) -> str:
        return f"<ProgramVersion id={self.id} program_id={self.program_id} version='{self.version}' is_current={self.is_current}>"
