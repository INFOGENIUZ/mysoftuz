import random
import string
from datetime import datetime, timezone


def generate_error_id() -> str:
    """
    Generates a unique, trackable Error ID formatted as ERR-YYYYMMDD-XXXXX
    (e.g., ERR-20260808-A7F92).
    """
    now_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    random_suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=5))
    return f"ERR-{now_str}-{random_suffix}"


def get_user_friendly_error_message(is_admin: bool = False, error_id: str = "") -> str:
    """
    Returns safe, sanitized error message for display.
    Guarantees no internal tracebacks, SQL statements, or sensitive credentials are leaked.
    """
    if is_admin:
        return (
            "⚠️ **Operatsiyani bajarib bo'lmadi.**\n\n"
            f"Xatolik ID:\n`{error_id}`\n\n"
            "Tafsilotlar server loglarida saqlandi."
        )

    return (
        "⚠️ **Kutilmagan xatolik yuz berdi.**\n\n"
        "Iltimos, birozdan keyin qayta urinib ko'ring."
    )
