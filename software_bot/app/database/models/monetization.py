from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, BigInteger
from sqlalchemy.orm import relationship
from app.database.base import Base


class PremiumPlan(Base):
    __tablename__ = "premium_plans"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(String(255), nullable=True)
    price = Column(Integer, nullable=False)  # Price in UZS minor units (e.g. 29000)
    currency = Column(String(10), default="UZS")
    duration_days = Column(Integer, nullable=False)  # 30, 90, 180, 365
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    subscriptions = relationship("Subscription", back_populates="plan", cascade="all, delete-orphan")


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    plan_id = Column(Integer, ForeignKey("premium_plans.id", ondelete="SET NULL"), nullable=True)
    status = Column(String(20), default="ACTIVE", index=True)  # PENDING, ACTIVE, EXPIRED, CANCELLED, REFUNDED
    started_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    payment_id = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    user = relationship("User", backref="subscriptions")
    plan = relationship("PremiumPlan", back_populates="subscriptions")


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    product_type = Column(String(20), nullable=False)  # PREMIUM, PROGRAM
    product_id = Column(Integer, nullable=False)
    amount = Column(Integer, nullable=False)  # Minor units
    currency = Column(String(10), default="UZS")
    status = Column(String(20), default="PENDING", index=True)  # PENDING, PAID, FAILED, CANCELLED, REFUNDED, EXPIRED
    provider = Column(String(50), default="SANDBOX")
    provider_payment_id = Column(String(100), nullable=True, unique=True)
    idempotency_key = Column(String(100), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    paid_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", backref="orders")


class ProgramEntitlement(Base):
    __tablename__ = "program_entitlements"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    program_id = Column(Integer, ForeignKey("programs.id", ondelete="CASCADE"), nullable=False, index=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="SET NULL"), nullable=True)
    status = Column(String(20), default="ACTIVE")  # ACTIVE, REVOKED
    granted_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime(timezone=True), nullable=True)  # NULL for lifetime access

    user = relationship("User", backref="program_entitlements")
    program = relationship("Program", backref="entitlements")


class PromoCode(Base):
    __tablename__ = "promo_codes"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False, index=True)
    type = Column(String(20), default="PERCENT")  # PERCENT, FIXED, FREE_DAYS
    value = Column(Integer, nullable=False)  # e.g. 10 (for 10%), 10000 (for 10,000 UZS), 7 (for 7 days)
    max_uses = Column(Integer, default=100)
    used_count = Column(Integer, default=0)
    starts_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class PromoUsage(Base):
    __tablename__ = "promo_usages"

    id = Column(Integer, primary_key=True, index=True)
    promo_id = Column(Integer, ForeignKey("promo_codes.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="SET NULL"), nullable=True)
    used_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class RevenueEvent(Base):
    __tablename__ = "revenue_events"

    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String(50), nullable=False)  # ORDER_CREATED, PAYMENT_PAID, PAYMENT_FAILED, REFUND_COMPLETED
    user_id = Column(Integer, nullable=False)
    order_id = Column(Integer, nullable=True)
    amount = Column(Integer, default=0)
    currency = Column(String(10), default="UZS")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
