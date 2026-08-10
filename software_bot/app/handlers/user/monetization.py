import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.database.engine import async_session_maker
from app.services.entitlement_service import EntitlementService
from app.services.payment_service import PaymentService
from app.services.user_service import UserService
from app.keyboards.user.reply import get_user_main_keyboard

logger = logging.getLogger(__name__)
router = Router(name="user_monetization_router")


def build_premium_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="⭐ Tariflarni ko'rish", callback_data="user:premium:plans"),
        InlineKeyboardButton(text="📜 Obunam", callback_data="user:premium:my_sub")
    )
    builder.row(InlineKeyboardButton(text="💳 Xaridlarim", callback_data="user:purchases:history"))
    return builder.as_markup()


def build_premium_plans_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="⭐ Premium 1 oy — 29 000 UZS", callback_data="user:premium:buy:1"))
    builder.row(InlineKeyboardButton(text="⭐ Premium 3 oy — 79 000 UZS", callback_data="user:premium:buy:2"))
    builder.row(InlineKeyboardButton(text="⭐ Premium 6 oy — 139 000 UZS", callback_data="user:premium:buy:3"))
    builder.row(InlineKeyboardButton(text="⭐ Premium 12 oy — 249 000 UZS", callback_data="user:premium:buy:4"))
    builder.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data="user:premium:menu"))
    return builder.as_markup()


# -----------------------------------------------------------------------------
# Main Premium Landing Page
# -----------------------------------------------------------------------------
@router.message(F.text == "⭐ Premium")
@router.callback_query(F.data == "user:premium:menu")
async def user_premium_menu_handler(event: Message | CallbackQuery):
    if isinstance(event, CallbackQuery):
        await event.answer()

    user_tg_id = event.from_user.id
    async with async_session_maker() as session:
        user_service = UserService(session)
        user = await user_service.get_user_by_telegram_id(user_tg_id)

        ent_service = EntitlementService(session)
        has_prem = await ent_service.has_active_premium(user.id) if user else False

    status_str = "🟢 ACTIVE" if has_prem else "⚪ INACTIVE"

    text = (
        f"⭐ **PREMIUM OBUNA**\n\n"
        f"Sizning obuna maqomingiz: **{status_str}**\n\n"
        f"**Premium obuna imkoniyatlari:**\n"
        f"🚀 Premium katalog dasturlarini yuklab olish\n"
        f"⚡ Cheklovsiz yuklash tezligi\n"
        f"🔔 Yangi versiyalar va update xabarnomalari\n"
        f"🎁 Maxsus aksiyalar va promokodlar\n\n"
        f"Quyidagi tugmalar orqali tarif tanlang:"
    )

    kb = build_premium_menu_keyboard()
    if isinstance(event, Message):
        await event.answer(text, reply_markup=kb, parse_mode="Markdown")
    elif isinstance(event, CallbackQuery) and event.message:
        await event.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")


# -----------------------------------------------------------------------------
# Plans List
# -----------------------------------------------------------------------------
@router.callback_query(F.data == "user:premium:plans")
async def user_premium_plans_handler(callback: CallbackQuery):
    await callback.answer()
    text = (
        "⭐ **PREMIUM TARIFLAR**\n\n"
        "O'zingizga mos tarifni tanlang va barcha premium dasturlarga kirish huquqini qo'lga kiriting:"
    )
    kb = build_premium_plans_keyboard()
    if callback.message:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")


# -----------------------------------------------------------------------------
# Order Creation & Payment
# -----------------------------------------------------------------------------
@router.callback_query(F.data.startswith("user:premium:buy:"))
async def user_premium_buy_handler(callback: CallbackQuery):
    await callback.answer()
    plan_id = int(callback.data.split(":")[-1])
    user_tg_id = callback.from_user.id

    plan_prices = {1: (29000, "1 oy"), 2: (79000, "3 oy"), 3: (139000, "6 oy"), 4: (249000, "12 oy")}
    price, label = plan_prices.get(plan_id, (29000, "1 oy"))

    async with async_session_maker() as session:
        user_service = UserService(session)
        user = await user_service.get_user_by_telegram_id(user_tg_id)

        payment_service = PaymentService(session)
        order = await payment_service.create_order(
            user_id=user.id,
            product_type="PREMIUM",
            product_id=plan_id,
            amount=price
        )

    text = (
        f"💳 **TO'LOV BUYURTMASI**\n\n"
        f"Buyurtma raqami: `#ORD-{order.id:06d}`\n"
        f"Mahsulot: **⭐ Premium — {label}**\n"
        f"Summa: **{price:,} UZS**\n\n"
        f"To'lovni amalga oshirish uchun pastdagi tugmani bosing:"
    )

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="💳 TO'LASH (SANDBOX)", callback_data=f"user:premium:pay_confirm:{order.id}"))
    builder.row(InlineKeyboardButton(text="❌ Bekor qilish", callback_data="user:premium:plans"))

    if callback.message:
        await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="Markdown")


