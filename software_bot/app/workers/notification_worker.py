import logging
import asyncio
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from app.database.models import NotificationJob, User, Program, ProgramVersion, UserNotification
from app.services.telegram_delivery_service import TelegramDeliveryService

logger = logging.getLogger(__name__)


def build_update_notification_keyboard(program_id: int, version_id: int) -> InlineKeyboardMarkup:
    """Builds inline keyboard attached to software update notifications."""
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📥 Yangi versiyani yuklash", callback_data=f"version:download:{version_id}"),
        ],
        [
            InlineKeyboardButton(text="📦 Versiyalar", callback_data=f"version:list:{program_id}"),
            InlineKeyboardButton(text="🔕 Xabarlarni o'chirish", callback_data=f"update:disable:{program_id}")
        ]
    ])
    return kb


class NotificationWorker:
    def __init__(self, session: AsyncSession, bot: Bot, rate_limit_delay: float = 0.05):
        self.session = session
        self.bot = bot
        self.delivery_service = TelegramDeliveryService(bot)
        self.rate_limit_delay = rate_limit_delay

    async def process_pending_jobs(self, batch_size: int = 20) -> int:
        """
        Fetches and processes pending notification jobs from queue.
        Implements rate limiting, retry backoff (up to 3 attempts), and crash recovery.
        Returns count of successfully sent notifications in this run.
        """
        # Crash recovery: reset stale jobs locked in 'processing' for > 5 minutes back to 'pending'
        stale_cutoff = datetime.now(timezone.utc) - timedelta(minutes=5)
        await self.session.execute(
            update(NotificationJob)
            .where(NotificationJob.status == "processing", NotificationJob.created_at < stale_cutoff)
            .values(status="pending")
        )
        await self.session.commit()

        # Claim pending jobs
        stmt = (
            select(NotificationJob)
            .where(NotificationJob.status == "pending", NotificationJob.attempts < 3)
            .order_by(NotificationJob.created_at.asc())
            .limit(batch_size)
        )
        res = await self.session.execute(stmt)
        jobs = list(res.scalars().all())

        if not jobs:
            return 0

        processed_count = 0

        for job in jobs:
            # Lock job status to processing
            job.status = "processing"
            job.attempts += 1
            await self.session.commit()

            # Load details
            u_stmt = select(User).where(User.id == job.user_id)
            user = (await self.session.execute(u_stmt)).scalar_one_or_none()

            p_stmt = select(Program).where(Program.id == job.program_id)
            program = (await self.session.execute(p_stmt)).scalar_one_or_none()

            v_stmt = select(ProgramVersion).where(ProgramVersion.id == job.version_id)
            version = (await self.session.execute(v_stmt)).scalar_one_or_none()

            if not user or not program or not version or user.is_blocked:
                job.status = "cancelled"
                job.last_error = "User blocked or invalid reference"
                await self.session.commit()
                continue

            notif_text = (
                f"🔔 **DASTUR YANGILANDI!**\n\n"
                f"💻 **{program.name.upper()}**\n\n"
                f"🔢 Yangi versiya: **{version.version}**\n"
                f"📝 Yangiliklar:\n{version.release_notes or 'Kichik tuzatishlar va optimallashtirish.'}\n\n"
                "📥 Yangi versiyani yuklab olish uchun quyidagi tugmani bosing."
            )
            kb = build_update_notification_keyboard(program.id, version.id)

            try:
                await self.delivery_service.send_message(
                    chat_id=user.telegram_id,
                    text=notif_text,
                    reply_markup=kb,
                    parse_mode="Markdown"
                )
                job.status = "sent"
                job.sent_at = datetime.now(timezone.utc)
                processed_count += 1

                # Create in-app Notification record
                in_app = UserNotification(
                    user_id=user.id,
                    type="update",
                    program_id=program.id,
                    version_id=version.id,
                    title=f"🔔 {program.name} yangilandi ({version.version})",
                    message=notif_text,
                    is_read=False
                )
                self.session.add(in_app)

            except Exception as send_err:
                err_str = str(send_err)
                logger.warning(f"NotificationWorker job {job.id} failed (attempt {job.attempts}): {err_str}")

                if "blocked" in err_str.lower() or "deactivated" in err_str.lower() or "not found" in err_str.lower():
                    job.status = "failed"
                    job.last_error = f"Permanent failure: {err_str}"
                    user.is_blocked = True
                else:
                    if job.attempts >= 3:
                        job.status = "failed"
                        job.last_error = f"Max retries reached: {err_str}"
                    else:
                        job.status = "pending"
                        job.last_error = f"Temporary failure: {err_str}"

            await self.session.commit()
            await asyncio.sleep(self.rate_limit_delay)

        return processed_count
