from datetime import datetime, timezone
from sqlalchemy import BigInteger, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base


class RecentlyViewed(Base):
    """
    SQLAlchemy model representing a user's recently viewed program history.
    """
    __tablename__ = "recently_viewed"
    __table_args__ = (
        UniqueConstraint("user_id", "program_id", name="uq_user_program_recent"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    program_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("programs.id", ondelete="CASCADE"), nullable=False, index=True)

    viewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )

    # Relationships
    user = relationship("User", backref="recently_viewed")
    program = relationship("Program", backref="recently_viewed")

    def __repr__(self) -> str:
        return f"<RecentlyViewed user_id={self.user_id} program_id={self.program_id} viewed_at={self.viewed_at}>"
