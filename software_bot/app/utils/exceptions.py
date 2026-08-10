class DownloadError(Exception):
    """Base exception for download operation errors."""
    pass


class ProgramNotFoundError(DownloadError):
    """Raised when program is not found in database."""
    pass


class ProgramInactiveError(DownloadError):
    """Raised when target program is deactivated by admin."""
    pass


class FileMissingError(DownloadError):
    """Raised when Telegram file_id is missing or invalid."""
    pass


class UserBlockedError(DownloadError):
    """Raised when user is blocked from downloading."""
    pass


class TelegramDeliveryError(DownloadError):
    """Raised when Telegram API fails to deliver document file."""
    pass
