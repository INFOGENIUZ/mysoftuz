from datetime import datetime, timezone
from sqlalchemy import BigInteger, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base


class Favorite(Base):
    """
    SQLAlchemy model representing a user's favorited program.
    """
    __tablename__ = "favorites"
    __table_args__ = (
        UniqueConstraint("user_id", "program_id", name="uq_user_program_favorite"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    program_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("programs.id", ondelete="CASCADE"), nullable=False, index=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    user = relationship("User", backref="favorites")
    program = relationship("Program", backref="favorites")

    def __repr__(self) -> str:
        return f"<Favorite user_id={self.user_id} program_id={self.program_id}>"
