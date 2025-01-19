import os 


def is_enabled(name: str) -> bool:
    return os.getenv(name, "false").lower() in ("true", "1", "on", "yes", "y")


class Environment:
    UIAUTODEV_MOCK = is_enabled("UIAUTODEV_MOCK")
