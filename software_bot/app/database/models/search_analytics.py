from datetime import datetime, timezone
from sqlalchemy import String, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.database.base import Base


class SearchEvent(Base):
    """
    SQLAlchemy model representing a search event for analytics (e.g. tracking zero-result queries).
    """
    __tablename__ = "search_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    query_normalized: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    result_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False, index=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )

    def __repr__(self) -> str:
        return f"<SearchEvent query='{self.query_normalized}' results={self.result_count}>"
