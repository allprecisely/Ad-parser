from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import logging

from settings import *

logger = logging.getLogger(__name__)

# {category_name: {ad_id: {**ad_props_by_category}}}
ADS_DICT = Dict[str, Dict[str, Dict[str, Any]]]

# {category_name: {user_id: {**user_props_by_category}}}
USERS_DICT = Dict[str, Dict[str, Dict[str, Any]]]


@dataclass
class HttpFilter:
    price_min: Optional[int] = None
    price_max: Optional[int] = None
    single_district: Optional[str] = None
    districts: Optional[List[int]] = None

    custom_filters: Dict[str, Any] = field(default_factory=dict)

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
        for filter_name, value in self.custom_filters.items():
            values = value if isinstance(value, list) else [value]
            filters.extend((f'{filter_name}---{v}' for v in values))

        query = '/'.join(filters)
        return (f'{query}/' if query else '') + self.query()


def init_logger(level: str = 'INFO'):
    logger = logging.getLogger('')
    logger.setLevel(level)
    logger.addHandler(logging.StreamHandler())
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    
    logger.info('Logger initiated. Level = %s', level)
