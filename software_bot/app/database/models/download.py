from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import ForeignKey, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base

if TYPE_CHECKING:
    from app.database.models.user import User
    from app.database.models.program import Program


class Download(Base):
    __tablename__ = "downloads"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    program_id: Mapped[int] = mapped_column(
        ForeignKey("programs.id", ondelete="CASCADE"), index=True, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True, nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="downloads")
    program: Mapped["Program"] = relationship("Program", back_populates="downloads")

    def __repr__(self) -> str:
        return f"<Download id={self.id} user_id={self.user_id} program_id={self.program_id}>"
