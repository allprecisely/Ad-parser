from dataclasses import dataclass, field
from typing import List, Optional
import logging
import time

import telegram

from settings import *

logger = logging.getLogger(__name__)


@dataclass
class Filter:
    price_min: Optional[int] = None
    price_max: Optional[int] = None
    single_district: Optional[str] = None
    districts: Optional[List[int]] = None

    custom_filters: List[str] = field(default_factory=list)

    def query(self) -> str:
        filters = ['?ordering=newest']
        if self.single_district:
            # !! not handled for api query
            filters = [f'{self.single_district}/?ordering=newest']
        if self.price_min:
            filters.append(f'price_min={self.price_min}')
        if self.price_max:
            filters.append(f'price_max={self.price_max}')
        if self.districts:
            assert not self.single_district
            filters.extend(
                f'city_districts={district_id}' for district_id in self.districts
            )

        return '&'.join(filters)

    def http_query(self) -> str:
        filters = []
        for _filter in self.custom_filters:
            value = getattr(self, _filter, None)
            if value:
                values = value if isinstance(value, list) else [value]
                filters.extend((f'{_filter}---{v}' for v in values))

        query = '/'.join(filters)
        return (f'{query}/' if query else '') + self.query()

    def api_query(self) -> str:
        filters = []
        for _filter in self.custom_filters:
            value = getattr(self, _filter, None)
            if value:
                values = [value] if isinstance(value, str) else value
                filters.extend((f'attrs__{_filter}={v}' for v in values))

        return self.query() + '&'.join(filters)


@dataclass
class AppartmentFilter(Filter):
    rubric: Optional[int] = None
    area_min: Optional[int] = None
    area_max: Optional[int] = None
    furnishing: Optional[List[int]] = None
    custom_filters: List[str] = field(default_factory=lambda: ['rubric', 'area_min', 'area_max', 'furnishing'])


def run_with_retries(bot, f, kwargs, delay: int = 1):
    for i in range(3):
        try:
            return f(**kwargs)
        except telegram.error.RetryAfter as exc:
            logger.info(f'again reload {exc.retry_after}')
            time.sleep(exc.retry_after)
        except Exception as exc:
            if i == 2:
                logger.exception('s-th went wrong, %s', f.__name__)
            time.sleep(delay)
    else:
        try:
            bot.send_message(text=f'{f.__name__}: {exc}', chat_id=STORAGE_CHAT_ID)
        except:
            pass


def init_logger(level: str = 'INFO'):
    logger = logging.getLogger('')
    logger.setLevel(level)
    logger.addHandler(logging.StreamHandler())
    
    logger.info('Logger initiated. DEBUG = %s', DEBUG)
