from app.core.config import LOGGER_CONFIG as DICT_CONFIG
from app.core.config import REDIS_URL
from .base import QueueName


__all__ = ['DICT_CONFIG', 'REDIS_URL', 'QUEUES']


QUEUES = [name.value for name in list(QueueName)]
