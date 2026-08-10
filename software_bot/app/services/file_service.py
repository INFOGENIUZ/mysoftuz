import logging
from typing import Optional, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models import Program

logger = logging.getLogger(__name__)


class FileService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_program_file_metadata(self, program_id: int) -> Optional[Program]:
        """Fetch program file metadata by ID."""
        stmt = select(Program).where(Program.id == program_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def validate_program_downloadable(self, program: Optional[Program]) -> Tuple[bool, str]:
        """
        Validates if a program is active and has a valid Telegram file_id.
        Returns tuple: (is_valid, error_reason_message)
        """
        if not program:
            return False, "⚠️ Dastur topilmadi."
        if not program.is_active:
            return False, "⚠️ Bu dastur hozircha mavjud emas."
        if not program.file_id or len(program.file_id.strip()) < 5:
            return False, "❌ Fayl ma'lumotlari mavjud emas."
        return True, ""

    async def get_telegram_file_id(self, program_id: int) -> Optional[str]:
        """Retrieves Telegram file_id for a program."""
        program = await self.get_program_file_metadata(program_id)
        if program and program.file_id:
            return program.file_id
        return None
