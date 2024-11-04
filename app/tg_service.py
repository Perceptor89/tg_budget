import asyncio
import typing
from json import JSONDecodeError
from logging import getLogger

from httpx import AsyncClient, RequestError, Response
from pydantic import ValidationError

from .core.config import POLLER_REQUEST_TIMEOUT, TG_TOKEN
from .schemas.telegram import TGUpdateSchema

if typing.TYPE_CHECKING:
    from app.budget import Accountant

logger = getLogger('tg_client')


class TelegramClient:
    _is_listening: bool = False
    _listen_task: asyncio.Task = None
    _manage_task: asyncio.Task = None
    _updates_queue: asyncio.Queue = None
    _offset: int = 0
    accountant: 'Accountant' = None

    async def start(self):
        self._updates_queue = asyncio.Queue()
        self._is_listening = True
        self._listen_task = asyncio.create_task(self._listen())
        self._manage_task = asyncio.create_task(self._manage_updates())

    async def stop(self):
        self._is_listening = False
        await self._listen_task
        await self._updates_queue.join()
        await self._updates_queue.put(None)
        await self._manage_task

    async def _listen(self):
        url = self._make_url('getUpdates')
        while self._is_listening:
            params = {'offset': self._offset, 'timeout': POLLER_REQUEST_TIMEOUT}
            response_dict = await self._request(url=url, json_params=params)
            logger.debug('response dict %s', response_dict)
            if response_dict and response_dict.get('ok'):
                for result in response_dict.get('result', []):
                    update_id = result.get('update_id')
                    self._offset = update_id + 1 if update_id else self._offset
                    try:
                        update = TGUpdateSchema.model_validate(result)
                        await self._updates_queue.put(update.message)
                    except ValidationError as error:
                        # TODO: bot report
                        logger.error('response validation %s', error)
            else:
                logger.error('response_dict %s', response_dict)

    async def _manage_updates(self):
        while self._is_listening or not self._updates_queue.empty():
            try:
                if message := await self._updates_queue.get():
                    await self.accountant.process_message(message)
            except Exception as error:
                logger.exception(error)
            finally:
                self._updates_queue.task_done()

    def _make_url(self, method: str):
        return f'https://api.telegram.org/bot{TG_TOKEN}/{method}'

    async def _request(
        self,
        *,
        url: str,
        method: str = 'GET',
        headers: dict = None,
        json_params: dict = None,
        form_data: dict = None,
    ) -> Response:
        logger.debug('request %s %s json: %s form: %s', method, url, json_params, form_data)
        request_params = dict(method=method, url=url, timeout=POLLER_REQUEST_TIMEOUT * 2)
        if json_params:
            request_params['json'] = json_params
        if form_data:
            request_params['data'] = form_data
        try:
            async with AsyncClient() as client:
                response = await client.request(**request_params)
                content = response.json()
                return content
        except RequestError as error:
            logger.error('request %s %s', error.__class__, error)
        except JSONDecodeError as error:
            logger.error('json %s %s', error, response.content)
