from logging import getLogger

from app.budget import Accountant

from .core.logger import setup_logger
from .tg_service import TelegramClient


setup_logger()
logger = getLogger('app')


class Engine:
    tg_client: TelegramClient
    accountant: Accountant

    def __init__(self):
        self.tg_client = TelegramClient()
        self.accountant = Accountant()
        self.tg_client.accountant, self.accountant.tg_client = self.accountant, self.tg_client

    async def start_app(self):
        logger.info('Start app')
        await self.tg_client.start()

    async def stop_app(self):
        logger.info('Stop app')
        await self.tg_client.stop()
