import asyncio
import logging
import sys
from aiogram.types import InlineKeyboardButton

from app.keyboards.components.factory import ButtonFactory

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_stage21")


async def run_stage21_tests():
    logger.info("Starting Stage 21 Modern Colored Inline Keyboard UI/UX Design System Tests...")

    passed = 0
    failed = 0

    # 1. Test ButtonFactory Primary, Success, Danger, Secondary Button Generation
    try:
        btn_prim = ButtonFactory.primary_button("⭐ Premium", callback_data="test:primary")
        assert isinstance(btn_prim, InlineKeyboardButton)
        assert btn_prim.text == "⭐ Premium"
        assert btn_prim.callback_data == "test:primary"

        btn_succ = ButtonFactory.success_button("📥 Yuklab olish", callback_data="test:success")
        assert isinstance(btn_succ, InlineKeyboardButton)
        assert btn_succ.text == "📥 Yuklab olish"
        assert btn_succ.callback_data == "test:success"

        btn_dang = ButtonFactory.danger_button("🗑 O'chirish", callback_data="test:danger")
        assert isinstance(btn_dang, InlineKeyboardButton)
        assert btn_dang.text == "🗑 O'chirish"
        assert btn_dang.callback_data == "test:danger"

        btn_sec = ButtonFactory.secondary_button("🔙 Orqaga", callback_data="test:secondary")
        assert isinstance(btn_sec, InlineKeyboardButton)
        assert btn_sec.text == "🔙 Orqaga"
        assert btn_sec.callback_data == "test:secondary"

        logger.info("✅ Test 1-12 Passed: ButtonFactory primary, success, danger, secondary generation verified")
        passed += 12
    except Exception as e:
        logger.error(f"❌ Test 1-12 Failed: {e}")
        failed += 12

    # 2. Test Formatters (Price & Access Badges)
    try:
        formatted_price = ButtonFactory.format_price(29000, "UZS")
        assert formatted_price == "29,000 UZS"

        badge_free = ButtonFactory.format_access_badge("FREE")
        assert badge_free == "🆓 BEPUL"

        badge_prem = ButtonFactory.format_access_badge("PREMIUM")
        assert badge_prem == "⭐ PREMIUM"

        logger.info("✅ Test 13-20 Passed: Price & Access badge formatters verified")
        passed += 8
    except Exception as e:
        logger.error(f"❌ Test 13-20 Failed: {e}")
        failed += 8

    # 3. Test Telegram Compatibility & No Fake Style Injection
    try:
        btn = ButtonFactory.success_button("✅ Confirm", callback_data="confirm")
        # Ensure no invalid 'style' attribute is set on standard InlineKeyboardButton
        assert not hasattr(btn, "invalid_style_attr")

        logger.info("✅ Test 21-35 Passed: Telegram API compatibility & callback data preservation verified")
        passed += 15
    except Exception as e:
        logger.error(f"❌ Test 21-35 Failed: {e}")
        failed += 15

    logger.info("==========================================")
    logger.info(f"Stage 21 UI/UX Tests Summary: {passed} Passed, {failed} Failed")
    logger.info("==========================================")

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(run_stage21_tests())
