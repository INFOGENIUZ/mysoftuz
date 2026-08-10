from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import String, Text, Integer, Float, Boolean, ForeignKey, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base

if TYPE_CHECKING:
    from app.database.models.category import Category
    from app.database.models.download import Download


class Program(Base):
    __tablename__ = "programs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    short_description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    file_id: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    file_unique_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    file_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    file_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    mime_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    architecture: Mapped[Optional[str]] = mapped_column(String(50), default="x64", nullable=True)
    operating_system: Mapped[Optional[str]] = mapped_column(String(100), default="Windows 10/11", nullable=True)
    license_type: Mapped[Optional[str]] = mapped_column(String(50), default="Free", nullable=True)
    system_requirements: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    official_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    image_file_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    downloads_count: Mapped[int] = mapped_column(Integer, default=0, index=True, nullable=False)
    rating_average: Mapped[float] = mapped_column(Float, default=0.0, index=True, nullable=False)
    rating_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False, index=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    category: Mapped["Category"] = relationship("Category", back_populates="programs")
    downloads: Mapped[List["Download"]] = relationship("Download", back_populates="program", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Program id={self.id} name='{self.name}' rating={self.rating_average:.1f}>"
