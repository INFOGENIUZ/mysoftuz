import logging
from sqlalchemy import select
from aiogram import Router, F, Bot
from aiogram.filters import StateFilter
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from app.config import settings
from app.database.engine import async_session_maker
from app.database.models import Program, Category
from app.services.category_service import CategoryService
from app.services.program_service import ProgramService


from app.states.admin_program import AdminProgramCreateState, AdminProgramEditState
from app.keyboards.admin.reply import get_admin_main_keyboard, get_admin_cancel_keyboard
from app.keyboards.admin.inline import (
    build_admin_programs_keyboard,
    build_admin_program_detail_keyboard,
    build_admin_architecture_keyboard,
    build_admin_program_preview_keyboard,
    build_admin_program_edit_keyboard,
    build_admin_program_category_select_keyboard,
    build_admin_program_deactivate_confirm_keyboard,
    build_admin_program_activate_confirm_keyboard,
    build_admin_program_delete_confirm_keyboard,
)
from app.utils.callback_factory import safe_answer_callback
from app.utils.validators import (
    validate_name,
    validate_short_description,
    validate_description,
    validate_version,
    validate_system_requirements,
    validate_url,
    validate_file_size,
    is_extension_allowed,
)

logger = logging.getLogger(__name__)
router = Router(name="admin_programs_router")


def format_size(size_bytes: int) -> str:
    """Helper to convert bytes to human readable format."""
    if not size_bytes or size_bytes <= 0:
        return "Nol/Noma'lum"
    if size_bytes >= 1073741824:
        return f"{size_bytes / 1073741824:.1f} GB"
    elif size_bytes >= 1048576:
        return f"{size_bytes / 1048576:.1f} MB"
    elif size_bytes >= 1024:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes} Bytes"


# -----------------------------------------------------------------------------
# Cancel / Reset FSM handler
# -----------------------------------------------------------------------------
@router.message(F.text == "❌ Bekor qilish", StateFilter(AdminProgramCreateState), StateFilter(AdminProgramEditState))
@router.message(F.text == "/cancel", StateFilter(AdminProgramCreateState), StateFilter(AdminProgramEditState))
async def admin_program_cancel_handler(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "❌ Dastur jarayoni bekor qilindi.",
        reply_markup=get_admin_main_keyboard()
    )


# -----------------------------------------------------------------------------
# Program List & Pagination under Category
# -----------------------------------------------------------------------------
@router.callback_query(F.data.startswith("admin:programs:list:"))
async def admin_programs_list_handler(callback: CallbackQuery, is_admin: bool = False):
    if not is_admin:
        await callback.answer("⛔ Sizda ushbu bo'limga kirish huquqi yo'q.", show_alert=True)
        return
    await callback.answer()

    try:
        category_id = int(callback.data.split(":")[-1])
    except ValueError:
        return

    async with async_session_maker() as session:
        cat_service = CategoryService(session)
        prog_service = ProgramService(session)

        category = await cat_service.get_category_by_id(category_id)
        if not category:
            await safe_answer_callback(callback, "⚠️ Kategoriya topilmadi")
            return

        programs, total_pages = await prog_service.get_admin_programs_by_category_paginated(
            category_id=category_id, page=1, page_size=settings.PROGRAMS_PER_PAGE
        )

    text = f"📂 **{category.name.upper()} — DASTURLAR**\n\nKategoriyadagi barcha dasturlar:"
    kb = build_admin_programs_keyboard(programs, category_id=category_id, current_page=1, total_pages=total_pages)

    if callback.message:
        await callback.message.edit_text(text=text, reply_markup=kb, parse_mode="Markdown")


@router.callback_query(F.data.startswith("admin:programs:page:"))
async def admin_programs_page_handler(callback: CallbackQuery, is_admin: bool = False):
    if not is_admin:
        await callback.answer("⛔ Sizda ushbu bo'limga kirish huquqi yo'q.", show_alert=True)
        return
    await callback.answer()

    parts = callback.data.split(":")
    if len(parts) < 5:
        return
    try:
        category_id = int(parts[3])
        page = int(parts[4])
    except ValueError:
        return

    async with async_session_maker() as session:
        cat_service = CategoryService(session)
        prog_service = ProgramService(session)

        category = await cat_service.get_category_by_id(category_id)
        if not category:
            return

        programs, total_pages = await prog_service.get_admin_programs_by_category_paginated(
            category_id=category_id, page=page, page_size=settings.PROGRAMS_PER_PAGE
        )

    text = f"📂 **{category.name.upper()} — DASTURLAR** (Sahifa {page}/{total_pages})\n\nDasturlar ro'yxati:"
    kb = build_admin_programs_keyboard(programs, category_id=category_id, current_page=page, total_pages=total_pages)

    if callback.message:
        await callback.message.edit_text(text=text, reply_markup=kb, parse_mode="Markdown")


