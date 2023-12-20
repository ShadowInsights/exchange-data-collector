from app.config import settings

LOGGING_LEVELS_DICT = {
    "DEBUG": 10,
    "INFO": 20,
    "WARNING": 30,
    "ERROR": 40,
    "CRITICAL": 50,
}


def get_logging_level() -> int:
    literal_logging_level = settings.LOGGING_LEVEL

    return LOGGING_LEVELS_DICT[literal_logging_level]
