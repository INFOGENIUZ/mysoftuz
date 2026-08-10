import logging
from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from app.config import settings
from app.database.engine import async_session_maker
from app.services.category_service import CategoryService
from app.services.admin_service import AdminService
from app.states.admin_category import AdminCategoryCreateState, AdminCategoryEditState
from app.keyboards.admin.reply import get_admin_main_keyboard, get_admin_cancel_keyboard
from app.keyboards.admin.inline import (
    build_admin_categories_keyboard,
    build_admin_category_detail_keyboard,
    build_admin_category_preview_keyboard,
    build_admin_category_edit_keyboard,
    build_admin_category_deactivate_confirm_keyboard,
    build_admin_category_activate_confirm_keyboard,
    build_admin_category_delete_confirm_keyboard,
)
from app.utils.callback_factory import safe_answer_callback
from app.utils.validators import validate_name, validate_description

logger = logging.getLogger(__name__)
router = Router(name="admin_categories_router")


# -----------------------------------------------------------------------------
# Cancel / Reset FSM handler
# -----------------------------------------------------------------------------
@router.message(F.text == "❌ Bekor qilish", StateFilter("*"))
@router.message(F.text == "/cancel", StateFilter("*"))
async def admin_category_cancel_handler(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "❌ Kategoriya jarayoni bekor qilindi.",
        reply_markup=get_admin_main_keyboard()
    )


# -----------------------------------------------------------------------------
# Category List & Pagination
# -----------------------------------------------------------------------------
@router.message(F.text == "📂 Kategoriyalar")
@router.callback_query(F.data == "admin:categories:list")
async def admin_categories_list_handler(event: Message | CallbackQuery, is_admin: bool = False):
    if not is_admin:
        if isinstance(event, Message):
            await event.answer("⛔ Sizda ushbu bo'limga kirish huquqi yo'q.")
        elif isinstance(event, CallbackQuery):
            await event.answer("⛔ Sizda ushbu bo'limga kirish huquqi yo'q.", show_alert=True)
        return

    if isinstance(event, CallbackQuery):
        await event.answer()

    async with async_session_maker() as session:
        cat_service = CategoryService(session)
        categories_with_count, total_pages = await cat_service.get_admin_categories_paginated(
            page=1, page_size=settings.CATEGORIES_PER_PAGE
        )

    text = "📂 **KATEGORIYALARNI BOSHQARISH**\n\nKategoriyalarni boshqarish bo'limi:"
    kb = build_admin_categories_keyboard(categories_with_count, current_page=1, total_pages=total_pages)

    if isinstance(event, Message):
        await event.answer(text=text, reply_markup=kb, parse_mode="Markdown")
    elif isinstance(event, CallbackQuery) and event.message:
        await event.message.edit_text(text=text, reply_markup=kb, parse_mode="Markdown")


@router.callback_query(F.data.startswith("admin:categories:page:"))
async def admin_categories_page_handler(callback: CallbackQuery, is_admin: bool = False):
    if not is_admin:
        await callback.answer("⛔ Sizda ushbu bo'limga kirish huquqi yo'q.", show_alert=True)
        return
    await callback.answer()

    try:
        page = int(callback.data.split(":")[-1])
    except ValueError:
        page = 1

    async with async_session_maker() as session:
        cat_service = CategoryService(session)
        categories_with_count, total_pages = await cat_service.get_admin_categories_paginated(
            page=page, page_size=settings.CATEGORIES_PER_PAGE
        )

    text = f"📂 **KATEGORIYALARNI BOSHQARISH** (Sahifa {page}/{total_pages})\n\nKategoriyalar ro'yxati:"
    kb = build_admin_categories_keyboard(categories_with_count, current_page=page, total_pages=total_pages)

    if callback.message:
        await callback.message.edit_text(text=text, reply_markup=kb, parse_mode="Markdown")