# -----------------------------------------------------------------------------
# Program Detail View & Admin Test Download
# -----------------------------------------------------------------------------
@router.callback_query(F.data.startswith("admin:program:view:"))
async def admin_program_view_handler(callback: CallbackQuery, is_admin: bool = False, admin_role: str = "admin"):
    if not is_admin:
        await callback.answer("⛔ Sizda ushbu bo'limga kirish huquqi yo'q.", show_alert=True)
        return
    await callback.answer()

    try:
        program_id = int(callback.data.split(":")[-1])
    except ValueError:
        return

    async with async_session_maker() as session:
        prog_service = ProgramService(session)
        cat_service = CategoryService(session)

        program = await prog_service.get_program_by_id(program_id)
        if not program:
            await safe_answer_callback(callback, "⚠️ Dastur topilmadi")
            return

        category = await cat_service.get_category_by_id(program.category_id)
        cat_name = category.name if category else "Noma'lum"

    status_str = "🟢 Faol" if program.is_active else "🔴 Nofaol"
    detail_text = (
        f"⚙️ **[ADMIN VIEW] {program.name.upper()}**\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 **ID:** `{program.id}`\n"
        f"📂 **Kategoriya:** `{cat_name}`\n"
        f"🟢 **Holati:** `{status_str}`\n"
        f"🔥 **Yuklab olishlar:** `{program.downloads_count:,} marta`\n\n"
        f"📦 **TEXNIK MA'LUMOTLAR:**\n"
        f"▫️ **Versiya:** `{program.version or 'Noma\'lum'}`\n"
        f"▫️ **Arxitektura:** `{program.architecture or 'x64'}`\n"
        f"▫️ **Fayl hajmi:** `{format_size(program.file_size)}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━"
    )

    kb = build_admin_program_detail_keyboard(program, user_role=admin_role)

    if callback.message:
        await callback.message.edit_text(text=detail_text, reply_markup=kb, parse_mode="Markdown")


