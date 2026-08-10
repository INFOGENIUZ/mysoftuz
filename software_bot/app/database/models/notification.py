from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import BigInteger, ForeignKey, DateTime, String, Text, Boolean, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base


class ProgramSubscription(Base):
    """
    SQLAlchemy model representing a user's subscription to update notifications for a program.
    """
    __tablename__ = "program_subscriptions"
    __table_args__ = (
        UniqueConstraint("user_id", "program_id", name="uq_user_program_sub"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    program_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("programs.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    user = relationship("User", backref="program_subscriptions")
    program = relationship("Program", backref="subscriptions")


class UserNotificationSetting(Base):
    """
    SQLAlchemy model representing global notification settings for a user.
    """
    __tablename__ = "user_notification_settings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)

    software_updates: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    new_programs: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    important_announcements: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

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

    user = relationship("User", backref="notification_settings")


class ProgramUpdateEvent(Base):
    """
    SQLAlchemy model representing a software update publication event.
    """
    __tablename__ = "program_update_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    program_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("programs.id", ondelete="CASCADE"), nullable=False, index=True)
    version_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("program_versions.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )


class NotificationJob(Base):
    """
    SQLAlchemy model representing a queued background notification job for worker processing.
    Status: 'pending', 'processing', 'sent', 'failed', 'cancelled'
    """
    __tablename__ = "notification_jobs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    program_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("programs.id", ondelete="CASCADE"), nullable=False, index=True)
    version_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("program_versions.id", ondelete="CASCADE"), nullable=False, index=True)

    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False, index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class UserNotification(Base):
    """
    SQLAlchemy model representing an in-app user notification for the Notification Center.
    """
    __tablename__ = "user_notifications"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(50), default="update", nullable=False)
    program_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("programs.id", ondelete="CASCADE"), nullable=True)
    version_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("program_versions.id", ondelete="CASCADE"), nullable=True)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )

    user = relationship("User", backref="notifications")