# -----------------------------------------------------------------------------
# Category Detail View
# -----------------------------------------------------------------------------
@router.callback_query(F.data.startswith("admin:category:view:"))
async def admin_category_view_handler(callback: CallbackQuery, is_admin: bool = False, admin_role: str = "admin"):
    if not is_admin:
        await callback.answer("⛔ Sizda ushbu bo'limga kirish huquqi yo'q.", show_alert=True)
        return
    await callback.answer()

    try:
        category_id = int(callback.data.split(":")[-1])
    except ValueError:
        await safe_answer_callback(callback, "⚠️ Noto'g'ri kategoriya ID")
        return

    async with async_session_maker() as session:
        cat_service = CategoryService(session)
        category, prog_count = await cat_service.get_category_with_program_count(category_id)

    if not category:
        await safe_answer_callback(callback, "⚠️ Kategoriya topilmadi")
        return

    status_str = "🟢 Faol" if category.is_active else "🔴 Nofaol"
    icon_str = f"{category.icon} " if category.icon else ""
    detail_text = (
        f"📂 **{icon_str}{category.name.upper()}**\n\n"
        f"📝 {category.description or 'Tavsif berilmagan.'}\n\n"
        f"🟢 Holati: **{status_str}**\n"
        f"🔢 Tartib: **{category.sort_order}**\n"
        f"💻 Dasturlar soni: **{prog_count} ta**\n\n"
        f"🆔 ID: **{category.id}**"
    )

    kb = build_admin_category_detail_keyboard(category, program_count=prog_count, user_role=admin_role)

    if callback.message:
        if category.image_file_id:
            try:
                await callback.message.edit_text(text=detail_text, reply_markup=kb, parse_mode="Markdown")
            except Exception:
                await callback.message.answer(text=detail_text, reply_markup=kb, parse_mode="Markdown")
        else:
            await callback.message.edit_text(text=detail_text, reply_markup=kb, parse_mode="Markdown")


# -----------------------------------------------------------------------------
# Create Category Flow (FSM)
# -----------------------------------------------------------------------------
@router.callback_query(F.data == "admin:category:create")
async def admin_category_create_start(callback: CallbackQuery, state: FSMContext, admin_role: str = "admin"):
    if admin_role == "moderator":
        await callback.answer("⛔ Moderatorlarda kategoriya yaratish huquqi yo'q.", show_alert=True)
        return
    await callback.answer()

    await state.set_state(AdminCategoryCreateState.waiting_for_name)
    await state.update_data(admin_id=callback.from_user.id)

    msg_text = "📝 **Kategoriya nomini kiriting:**\n\nMasalan:\n🎨 Grafik dizayn"
    if callback.message:
        await callback.message.answer(msg_text, reply_markup=get_admin_cancel_keyboard(), parse_mode="Markdown")


@router.message(AdminCategoryCreateState.waiting_for_name)
async def admin_category_create_name(message: Message, state: FSMContext):
    name = message.text.strip() if message.text else ""
    if not validate_name(name, min_len=1, max_len=150):
        await message.answer("⚠️ Noto'g'ri nom formatini kiriting (1–150 belgi):")
        return

    async with async_session_maker() as session:
        cat_service = CategoryService(session)
        dup = await cat_service.get_category_by_slug(name)
        if dup:
            await message.answer("⚠️ Bu nomdagi kategoriya allaqachon mavjud.\n\nBoshqa nom kiriting:")
            return

    await state.update_data(name=name)
    await state.set_state(AdminCategoryCreateState.waiting_for_description)

    prompt = "📝 **Kategoriya tavsifini kiriting:**\n\n(O'tkazib yuborish uchun `/skip` yuboring)"
    await message.answer(prompt, reply_markup=get_admin_cancel_keyboard(show_skip=True), parse_mode="Markdown")


@router.message(AdminCategoryCreateState.waiting_for_description)
async def admin_category_create_description(message: Message, state: FSMContext):
    text = message.text.strip() if message.text else ""
    desc = None if text in ("/skip", "⏭ O'tkazib yuborish") else text

    if desc and not validate_description(desc, max_len=1000):
        await message.answer("⚠️ Tavsif juda uzun (maksimal 1000 belgi). Qayta kiriting:")
        return

    await state.update_data(description=desc)
    await state.set_state(AdminCategoryCreateState.waiting_for_icon)

    prompt = "🎨 **Kategoriya uchun emoji/icon yuboring:**\n\nMasalan:\n🎨\n(O'tkazib yuborish uchun `/skip` yuboring)"
    await message.answer(prompt, reply_markup=get_admin_cancel_keyboard(show_skip=True), parse_mode="Markdown")


@router.message(AdminCategoryCreateState.waiting_for_icon)
async def admin_category_create_icon(message: Message, state: FSMContext):
    text = message.text.strip() if message.text else ""
    icon = "📂" if text in ("/skip", "⏭ O'tkazib yuborish") or not text else text[:10]

    await state.update_data(icon=icon)
    await state.set_state(AdminCategoryCreateState.waiting_for_image)

    prompt = "🖼 **Kategoriya rasmini yuboring:**\n\n(O'tkazib yuborish uchun `/skip` yuboring)"
    await message.answer(prompt, reply_markup=get_admin_cancel_keyboard(show_skip=True), parse_mode="Markdown")


