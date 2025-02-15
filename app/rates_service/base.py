from abc import ABC, abstractmethod
import datetime
from logging import getLogger
from typing import Literal, Optional, Union

from httpx import AsyncClient, ConnectError, ConnectTimeout, Timeout
import xml.etree.ElementTree as ET


logger = getLogger('rates')

KNOWN_ERRORS = (
    ValueError,
    ConnectError,
    ConnectTimeout,
)


class _BaseSeeker(ABC):
    base_url: str
    is_json_response: bool = True

    @staticmethod
    async def _request(
        url: str,
        method: Literal['GET'] = 'GET',
        headers: Optional[dict] = None,
        json: Optional[dict] = None,
        is_json_response: bool = True,
    ) -> tuple[int, Union[dict, str]]:
        timeout = Timeout(timeout=15)
        async with AsyncClient(timeout=timeout) as client:
            logger.debug('request %s %s %s %s', method, url, headers, json)
            response = await client.request(method=method, url=url, json=json, headers=headers)
            status = response.status_code
            content = response.json() if is_json_response else response.text
            logger.debug('response %s %s', status, content)
            return status, content

    @abstractmethod
    def extract_rate(self, content: dict) -> float:
        pass

    @abstractmethod
    def make_url(self, date: datetime.date) -> str:
        pass


class ARSSeeker(_BaseSeeker):
    base_url = 'https://api.bluelytics.com.ar/v2/historical?day={date}'

    def make_url(self, date: datetime.date) -> str:
        return self.base_url.format(date=date.isoformat())

    def extract_rate(self, content: dict) -> float:
        usd_to_ars = content.get('blue', {}).get('value_buy')
        return usd_to_ars


class RUBSeeker(_BaseSeeker):
    base_url = 'https://www.cbr.ru/scripts/XML_daily.asp?date_req={date}'
    is_json_response = False

    def make_url(self, date: datetime.date) -> str:
        return self.base_url.format(date=date.strftime('%d.%m.%Y'))

    def extract_rate(self, content: str) -> Optional[float]:
        xml = ET.fromstring(content)

        for valute in xml.findall('Valute'):
            char_code = valute.find('CharCode').text
            if char_code == 'USD':
                return round(float(valute.find('Value').text.replace(',', '.')), 6)


class RateSeeker:
    mapper = {
        'ARS': ARSSeeker,
        'RUB': RUBSeeker,
    }

    async def get_rate(self, valute_code: str, date: datetime.date) -> Optional[float]:
        seeker: _BaseSeeker = self.mapper.get(valute_code)
        if not seeker:
            raise ValueError(f'no seeker implemented for valute {valute_code}')

        seeker = seeker()

        url = seeker.make_url(date)
        status, content = await seeker._request(url=url, is_json_response=seeker.is_json_response)

        if status != 200:
            raise ValueError(f'response status {status} for valute {valute_code}')

        return seeker.extract_rate(content)
