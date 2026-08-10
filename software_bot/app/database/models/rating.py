from datetime import datetime, timezone
from sqlalchemy import BigInteger, ForeignKey, DateTime, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base


class ProgramRating(Base):
    """
    SQLAlchemy model representing a user's star rating (1 to 5) for a program.
    """
    __tablename__ = "program_ratings"
    __table_args__ = (
        UniqueConstraint("user_id", "program_id", name="uq_user_program_rating"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    program_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("programs.id", ondelete="CASCADE"), nullable=False, index=True)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    user = relationship("User", backref="program_ratings")
    program = relationship("Program", backref="program_ratings")

    def __repr__(self) -> str:
        return f"<ProgramRating user_id={self.user_id} program_id={self.program_id} rating={self.rating}>"