@router.message(AdminCategoryCreateState.waiting_for_image)
async def admin_category_create_image(message: Message, state: FSMContext):
    image_file_id = None
    if message.photo:
        image_file_id = message.photo[-1].file_id
    elif message.text and message.text.strip() in ("/skip", "⏭ O'tkazib yuborish"):
        image_file_id = None
    else:
        await message.answer("❌ Iltimos, rasm yuboring yoki `/skip` bosing.")
        return

    await state.update_data(image_file_id=image_file_id)
    await state.set_state(AdminCategoryCreateState.waiting_for_sort_order)

    prompt = "🔢 **Kategoriya tartib raqamini kiriting (masalan 1):**\n\n(O'tkazib yuborish uchun `/skip` yuboring)"
    await message.answer(prompt, reply_markup=get_admin_cancel_keyboard(show_skip=True), parse_mode="Markdown")


@router.message(AdminCategoryCreateState.waiting_for_sort_order)
async def admin_category_create_sort_order(message: Message, state: FSMContext):
    text = message.text.strip() if message.text else ""
    sort_order = 0
    if text not in ("/skip", "⏭ O'tkazib yuborish"):
        if not text.isdigit() or int(text) < 0:
            await message.answer("⚠️ Tartib raqami musbat integer bo'lishi kerak! Qayta kiriting:")
            return
        sort_order = int(text)

    await state.update_data(sort_order=sort_order)
    await state.set_state(AdminCategoryCreateState.waiting_for_confirm)

    data = await state.get_data()

    preview_text = (
        "📂 **KATEGORIYA PREVIEW**\n\n"
        f"{data.get('icon', '📂')} **{data.get('name')}**\n\n"
        f"📝 {data.get('description') or 'Tavsif berilmagan.'}\n\n"
        f"🔢 Tartib: **{sort_order}**\n"
        f"🟢 Holati: **Faol**"
    )

    kb = build_admin_category_preview_keyboard()
    if data.get("image_file_id"):
        await message.answer_photo(photo=data["image_file_id"], caption=preview_text, reply_markup=kb, parse_mode="Markdown")
    else:
        await message.answer(text=preview_text, reply_markup=kb, parse_mode="Markdown")


