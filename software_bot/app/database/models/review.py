from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import BigInteger, ForeignKey, DateTime, String, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base


class ProgramReview(Base):
    """
    SQLAlchemy model representing a user's written review for a program.
    Status values: 'PENDING', 'APPROVED', 'REJECTED'
    """
    __tablename__ = "program_reviews"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    program_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("programs.id", ondelete="CASCADE"), nullable=False, index=True)
    rating_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("program_ratings.id", ondelete="SET NULL"), nullable=True)

    text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="PENDING", nullable=False, index=True)
    is_visible: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

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
    user = relationship("User", backref="program_reviews")
    program = relationship("Program", backref="program_reviews")
    rating_obj = relationship("ProgramRating")

    def __repr__(self) -> str:
        return f"<ProgramReview id={self.id} user_id={self.user_id} program_id={self.program_id} status='{self.status}'>"


class ReviewReport(Base):
    """
    SQLAlchemy model representing a user report against an inappropriate review.
    """
    __tablename__ = "review_reports"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    review_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("program_reviews.id", ondelete="CASCADE"), nullable=False, index=True)
    reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    user = relationship("User")
    review = relationship("ProgramReview", backref="reports")
