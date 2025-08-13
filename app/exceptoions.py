import logging
import functools


logger = logging.getLogger('app')


class AccountantError(Exception):
    """Accountant error."""


def catch_exception(fn):
    """Catch exception decorator."""
    @functools.wraps(fn)
    async def wrapper(*args, **kwargs):
        try:
            return await fn(*args, **kwargs)
        except AccountantError as error:
            logger.error('%s args %s kwargs %s error %s', fn.__name__, args, kwargs, error)
        except Exception as error:
            logger.exception('%s args %s kwargs %s error %s', fn.__name__, args, kwargs, error)
    return wrapper
