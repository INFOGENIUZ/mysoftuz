import re
from typing import Optional
from app.config import settings

URL_REGEX = re.compile(
    r"^https?://"  # http:// or https://
    r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|"  # domain
    r"localhost|"  # localhost
    r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # ip
    r"(?::\d+)?"  # optional port
    r"(?:/?|[/?]\S+)$", re.IGNORECASE
)

SLUG_REGEX = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def validate_name(name: Optional[str], min_len: int = 1, max_len: int = 150) -> bool:
    """Validates program or category name length."""
    if not name or not isinstance(name, str):
        return False
    clean = name.strip()
    return min_len <= len(clean) <= max_len


def validate_short_description(text: Optional[str], max_len: int = 500) -> bool:
    """Validates short description length."""
    if text is None:
        return True
    return len(text.strip()) <= max_len


def validate_description(text: Optional[str], max_len: int = 5000) -> bool:
    """Validates full description length."""
    if text is None:
        return True
    return len(text.strip()) <= max_len


def validate_version(version: Optional[str], max_len: int = 100) -> bool:
    """Validates version string length and characters."""
    if not version:
        return True
    clean = version.strip()
    if len(clean) > max_len:
        return False
    return bool(re.match(r"^[vV]?\d+(\.\d+)*(-[a-zA-Z0-9.]+)?$", clean))


def validate_system_requirements(text: Optional[str], max_len: int = 3000) -> bool:
    """Validates system requirements length."""
    if text is None:
        return True
    return len(text.strip()) <= max_len


def validate_url(url: Optional[str]) -> bool:
    """Validates if string is a valid http/https URL."""
    if not url or not isinstance(url, str):
        return False
    return bool(URL_REGEX.match(url.strip()))


def validate_file_size(size_bytes: Optional[int]) -> bool:
    """Validates if file size is non-negative and within MAX_FILE_SIZE_MB."""
    if size_bytes is None:
        return True
    if size_bytes < 0:
        return False
    max_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
    return size_bytes <= max_bytes


def is_file_size_allowed(size_bytes: Optional[int]) -> bool:
    """Alias for validate_file_size."""
    return validate_file_size(size_bytes)


def validate_telegram_file_id(file_id: Optional[str]) -> bool:
    """Validates non-empty Telegram file_id."""
    if not file_id or not isinstance(file_id, str):
        return False
    return len(file_id.strip()) > 5


def validate_slug(slug: Optional[str]) -> bool:
    """Validates url-friendly slug format."""
    if not slug or not isinstance(slug, str):
        return False
    return bool(SLUG_REGEX.match(slug.strip()))


def is_extension_allowed(file_name: Optional[str]) -> bool:
    """Validates file extension against config ALLOWED_EXTENSIONS."""
    if not file_name or not isinstance(file_name, str):
        return True
    clean_name = file_name.strip().lower()
    for ext in settings.ALLOWED_EXTENSIONS:
        if clean_name.endswith(ext):
            return True
    return False


def validate_version_format(version: str) -> bool:
    return validate_version(version)


def sanitize_text(text: str) -> str:
    return text.strip() if text else ""
