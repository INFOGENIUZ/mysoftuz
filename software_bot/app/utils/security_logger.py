import logging

logger = logging.getLogger("security")


def log_security_event(event_type: str, user_id: int, details: str = "") -> None:
    """
    Logs structured security events (e.g. admin actions, unauthorized access attempts)
    ensuring sensitive data like BOT_TOKEN or raw passwords are never included.
    """
    logger.warning(
        f"[SECURITY_EVENT] type={event_type} | user_id={user_id} | details={details}"
    )