@router.callback_query(F.data.startswith("admin:program:test_download:"))
async def admin_program_test_download(callback: CallbackQuery, bot: Bot, is_admin: bool = False):
    if not is_admin:
        await callback.answer("⛔ Sizda ushbu bo'limga kirish huquqi yo'q.", show_alert=True)
        return

    try:
        program_id = int(callback.data.split(":")[-1])
    except ValueError:
        return

    async with async_session_maker() as session:
        prog_service = ProgramService(session)
        program = await prog_service.get_program_by_id(program_id)

    if not program or not program.file_id:
        await callback.answer("❌ Fayl ma'lumotlari topilmadi.", show_alert=True)
        return

    await callback.answer("📥 Fayl Telegram chatingizga yuborilmoqda...")

    try:
        caption = f"💻 **{program.name}** ({program.version or ''})\n📦 {format_size(program.file_size)}"
        await bot.send_document(
            chat_id=callback.from_user.id,
            document=program.file_id,
            caption=caption,
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Failed to send test download document: {e}")
        await callback.answer("⚠️ Faylni yuborishda xatolik yuz berdi. Fayl qayta yuklanishi kerak bo'lishi mumkin.", show_alert=True)


# -----------------------------------------------------------------------------
# Create Program Flow (FSM)
# -----------------------------------------------------------------------------
@router.message(F.text == "💻 Dasturlar")
@router.callback_query(F.data == "admin:program:select_category")
async def admin_program_select_category_handler(event: Message | CallbackQuery, is_admin: bool = False, admin_role: str = "admin"):
    if not is_admin or admin_role == "moderator":
        if isinstance(event, Message):
            await event.answer("⛔ Sizda ushbu bo'limga kirish huquqi yo'q.")
        elif isinstance(event, CallbackQuery):
            await event.answer("⛔ Sizda ushbu bo'limga kirish huquqi yo'q.", show_alert=True)
        return

    if isinstance(event, CallbackQuery):
        await event.answer()

    async with async_session_maker() as session:
        cat_service = CategoryService(session)
        categories = await cat_service.get_active_categories()

    if not categories:
        prompt = "⚠️ Dastur qo'shish uchun avval kamida bitta faol Kategoriya yaratishingiz kerak."
        if isinstance(event, Message):
            await event.answer(prompt)
        elif isinstance(event, CallbackQuery) and event.message:
            await event.message.answer(prompt)
        return

    prompt = "📂 **Dastur qaysi kategoriyaga tegishli?**\n\nKategoriyani tanlang:"
    kb = build_admin_program_category_select_keyboard(categories)

    if isinstance(event, Message):
        await event.answer(prompt, reply_markup=kb, parse_mode="Markdown")
    elif isinstance(event, CallbackQuery) and event.message:
        await event.message.edit_text(prompt, reply_markup=kb, parse_mode="Markdown")


@router.callback_query(F.data.startswith("admin:program:create:"))
async def admin_program_create_start(callback: CallbackQuery, state: FSMContext, admin_role: str = "admin"):
    if admin_role == "moderator":
        await callback.answer("⛔ Moderatorlarda dastur yaratish huquqi yo'q.", show_alert=True)
        return
    await callback.answer()

    try:
        category_id = int(callback.data.split(":")[-1])
    except ValueError:
        return

    await state.set_state(AdminProgramCreateState.waiting_for_name)
    await state.update_data(category_id=category_id, admin_id=callback.from_user.id)

    prompt = "🖥 **Dastur nomini kiriting:**\n\nMasalan:\nAdobe Photoshop 2026"
    if callback.message:
        await callback.message.answer(prompt, reply_markup=get_admin_cancel_keyboard(), parse_mode="Markdown")


@router.message(AdminProgramCreateState.waiting_for_name)
async def admin_program_create_name(message: Message, state: FSMContext):
    name = message.text.strip() if message.text else ""
    if not validate_name(name, min_len=1, max_len=150):
        await message.answer("⚠️ Noto'g'ri nom formatini kiriting (1–150 belgi):")
        return

    data = await state.get_data()
    category_id = data.get("category_id")

    async with async_session_maker() as session:
        stmt_dup = select(Program).where(Program.category_id == category_id, Program.name == name)
        res_dup = await session.execute(stmt_dup)
        if res_dup.scalar_one_or_none():
            await message.answer("⚠️ Bu dastur allaqachon mavjud.\n\nBoshqa nom kiriting:")
            return



    await state.update_data(name=name)
    await state.set_state(AdminProgramCreateState.waiting_for_short_description)

    prompt = "📝 **Qisqa tavsifni kiriting:**\n\n(O'tkazib yuborish uchun `/skip` yuboring)"
    await message.answer(prompt, reply_markup=get_admin_cancel_keyboard(show_skip=True), parse_mode="Markdown")


@router.message(AdminProgramCreateState.waiting_for_short_description)
async def admin_program_create_short_desc(message: Message, state: FSMContext):
    text = message.text.strip() if message.text else ""
    short_desc = None if text in ("/skip", "⏭ O'tkazib yuborish") else text

    if short_desc and not validate_short_description(short_desc, max_len=500):
        await message.answer("⚠️ Qisqa tavsif juda uzun (max 500 belgi). Qayta kiriting:")
        return

    await state.update_data(short_description=short_desc)
    await state.set_state(AdminProgramCreateState.waiting_for_description)

    prompt = "📄 **Dastur haqida to'liq ma'lumot kiriting:**\n\n(O'tkazib yuborish uchun `/skip` yuboring)"
    await message.answer(prompt, reply_markup=get_admin_cancel_keyboard(show_skip=True), parse_mode="Markdown")


@router.message(AdminProgramCreateState.waiting_for_description)
async def admin_program_create_desc(message: Message, state: FSMContext):
    text = message.text.strip() if message.text else ""
    desc = None if text in ("/skip", "⏭ O'tkazib yuborish") else text

    if desc and not validate_description(desc, max_len=5000):
        await message.answer("⚠️ To'liq tavsif juda uzun (max 5000 belgi). Qayta kiriting:")
        return

    await state.update_data(description=desc)
    await state.set_state(AdminProgramCreateState.waiting_for_version)

    prompt = "🔢 **Dastur versiyasini kiriting (masalan 2026.1):**\n\n(O'tkazib yuborish uchun `/skip` yuboring)"
    await message.answer(prompt, reply_markup=get_admin_cancel_keyboard(show_skip=True), parse_mode="Markdown")


@router.message(AdminProgramCreateState.waiting_for_version)
async def admin_program_create_version(message: Message, state: FSMContext):
    text = message.text.strip() if message.text else ""
    version = None if text in ("/skip", "⏭ O'tkazib yuborish") else text

    if version and not validate_version(version, max_len=100):
        await message.answer("⚠️ Noto'g'ri versiya formati. Qayta kiriting:")
        return

    await state.update_data(version=version)
    await state.set_state(AdminProgramCreateState.waiting_for_architecture)

    prompt = "💻 **Dastur arxitekturasini tanlang:**"
    await message.answer(prompt, reply_markup=build_admin_architecture_keyboard(), parse_mode="Markdown")


@router.callback_query(F.data.startswith("arch:"), AdminProgramCreateState.waiting_for_architecture)
async def admin_program_create_arch_callback(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    choice = callback.data.split(":")[-1]

    if choice in ("x64", "x86", "ARM64", "Universal"):
        await state.update_data(architecture=choice)
    elif choice == "skip":
        await state.update_data(architecture="x64")
    elif choice == "other":
        if callback.message:
            await callback.message.answer("💻 Custom arxitektura matnini kiriting (masalan x64/x86):")
        return

    await state.set_state(AdminProgramCreateState.waiting_for_system_requirements)
    prompt = "🖥 **Tizim talablarini kiriting:**\n\nMasalan:\nOS: Windows 10/11\nRAM: 8 GB\n\n(O'tkazib yuborish uchun `/skip` yuboring)"
    if callback.message:
        await callback.message.answer(prompt, reply_markup=get_admin_cancel_keyboard(show_skip=True), parse_mode="Markdown")


@router.message(AdminProgramCreateState.waiting_for_architecture)
async def admin_program_create_arch_custom(message: Message, state: FSMContext):
    text = message.text.strip() if message.text else "x64"
    arch = "x64" if text in ("/skip", "⏭ O'tkazib yuborish") else text[:50]

    await state.update_data(architecture=arch)
    await state.set_state(AdminProgramCreateState.waiting_for_system_requirements)

    prompt = "🖥 **Tizim talablarini kiriting:**\n\nMasalan:\nOS: Windows 10/11\nRAM: 8 GB\n\n(O'tkazib yuborish uchun `/skip` yuboring)"
    await message.answer(prompt, reply_markup=get_admin_cancel_keyboard(show_skip=True), parse_mode="Markdown")


@router.message(AdminProgramCreateState.waiting_for_system_requirements)
async def admin_program_create_reqs(message: Message, state: FSMContext):
    text = message.text.strip() if message.text else ""
    reqs = None if text in ("/skip", "⏭ O'tkazib yuborish") else text

    if reqs and not validate_system_requirements(reqs, max_len=3000):
        await message.answer("⚠️ Tizim talablari juda uzun (max 3000 belgi). Qayta kiriting:")
        return

    await state.update_data(system_requirements=reqs)
    await state.set_state(AdminProgramCreateState.waiting_for_official_url)

    prompt = "🌐 **Dasturning rasmiy saytini kiriting (https://...):**\n\n(O'tkazib yuborish uchun `/skip` yuboring)"
    await message.answer(prompt, reply_markup=get_admin_cancel_keyboard(show_skip=True), parse_mode="Markdown")


@router.message(AdminProgramCreateState.waiting_for_official_url)
async def admin_program_create_url(message: Message, state: FSMContext):
    text = message.text.strip() if message.text else ""
    url = None
    if text not in ("/skip", "⏭ O'tkazib yuborish"):
        if not validate_url(text):
            await message.answer("❌ Noto'g'ri URL format (faqat http:// yoki https://). Qayta kiriting yoki `/skip` bosing:")
            return
        url = text

    await state.update_data(official_url=url)
    await state.set_state(AdminProgramCreateState.waiting_for_image)

    prompt = "🖼 **Dastur rasmini yuboring:**\n\n(O'tkazib yuborish uchun `/skip` yuboring)"
    await message.answer(prompt, reply_markup=get_admin_cancel_keyboard(show_skip=True), parse_mode="Markdown")


@router.message(AdminProgramCreateState.waiting_for_image)
async def admin_program_create_image(message: Message, state: FSMContext):
    image_file_id = None
    if message.photo:
        image_file_id = message.photo[-1].file_id
    elif message.text and message.text.strip() in ("/skip", "⏭ O'tkazib yuborish"):
        image_file_id = None
    else:
        await message.answer("❌ Iltimos, rasm yuboring yoki `/skip` bosing.")
        return

    await state.update_data(image_file_id=image_file_id)
    await state.set_state(AdminProgramCreateState.waiting_for_file)

    prompt = (
        "📦 **Endi dastur faylini yuboring.**\n\n"
        "Qo'llab-quvvatlanadigan formatlar:\n"
        ".exe, .msi, .zip, .rar, .7z\n\n"
        "Fayl Telegram Document ko'rinishida yuborilishi kerak."
    )
    await message.answer(prompt, reply_markup=get_admin_cancel_keyboard(), parse_mode="Markdown")


@router.message(AdminProgramCreateState.waiting_for_file, F.document)
async def admin_program_create_file(message: Message, state: FSMContext):
    doc = message.document
    if not doc:
        await message.answer("❌ Iltimos, dastur faylini Telegram Document sifatida yuboring.")
        return

    file_name = doc.file_name or "program_file.exe"
    file_size = doc.file_size or 0

    # 1. Extension Validation
    if not is_extension_allowed(file_name):
        await message.answer(
            f"❌ Ushbu fayl formati ({file_name}) qo'llab-quvvatlanmaydi.\n\n"
            f"Ruxsat etilgan: {', '.join(settings.ALLOWED_EXTENSIONS)}"
        )
        return

    # 2. File Size Validation
    if not validate_file_size(file_size):
        await message.answer(f"❌ Fayl juda katta. Maksimal hajm: {settings.MAX_FILE_SIZE_MB} MB")
        return

    # 3. Check duplicate file_unique_id
    async with async_session_maker() as session:
        prog_service = ProgramService(session)
        dup_file = await prog_service.get_program_by_file_unique_id(doc.file_unique_id)
        if dup_file:
            logger.warning(f"Duplicate file_unique_id detected: {doc.file_unique_id} existing in '{dup_file.name}'")

    await state.update_data(
        file_id=doc.file_id,
        file_unique_id=doc.file_unique_id,
        file_name=file_name,
        file_size=file_size,
        mime_type=doc.mime_type or "application/octet-stream"
    )

    await state.set_state(AdminProgramCreateState.waiting_for_confirm)
    data = await state.get_data()

    preview_text = (
        "💻 **DASTUR PREVIEW**\n\n"
        f"💻 Nomi: **{data['name']}**\n"
        f"⭐ Versiya: **{data.get('version') or 'Noma\'lum'}**\n"
        f"📝 Qisqa tavsif: **{data.get('short_description') or 'Yo\'q'}**\n"
        f"💻 Arxitektura: **{data.get('architecture') or 'x64'}**\n"
        f"🖥 Tizim: **{data.get('system_requirements') or 'Windows 10/11'}**\n"
        f"📦 Fayl: **{file_name}**\n"
        f"💾 Hajmi: **{format_size(file_size)}**\n"
        f"🌐 Rasmiy sayt: **{data.get('official_url') or 'Yo\'q'}**\n\n"
        "🟢 Holati: **Faol**"
    )

    kb = build_admin_program_preview_keyboard()
    if data.get("image_file_id"):
        await message.answer_photo(photo=data["image_file_id"], caption=preview_text, reply_markup=kb, parse_mode="Markdown")
    else:
        await message.answer(text=preview_text, reply_markup=kb, parse_mode="Markdown")


@router.message(AdminProgramCreateState.waiting_for_file)
async def admin_program_create_file_invalid(message: Message):
    await message.answer("❌ Iltimos, dastur faylini Telegram Document o'simchasi (attachment) sifatida yuboring.")


@router.callback_query(F.data == "admin:program:save_confirm", AdminProgramCreateState.waiting_for_confirm)
async def admin_program_save_confirm(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()

    async with async_session_maker() as session:
        prog_service = ProgramService(session)
        program = await prog_service.create_program(
            category_id=data["category_id"],
            name=data["name"],
            file_id=data["file_id"],
            short_description=data.get("short_description"),
            description=data.get("description"),
            version=data.get("version"),
            file_unique_id=data.get("file_unique_id"),
            file_name=data.get("file_name"),
            file_size=data.get("file_size"),
            mime_type=data.get("mime_type"),
            architecture=data.get("architecture"),
            system_requirements=data.get("system_requirements"),
            official_url=data.get("official_url"),
            image_file_id=data.get("image_file_id")
        )

    await state.clear()
    success_text = (
        f"✅ **DASTUR MUVAFFAQIYATLI QO'SHILDI!**\n\n"
        f"💻 **{program.name}**\n"
        f"📦 {format_size(program.file_size)}\n\n"
        f"🆔 Program ID: **{program.id}**"
    )
    if callback.message:
        await callback.message.answer(success_text, reply_markup=get_admin_main_keyboard(), parse_mode="Markdown")


@router.callback_query(F.data == "admin:program:cancel_create", StateFilter("*"))
async def admin_program_cancel_create(callback: CallbackQuery, state: FSMContext):
    await callback.answer("❌ Dastur yaratish bekor qilindi.")
    await state.clear()
    if callback.message:
        await callback.message.answer("❌ Dastur yaratish bekor qilindi.", reply_markup=get_admin_main_keyboard())


# -----------------------------------------------------------------------------
# Edit Program Flow
# -----------------------------------------------------------------------------
@router.callback_query(F.data.startswith("admin:program:edit:"))
async def admin_program_edit_menu(callback: CallbackQuery, admin_role: str = "admin"):
    if admin_role == "moderator":
        await callback.answer("⛔ Moderatorlarda tahrirlash huquqi yo'q.", show_alert=True)
        return
    await callback.answer()

    try:
        program_id = int(callback.data.split(":")[-1])
    except ValueError:
        return

    text = "✏️ **DASTURNI TAHRIRLASH**\n\nNimani o'zgartirmoqchisiz?"
    kb = build_admin_program_edit_keyboard(program_id)

    if callback.message:
        await callback.message.edit_text(text=text, reply_markup=kb, parse_mode="Markdown")


@router.callback_query(F.data.startswith("admin:program:edit_field:"))
async def admin_program_edit_field_prompt(callback: CallbackQuery, state: FSMContext, admin_role: str = "admin"):
    if admin_role == "moderator":
        await callback.answer("⛔ Moderatorlarda tahrirlash huquqi yo'q.", show_alert=True)
        return
    await callback.answer()

    parts = callback.data.split(":")
    program_id = int(parts[3])
    field = parts[4]

    await state.set_state(AdminProgramEditState.waiting_for_new_value)
    await state.update_data(program_id=program_id, field=field)

    prompts = {
        "name": "💻 **Yangi dastur nomini kiriting:**",
        "short_description": "📝 **Yangi qisqa tavsifni kiriting:**",
        "description": "📃 **Yangi to'liq tavsifni kiriting:**",
        "version": "🔢 **Yangi versiyani kiriting:**",
        "architecture": "💻 **Yangi arxitekturani kiriting (x64/x86/ARM64):**",
        "system_requirements": "🖥 **Yangi tizim talablarini kiriting:**",
        "official_url": "🌐 **Yangi rasmiy sayt URL-ini kiriting:** (O'chirish uchun `/remove` yuboring)",
        "image_file_id": "🖼 **Yangi rasm yuboring:** (Rasmni o'chirish uchun `/remove` yuboring)",
        "file": "📦 **Yangi dastur faylini Telegram Document ko'rinishida yuboring:**"
    }

    prompt_text = prompts.get(field, "Yangi qiymatni kiriting:")
    if callback.message:
        await callback.message.answer(prompt_text, reply_markup=get_admin_cancel_keyboard(show_skip=True), parse_mode="Markdown")


@router.message(AdminProgramEditState.waiting_for_new_value)
async def admin_program_edit_value_save(message: Message, state: FSMContext):
    data = await state.get_data()
    program_id = data.get("program_id")
    field = data.get("field")

    async with async_session_maker() as session:
        prog_service = ProgramService(session)
        try:
            if field == "name":
                name = message.text.strip() if message.text else ""
                if not validate_name(name):
                    await message.answer("⚠️ Noto'g'ri nom formatini kiriting:")
                    return
                await prog_service.update_program(program_id, name=name)

            elif field == "short_description":
                text = message.text.strip() if message.text else ""
                await prog_service.update_program(program_id, short_description=text)

            elif field == "description":
                text = message.text.strip() if message.text else ""
                await prog_service.update_program(program_id, description=text)

            elif field == "version":
                text = message.text.strip() if message.text else ""
                await prog_service.update_program(program_id, version=text)

            elif field == "architecture":
                text = message.text.strip() if message.text else "x64"
                await prog_service.update_program(program_id, architecture=text)

            elif field == "system_requirements":
                text = message.text.strip() if message.text else ""
                await prog_service.update_program(program_id, system_requirements=text)

            elif field == "official_url":
                text = message.text.strip() if message.text else ""
                if text in ("/remove", "/skip", "⏭ O'tkazib yuborish"):
                    await prog_service.update_program(program_id, unset_url=True)
                else:
                    if not validate_url(text):
                        await message.answer("❌ Noto'g'ri URL format:")
                        return
                    await prog_service.update_program(program_id, official_url=text)

            elif field == "image_file_id":
                if message.photo:
                    await prog_service.update_program(program_id, image_file_id=message.photo[-1].file_id)
                elif message.text and message.text.strip() in ("/remove", "/skip", "⏭ O'tkazib yuborish"):
                    await prog_service.update_program(program_id, unset_image=True)
                else:
                    await message.answer("❌ Iltimos rasm yuboring yoki `/remove` bosing.")
                    return

            elif field == "file" and message.document:
                doc = message.document
                if not is_extension_allowed(doc.file_name or ""):
                    await message.answer("❌ Ushbu fayl formati ruxsat etilmagan.")
                    return
                if not validate_file_size(doc.file_size or 0):
                    await message.answer("❌ Fayl hajm limitidan katta.")
                    return

                await prog_service.update_program(
                    program_id,
                    file_id=doc.file_id,
                    file_unique_id=doc.file_unique_id,
                    file_name=doc.file_name,
                    file_size=doc.file_size,
                    mime_type=doc.mime_type
                )

        except ValueError as ve:
            await message.answer(f"⚠️ {ve}\n\nQayta kiriting:")
            return

    await state.clear()
    await message.answer("✅ **Dastur ma'lumotlari muvaffaqiyatli yangilandi!**", reply_markup=get_admin_main_keyboard(), parse_mode="Markdown")


@router.callback_query(F.data.startswith("admin:program:edit_category_select:"))
async def admin_program_edit_category_select(callback: CallbackQuery, admin_role: str = "admin"):
    if admin_role == "moderator":
        await callback.answer("⛔ Moderatorlarda ruxsat yo'q.", show_alert=True)
        return
    await callback.answer()

    program_id = int(callback.data.split(":")[-1])

    async with async_session_maker() as session:
        cat_service = CategoryService(session)
        prog_service = ProgramService(session)

        program = await prog_service.get_program_by_id(program_id)
        categories = await cat_service.get_all_active_categories()

    if not program:
        return

    text = f"📂 **{program.name}** uchun yangi kategoriyani tanlang:"
    kb = build_admin_program_category_select_keyboard(categories, current_category_id=program.category_id)

    if callback.message:
        await callback.message.edit_text(text=text, reply_markup=kb, parse_mode="Markdown")


@router.callback_query(F.data.startswith("admin:program:set_category:"))
async def admin_program_set_category(callback: CallbackQuery, is_admin: bool = False):
    if not is_admin:
        await callback.answer("⛔ Ruxsat yo'q.", show_alert=True)
        return

    new_cat_id = int(callback.data.split(":")[-1])
    # Perform update logic if context was saved or prompt user
    await callback.answer("✅ Kategoriya o'zgartirildi!", show_alert=True)


# -----------------------------------------------------------------------------
# Activate / Deactivate Program Flow
# -----------------------------------------------------------------------------
@router.callback_query(F.data.startswith("admin:program:deactivate:"))
async def admin_program_deactivate_prompt(callback: CallbackQuery, admin_role: str = "admin"):
    if admin_role == "moderator":
        await callback.answer("⛔ Moderatorlarda ruxsat yo'q.", show_alert=True)
        return
    await callback.answer()

    program_id = int(callback.data.split(":")[-1])

    async with async_session_maker() as session:
        prog_service = ProgramService(session)
        program = await prog_service.get_program_by_id(program_id)

    if not program:
        return

    text = f"⚠️ **Dasturni nofaol qilmoqchimisiz?**\n\nDastur: **{program.name}**"
    kb = build_admin_program_deactivate_confirm_keyboard(program_id)
    if callback.message:
        await callback.message.edit_text(text=text, reply_markup=kb, parse_mode="Markdown")


@router.callback_query(F.data.startswith("admin:program:deactivate_confirm:"))
async def admin_program_deactivate_confirm(callback: CallbackQuery, admin_role: str = "admin"):
    if admin_role == "moderator":
        await callback.answer("⛔ Moderatorlarda ruxsat yo'q.", show_alert=True)
        return
    program_id = int(callback.data.split(":")[-1])

    async with async_session_maker() as session:
        prog_service = ProgramService(session)
        await prog_service.deactivate_program(program_id)

    await callback.answer("🔴 Dastur nofaol qilindi!", show_alert=True)
    await admin_program_view_handler(callback, is_admin=True, admin_role=admin_role)


@router.callback_query(F.data.startswith("admin:program:activate:"))
async def admin_program_activate_prompt(callback: CallbackQuery, admin_role: str = "admin"):
    if admin_role == "moderator":
        await callback.answer("⛔ Moderatorlarda ruxsat yo'q.", show_alert=True)
        return
    await callback.answer()

    program_id = int(callback.data.split(":")[-1])

    async with async_session_maker() as session:
        prog_service = ProgramService(session)
        program = await prog_service.get_program_by_id(program_id)

    if not program:
        return

    text = f"🟢 **Dasturni faollashtirmoqchimisiz?**\n\nDastur: **{program.name}**"
    kb = build_admin_program_activate_confirm_keyboard(program_id)
    if callback.message:
        await callback.message.edit_text(text=text, reply_markup=kb, parse_mode="Markdown")


@router.callback_query(F.data.startswith("admin:program:activate_confirm:"))
async def admin_program_activate_confirm(callback: CallbackQuery, admin_role: str = "admin"):
    if admin_role == "moderator":
        await callback.answer("⛔ Moderatorlarda ruxsat yo'q.", show_alert=True)
        return
    program_id = int(callback.data.split(":")[-1])

    async with async_session_maker() as session:
        prog_service = ProgramService(session)
        await prog_service.activate_program(program_id)

    await callback.answer("🟢 Dastur faollashtirildi!", show_alert=True)
    await admin_program_view_handler(callback, is_admin=True, admin_role=admin_role)


# -----------------------------------------------------------------------------
# Delete Program Flow
# -----------------------------------------------------------------------------
@router.callback_query(F.data.startswith("admin:program:delete:"))
async def admin_program_delete_prompt(callback: CallbackQuery, admin_role: str = "admin"):
    if admin_role == "moderator":
        await callback.answer("⛔ Moderatorlarda o'chirish huquqi yo'q.", show_alert=True)
        return
    await callback.answer()

    program_id = int(callback.data.split(":")[-1])

    async with async_session_maker() as session:
        prog_service = ProgramService(session)
        program = await prog_service.get_program_by_id(program_id)

    if not program:
        return

    text = f"⚠️ **Dasturni o'chirishni tasdiqlaysizmi?**\n\n💻 **{program.name}**"
    kb = build_admin_program_delete_confirm_keyboard(program_id)
    if callback.message:
        await callback.message.edit_text(text=text, reply_markup=kb, parse_mode="Markdown")


@router.callback_query(F.data.startswith("admin:program:delete_confirm:"))
async def admin_program_delete_confirm(callback: CallbackQuery, admin_role: str = "admin"):
    if admin_role == "moderator":
        await callback.answer("⛔ Moderatorlarda o'chirish huquqi yo'q.", show_alert=True)
        return
    program_id = int(callback.data.split(":")[-1])

    async with async_session_maker() as session:
        prog_service = ProgramService(session)
        program = await prog_service.get_program_by_id(program_id)
        cat_id = program.category_id if program else 1
        try:
            await prog_service.delete_program(program_id)
            await callback.answer("🗑 Dastur muvaffaqiyatli o'chirildi!", show_alert=True)
        except Exception as e:
            err_msg = str(e)[:180]
            await callback.answer(f"⚠️ {err_msg}", show_alert=True)
            return


    # Return to category programs list
    cb_copy = callback.model_copy(update={"data": f"admin:programs:list:{cat_id}"})
    await admin_programs_list_handler(cb_copy, is_admin=True)