@router.callback_query(F.data == "admin:category:save_confirm", AdminCategoryCreateState.waiting_for_confirm)
async def admin_category_save_confirm(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()

    async with async_session_maker() as session:
        cat_service = CategoryService(session)
        category = await cat_service.create_category(
            name=data["name"],
            description=data.get("description"),
            icon=data.get("icon"),
            image_file_id=data.get("image_file_id"),
            sort_order=data.get("sort_order", 0)
        )

    await state.clear()
    success_text = f"✅ **Kategoriya muvaffaqiyatli yaratildi!**\n\n📂 {category.name}"
    if callback.message:
        await callback.message.answer(success_text, reply_markup=get_admin_main_keyboard(), parse_mode="Markdown")


@router.callback_query(F.data == "admin:category:cancel_create", StateFilter("*"))
async def admin_category_cancel_create(callback: CallbackQuery, state: FSMContext):
    await callback.answer("❌ Kategoriya yaratish bekor qilindi.")
    await state.clear()
    if callback.message:
        await callback.message.answer("❌ Kategoriya yaratish bekor qilindi.", reply_markup=get_admin_main_keyboard())


# -----------------------------------------------------------------------------
# Edit Category Flow
# -----------------------------------------------------------------------------
@router.callback_query(F.data.startswith("admin:category:edit:"))
async def admin_category_edit_menu(callback: CallbackQuery, admin_role: str = "admin"):
    if admin_role == "moderator":
        await callback.answer("⛔ Moderatorlarda tahrirlash huquqi yo'q.", show_alert=True)
        return
    await callback.answer()

    try:
        category_id = int(callback.data.split(":")[-1])
    except ValueError:
        return

    text = "✏️ **KATEGORIYANI TAHRIRLASH**\n\nNimani o'zgartirmoqchisiz?"
    kb = build_admin_category_edit_keyboard(category_id)

    if callback.message:
        await callback.message.edit_text(text=text, reply_markup=kb, parse_mode="Markdown")


@router.callback_query(F.data.startswith("admin:category:edit_field:"))
async def admin_category_edit_field_prompt(callback: CallbackQuery, state: FSMContext, admin_role: str = "admin"):
    if admin_role == "moderator":
        await callback.answer("⛔ Moderatorlarda tahrirlash huquqi yo'q.", show_alert=True)
        return
    await callback.answer()

    parts = callback.data.split(":")
    category_id = int(parts[3])
    field = parts[4]

    await state.set_state(AdminCategoryEditState.waiting_for_new_value)
    await state.update_data(category_id=category_id, field=field)

    prompts = {
        "name": "📝 **Yangi kategoriya nomini kiriting:**",
        "description": "📄 **Yangi tavsifni kiriting:** (O'chirish uchun `/skip` yuboring)",
        "icon": "🎨 **Yangi emoji/icon yuboring:** (O'chirish uchun `/skip` yuboring)",
        "image": "🖼 **Yangi rasm yuboring:** (Rasmni o'chirish uchun `/remove` yuboring)",
        "sort_order": "🔢 **Yangi tartib raqamini kiriting (masalan 1):**",
    }

    prompt_text = prompts.get(field, "Yangi qiymatni kiriting:")
    if callback.message:
        await callback.message.answer(prompt_text, reply_markup=get_admin_cancel_keyboard(show_skip=True), parse_mode="Markdown")


@router.message(AdminCategoryEditState.waiting_for_new_value)
async def admin_category_edit_value_save(message: Message, state: FSMContext):
    data = await state.get_data()
    category_id = data.get("category_id")
    field = data.get("field")

    async with async_session_maker() as session:
        cat_service = CategoryService(session)
        try:
            if field == "name":
                name = message.text.strip() if message.text else ""
                if not validate_name(name):
                    await message.answer("⚠️ Noto'g'ri nom formatini kiriting:")
                    return
                await cat_service.update_category(category_id, name=name)

            elif field == "description":
                text = message.text.strip() if message.text else ""
                if text in ("/skip", "⏭ O'tkazib yuborish"):
                    await cat_service.update_category(category_id, unset_description=True)
                else:
                    await cat_service.update_category(category_id, description=text)

            elif field == "icon":
                text = message.text.strip() if message.text else ""
                if text in ("/skip", "⏭ O'tkazib yuborish"):
                    await cat_service.update_category(category_id, unset_icon=True)
                else:
                    await cat_service.update_category(category_id, icon=text[:10])

            elif field == "image":
                if message.photo:
                    await cat_service.update_category(category_id, image_file_id=message.photo[-1].file_id)
                elif message.text and message.text.strip() in ("/remove", "/skip", "⏭ O'tkazib yuborish"):
                    await cat_service.update_category(category_id, unset_image=True)
                else:
                    await message.answer("❌ Iltimos rasm yuboring yoki `/remove` bosing.")
                    return

            elif field == "sort_order":
                text = message.text.strip() if message.text else ""
                if not text.isdigit() or int(text) < 0:
                    await message.answer("⚠️ Tartib raqami musbat integer bo'lishi kerak:")
                    return
                await cat_service.update_category(category_id, sort_order=int(text))

        except ValueError as ve:
            await message.answer(f"⚠️ {ve}\n\nQayta kiriting:")
            return

    await state.clear()
    await message.answer("✅ **Kategoriya muvaffaqiyatli yangilandi!**", reply_markup=get_admin_main_keyboard(), parse_mode="Markdown")


# -----------------------------------------------------------------------------
# Activate / Deactivate Category Flow
# -----------------------------------------------------------------------------
@router.callback_query(F.data.startswith("admin:category:deactivate:"))
async def admin_category_deactivate_prompt(callback: CallbackQuery, admin_role: str = "admin"):
    if admin_role == "moderator":
        await callback.answer("⛔ Moderatorlarda ruxsat yo'q.", show_alert=True)
        return
    await callback.answer()
    category_id = int(callback.data.split(":")[-1])

    async with async_session_maker() as session:
        cat_service = CategoryService(session)
        category = await cat_service.get_category_by_id(category_id)

    if not category:
        return

    text = (
        f"⚠️ **Kategoriyani nofaol qilmoqchimisiz?**\n\n"
        f"Kategoriya: **{category.name}**\n\n"
        "Bu kategoriya va uning dasturlari foydalanuvchilarga ko'rsatilmaydi."
    )
    kb = build_admin_category_deactivate_confirm_keyboard(category_id)
    if callback.message:
        await callback.message.edit_text(text=text, reply_markup=kb, parse_mode="Markdown")


@router.callback_query(F.data.startswith("admin:category:deactivate_confirm:"))
async def admin_category_deactivate_confirm(callback: CallbackQuery, admin_role: str = "admin"):
    if admin_role == "moderator":
        await callback.answer("⛔ Moderatorlarda ruxsat yo'q.", show_alert=True)
        return
    category_id = int(callback.data.split(":")[-1])

    async with async_session_maker() as session:
        cat_service = CategoryService(session)
        await cat_service.deactivate_category(category_id)

    await callback.answer("🔴 Kategoriya nofaol qilindi!", show_alert=True)
    await admin_category_view_handler(callback, is_admin=True, admin_role=admin_role)


@router.callback_query(F.data.startswith("admin:category:activate:"))
async def admin_category_activate_prompt(callback: CallbackQuery, admin_role: str = "admin"):
    if admin_role == "moderator":
        await callback.answer("⛔ Moderatorlarda ruxsat yo'q.", show_alert=True)
        return
    await callback.answer()
    category_id = int(callback.data.split(":")[-1])

    async with async_session_maker() as session:
        cat_service = CategoryService(session)
        category = await cat_service.get_category_by_id(category_id)

    if not category:
        return

    text = f"🟢 **Kategoriyani faollashtirmoqchimisiz?**\n\nKategoriya: **{category.name}**"
    kb = build_admin_category_activate_confirm_keyboard(category_id)
    if callback.message:
        await callback.message.edit_text(text=text, reply_markup=kb, parse_mode="Markdown")


@router.callback_query(F.data.startswith("admin:category:activate_confirm:"))
async def admin_category_activate_confirm(callback: CallbackQuery, admin_role: str = "admin"):
    if admin_role == "moderator":
        await callback.answer("⛔ Moderatorlarda ruxsat yo'q.", show_alert=True)
        return
    category_id = int(callback.data.split(":")[-1])

    async with async_session_maker() as session:
        cat_service = CategoryService(session)
        await cat_service.activate_category(category_id)

    await callback.answer("🟢 Kategoriya faollashtirildi!", show_alert=True)
    await admin_category_view_handler(callback, is_admin=True, admin_role=admin_role)


# -----------------------------------------------------------------------------
# Delete Category Flow with Protection
# -----------------------------------------------------------------------------
@router.callback_query(F.data.startswith("admin:category:delete:"))
async def admin_category_delete_prompt(callback: CallbackQuery, admin_role: str = "admin"):
    if admin_role == "moderator":
        await callback.answer("⛔ Moderatorlarda o'chirish huquqi yo'q.", show_alert=True)
        return
    await callback.answer()
    category_id = int(callback.data.split(":")[-1])

    async with async_session_maker() as session:
        cat_service = CategoryService(session)
        category, prog_count = await cat_service.get_category_with_program_count(category_id)

    if not category:
        return

    # Delete Protection Check
    if prog_count > 0:
        blocked_text = (
            f"⚠️ **Kategoriyani o'chirib bo'lmaydi.**\n\n"
            f"📦 Ushbu kategoriyada **{prog_count} ta** dastur mavjud.\n\n"
            "Avval dasturlarni boshqa kategoriyaga ko'chiring yoki boshqaring."
        )
        if callback.message:
            try:
                await callback.message.edit_text(
                    text=blocked_text,
                    reply_markup=build_admin_category_detail_keyboard(category, prog_count, user_role=admin_role),
                    parse_mode="Markdown"
                )
            except Exception:
                pass
        return


    text = f"⚠️ **Kategoriyani o'chirishni tasdiqlaysizmi?**\n\n📂 **{category.name}**"
    kb = build_admin_category_delete_confirm_keyboard(category_id)
    if callback.message:
        await callback.message.edit_text(text=text, reply_markup=kb, parse_mode="Markdown")


@router.callback_query(F.data.startswith("admin:category:delete_confirm:"))
async def admin_category_delete_confirm(callback: CallbackQuery, admin_role: str = "admin"):
    if admin_role == "moderator":
        await callback.answer("⛔ Moderatorlarda o'chirish huquqi yo'q.", show_alert=True)
        return
    category_id = int(callback.data.split(":")[-1])

    async with async_session_maker() as session:
        cat_service = CategoryService(session)
        try:
            await cat_service.delete_category(category_id)
            await callback.answer("🗑 Kategoriya muvaffaqiyatli o'chirildi!", show_alert=True)
        except ValueError as ve:
            await callback.answer(f"⚠️ {ve}", show_alert=True)
            return

    await admin_categories_list_handler(callback, is_admin=True)


# -----------------------------------------------------------------------------
# Add Program Redirect (Stage 6 Integration)
# -----------------------------------------------------------------------------
@router.callback_query(F.data.startswith("admin:category:add_program:"))
async def admin_category_add_program_redirect(callback: CallbackQuery, state: FSMContext, admin_role: str = "admin"):
    from app.handlers.admin.programs import admin_program_create_start
    await admin_program_create_start(callback, state, admin_role=admin_role)

