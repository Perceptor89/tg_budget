import os
import pathlib
from environs import Env


env = Env()

# Time constants
ONE_SECOND = 1
ONE_MINUTE = ONE_SECOND * 60
ONE_HOUR = ONE_MINUTE * 60
ONE_DAY = ONE_HOUR * 24
ONE_WEEK = ONE_DAY * 7
ONE_YEAR = ONE_DAY * 365

# directories
APP_DIR = pathlib.Path(__file__).absolute().parent.parent
PROJECT_ROOT_DIR = APP_DIR.parent
LOG_PATH_DIR = PROJECT_ROOT_DIR / 'logs'
env.read_env(path=PROJECT_ROOT_DIR / '.env', override=True)

# database
with env.prefixed('POSTGRES_'):
    user = env('USER')
    password = env('PASSWORD')
    host = env('HOST', 'localhost')
    port = env.int('PORT', 5432)
    name = env('DB')
DATABASE_URL = f'postgresql+asyncpg://{user}:{password}@{host}:{port}/{name}'

REDIS_HOST = env('REDIS_HOST', 'localhost')
REDIS_PORT = env.int('REDIS_PORT', 6379)
REDIS_DB = env.int('REDIS_DB', 0)
REDIS_URL = f'redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}'

# telegram
TG_TOKEN = env('TG_TOKEN')
TG_BASE_URL = f'https://api.telegram.org/bot{TG_TOKEN}'
POLLER_REQUEST_TIMEOUT = env.int('POLLER_REQUEST_TIMEOUT', 60)

LOGGER_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'main_formatter': {
            'format': (
                '%(levelname)1.1s %(asctime)s %(name)s - %(message).2000s'
                ' - %(filename)s - %(funcName)s - %(lineno)s'
            ),
            'datefmt': "%d.%m %H:%M:%S",
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'main_formatter',
        },
        'fileAppHandler': {
            'level': 'DEBUG',
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'filename': (LOG_PATH_DIR / 'app.log').as_posix(),
            'formatter': 'main_formatter',
            'when': 'midnight',
            'backupCount': 5,
        },
    },
    'loggers': {
        'app': {
            'handlers': ['fileAppHandler', 'console'],
            'level': 'DEBUG',
        },
        'tg_client': {
            'handlers': ['fileAppHandler', 'console'],
            'level': 'DEBUG',
        },
        'db': {
            'handlers': ['fileAppHandler', 'console'],
            'level': 'DEBUG',
        },
        'rq': {
            'handlers': ['fileAppHandler', 'console'],
            'level': 'DEBUG',
        }
    },
}
