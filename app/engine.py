from logging import getLogger

from app.accountant.base import Accountant
from app.core import config
from app.db_service.repository import DatabaseAccessor
from app.scheduler import scheduler
from app.tg_service.editor import TGMessageEditor

from .core.logger import setup_logger
from .tg_service import TelegramClient


setup_logger()
logger = getLogger('app')


class Engine:
    db: DatabaseAccessor
    tg_client: TelegramClient
    editor: TGMessageEditor
    accountant: Accountant

    def __init__(self):
        self.tg_client = TelegramClient(config.TG_BASE_URL)
        self.db = DatabaseAccessor()
        self.editor = TGMessageEditor()
        self.accountant = Accountant(db=self.db, tg_client=self.tg_client, editor=self.editor)
        self.tg_client.accountant = self.accountant
        self.accountant.tg_client = self.tg_client

    async def start_app(self):
        logger.info('Start app')
        scheduler.start()
        await self.tg_client.start()

    async def stop_app(self):
        logger.info('Stop app')
        scheduler.shutdown(wait=True)
        await self.tg_client.stop()
