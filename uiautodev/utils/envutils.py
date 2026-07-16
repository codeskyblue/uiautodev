import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


def is_enabled(name: str) -> bool:
    return os.getenv(name, "false").lower() in ("true", "1", "on", "yes", "y")


def get_int(name: str) -> Optional[int]:
    value = os.getenv(name)
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        logger.warning("Ignoring environment variable %s=%r: not a valid integer", name, value)
        return None


class Environment:
    UIAUTODEV_MOCK = is_enabled("UIAUTODEV_MOCK")
    UIAUTODEV_U2_PORT = get_int("UIAUTODEV_U2_PORT")