# -----------------------------------------------------------------------------
# Payment Confirmation
# -----------------------------------------------------------------------------
@router.callback_query(F.data.startswith("user:premium:pay_confirm:"))
async def user_premium_pay_confirm_handler(callback: CallbackQuery):
    order_id = int(callback.data.split(":")[-1])
    fake_provider_payment_id = f"PAY-{order_id}-{callback.from_user.id}"

    async with async_session_maker() as session:
        payment_service = PaymentService(session)
        # Fetch order to get price
        from app.database.models import Order
        from sqlalchemy import select
        res = await session.execute(select(Order).where(Order.id == order_id))
        order = res.scalar_one_or_none()
        price = order.amount if order else 29000

        success, msg = await payment_service.process_payment(
            order_id=order_id,
            provider_payment_id=fake_provider_payment_id,
            paid_amount=price
        )

    if success:
        await callback.answer("✅ To'lov muvaffaqiyatli amalga oshirildi!", show_alert=True)
        text = (
            "🧾 **TO'LOV MUVAFFAQIYATLI!**\n\n"
            f"Order ID: `#ORD-{order_id:06d}`\n"
            "Maqom: **🟢 PAID**\n"
            "Tabriklaymiz! Sizning Premium obunangiz faollashtirildi."
        )
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="⭐ Premium Menyu", callback_data="user:premium:menu"))
        if callback.message:
            await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="Markdown")
    else:
        await callback.answer(f"❌ To'lov rad etildi: {msg}", show_alert=True)


@router.callback_query(F.data == "user:premium:my_sub")
async def user_premium_my_sub_handler(callback: CallbackQuery):
    await callback.answer()
    if not callback.from_user:
        return

    user_tg_id = callback.from_user.id
    async with async_session_maker() as session:
        user_service = UserService(session)
        user = await user_service.get_user_by_telegram_id(user_tg_id)
        if not user:
            await callback.answer("⚠️ Foydalanuvchi topilmadi.", show_alert=True)
            return

        from app.database.models import Subscription
        from sqlalchemy import select
        stmt = (
            select(Subscription)
            .where(Subscription.user_id == user.id, Subscription.status == "ACTIVE")
            .order_by(Subscription.expires_at.desc())
            .limit(1)
        )
        res = await session.execute(stmt)
        active_sub = res.scalar_one_or_none()

    if active_sub:
        exp_str = active_sub.expires_at.strftime("%d.%m.%Y %H:%M") if active_sub.expires_at else "Noma'lum"
        text = (
            "📜 **SHAXSIY OBUNANGIZ HAQIDA MA'LUMOT**\n\n"
            "Status: **🟢 FAOL (ACTIVE)**\n"
            f"Tugash sanasi: **{exp_str}**\n\n"
            "🚀 Sizda barcha Premium imkoniyatlar faol!"
        )
    else:
        text = (
            "📜 **SHAXSIY OBUNANGIZ HAQIDA MA'LUMOT**\n\n"
            "Status: **⚪ NOFAOL (INACTIVE)**\n\n"
            "Sizda hozircha faol Premium obuna mavjud emas.\n"
            "Tarif tanlash uchun quyidagi tugmani bosing:"
        )

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="⭐ Tariflarni ko'rish", callback_data="user:premium:plans"))
    builder.row(InlineKeyboardButton(text="🔙 Premium menyu", callback_data="user:premium:menu"))

    if callback.message:
        await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="Markdown")


@router.callback_query(F.data == "user:purchases:history")
async def user_purchases_history_handler(callback: CallbackQuery):
    await callback.answer()
    if not callback.from_user:
        return

    user_tg_id = callback.from_user.id
    async with async_session_maker() as session:
        user_service = UserService(session)
        user = await user_service.get_user_by_telegram_id(user_tg_id)
        if not user:
            await callback.answer("⚠️ Foydalanuvchi topilmadi.", show_alert=True)
            return

        from app.database.models import Order
        from sqlalchemy import select
        stmt = (
            select(Order)
            .where(Order.user_id == user.id)
            .order_by(Order.created_at.desc())
            .limit(10)
        )
        res = await session.execute(stmt)
        orders = list(res.scalars().all())

    if not orders:
        text = "💳 **XARIDLAR TARIHI**\n\nSiz hali hech qanday xarid amalga oshirmagansiz."
    else:
        text = "💳 **OXIRGI XARIDLARINGIZ TARIHI**\n\n"
        for o in orders:
            status_icon = "🟢" if o.status == "PAID" else ("🔴" if o.status == "FAILED" else "⏳")
            created_str = o.created_at.strftime("%d.%m.%Y") if o.created_at else ""
            text += f"{status_icon} `#ORD-{o.id:06d}` — **{o.amount:,} UZS** ({created_str})\n"

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔙 Premium menyu", callback_data="user:premium:menu"))

    if callback.message:
        await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="Markdown")
