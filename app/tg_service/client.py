import asyncio
from json import JSONDecodeError
from logging import getLogger
from typing import TYPE_CHECKING, Literal, Optional, Type, Union

from httpx import AsyncClient, RequestError, Response
from pydantic import ValidationError

from app.tg_service.api import TGAPI
from app.utils import custom_urljoin

from ..core.config import POLLER_REQUEST_TIMEOUT
from .schemas import RequestSchema, ResponseSchema, TGUpdateSchema


if TYPE_CHECKING:
    from app.accountant.base import Accountant

logger = getLogger('tg_client')


class SendTaskSchema:
    method: Type[TGAPI]
    data: RequestSchema
    event: asyncio.Event
    response: Union[dict, ResponseSchema, None]

    def __init__(
        self, method: Type[TGAPI], data: RequestSchema,
    ) -> None:
        self.response = None
        self.method = method
        self.data = data
        self.event = asyncio.Event()


class TelegramClient:
    base_url: str
    manage_tasks: list[asyncio.Task]
    send_tasks: list[asyncio.Task]
    managers_count: int = 1
    senders_count: int = 1
    is_running: bool = False
    listen_task: asyncio.Task = None
    manage_queue: asyncio.Queue = None
    send_queue: asyncio.Queue = None
    offset: int = 0
    _sleep_for: int = 5

    accountant: 'Accountant' = None

    def __init__(self, base_url: str, managers_count: int = 1, senders_count: int = 1):
        self.base_url = base_url
        self.manage_tasks = []
        self.send_tasks = []
        self.managers_count = managers_count
        self.senders_count = senders_count

    async def start(self):
        self.manage_queue = asyncio.Queue()
        self.send_queue = asyncio.Queue()
        self.is_running = True
        self.listen_task = asyncio.create_task(self._listen())
        for _ in range(self.managers_count):
            self.manage_tasks.append(asyncio.create_task(self._manage_updates()))
        for _ in range(self.senders_count):
            self.send_tasks.append(asyncio.create_task(self._send_messages()))

    async def stop(self):
        self.is_running = False
        await self.listen_task
        await self.manage_queue.join()
        await self.send_queue.join()
        for _ in self.manage_tasks:
            await self.manage_queue.put(None)
        for _ in self.send_tasks:
            await self.send_queue.put(None)
        for task in self.manage_tasks:
            await task
        for task in self.send_tasks:
            await task

    async def send(self, method: Type[TGAPI], data: RequestSchema) -> SendTaskSchema:
        """Send request to Telegram API."""
        task = SendTaskSchema(method=method, data=data)
        await self.send_queue.put(task)
        return task

    async def _listen(self):
        url = self._make_url('getUpdates')
        while self.is_running:
            json = {'offset': self.offset, 'timeout': POLLER_REQUEST_TIMEOUT}
            response_dict = await self._request(url=url, json=json)
            logger.debug('response dict %s', response_dict)
            if response_dict and response_dict.get('ok'):
                for result in response_dict.get('result', []):
                    update_id = result.get('update_id')
                    self.offset = update_id + 1 if update_id else self.offset
                    try:
                        update = TGUpdateSchema.model_validate(result)
                        await self.manage_queue.put(update.message or update.callback_query)
                    except Exception as error:
                        # TODO: bot report
                        logger.error('response_validation-E %s', error)
                        await asyncio.sleep(self._sleep_for)
            else:
                logger.error('response_dict %s', response_dict)
                await asyncio.sleep(self._sleep_for)

    async def _send(self, send_task: SendTaskSchema):
        params = dict(url=self._make_url(send_task.method.name))
        payload_key = 'data' if getattr(send_task.data, 'is_form', False) else 'json'
        params[payload_key] = send_task.data.model_dump(
            exclude_none=True, exclude={'files', 'is_form'})
        if getattr(send_task.data, 'files', None):
            params['files'] = send_task.data.files.model_dump()
        response = await self._request(**params)
        if send_task.method.response_schema:
            try:
                validated = send_task.method.response_schema.model_validate(response)
            except ValidationError as error:
                logger.error('response_validation-E %s', error)
            else:
                send_task.response = validated
        send_task.event.set()

    async def _manage_updates(self):
        while self.is_running or not self.manage_queue.empty():
            try:
                if message := await self.manage_queue.get():
                    await self.accountant.process_message(message)
            except Exception as error:
                logger.exception(error)
            finally:
                self.manage_queue.task_done()

    async def _send_messages(self):
        while self.is_running or not self.send_queue.empty():
            try:
                if send_task := await self.send_queue.get():
                    await self._send(send_task)
            except Exception as error:
                logger.exception(error)
            finally:
                self.send_queue.task_done()
                await asyncio.sleep(0.2)

    def _make_url(self, method: str):
        return custom_urljoin(self.base_url, method)

    async def _request(
        self,
        *,
        url: str,
        method: Literal['GET', 'POST'] = 'POST',
        headers: Optional[dict] = None,
        json: Optional[dict] = None,
        data: Optional[dict] = None,
        files: Optional[dict] = None,
        timeout: int = POLLER_REQUEST_TIMEOUT * 2,
    ) -> Response:
        files = files or {}
        logger.debug(
            'request %s %s json: %s form: %s files: %s',
            method, url, json, data, files.keys(),
        )
        try:
            async with AsyncClient() as client:
                response = await client.request(method=method, url=url, timeout=timeout,
                                                headers=headers, json=json, data=data,
                                                files=files)
                content = response.json()
                logger.debug('response %s %s', response.status_code, content)
                if response.status_code != 200:
                    logger.error('request-E %s %s', response.status_code, content)
                return content
        except RequestError as error:
            logger.error('request-E %s %s', error.__class__, error)
        except JSONDecodeError as error:
            logger.error('json_decode-E %s %s', error, response.content)
