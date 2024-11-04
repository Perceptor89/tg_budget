from logging.config import dictConfig

from .config import LOGGER_CONFIG


def setup_logger() -> None:
    """Set up logger settings."""
    dictConfig(LOGGER_CONFIG)
