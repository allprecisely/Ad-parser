import logging
import os
import time
from typing import Dict

import requests

from model import Bazaraki
from settings import *
from utils import run_with_retries
import distance_counter

CHAT_ID_APPARTMENTS = os.environ['CHAT_ID_APPARTAMENTS']
MAX_PRICE = 1800
API_FILTER_APPARTMENTS = (
    '?rubric=681&c=1133&ordering=newest&q=&attrs__furnishing=1&attrs__furnishing=2&'
    'attrs__area_min=30&city_districts=5738&city_districts=5008&city_districts=5515&'
    'city_districts=5684&city_districts=5682&city_districts=5688&city_districts=5690&'
    'city_districts=5692&city_districts=5694&city_districts=5696&city_districts=5049&'
    'city_districts=5683&city_districts=5739&city_districts=5687&city_districts=5689&'
    'city_districts=5691&city_districts=5693&city_districts=5695&city_districts=5699&'
    'city_districts=5207&city_districts=5737&city_districts=5593&city_districts=5385&'
    f'city_districts=5731&city_districts=5476&city_districts=5317&price_max={MAX_PRICE}&'
)
RAW_FILTER_APPARTMENTS = (
    'area_min---30/furnishing---1/furnishing---2/'
    f'?type_view=line&ordering=newest&price_max={MAX_PRICE}&city_districts=5738&'
    'city_districts=5008&city_districts=5515&city_districts=5684&city_districts=5682&'
    'city_districts=5688&city_districts=5690&city_districts=5692&city_districts=5694&'
    'city_districts=5696&city_districts=5049&city_districts=5683&city_districts=5739&'
    'city_districts=5687&city_districts=5689&city_districts=5691&city_districts=5693&'
    'city_districts=5695&city_districts=5699&city_districts=5207&city_districts=5737&'
    'city_districts=5593&city_districts=5385&city_districts=5731&city_districts=5476&'
    'city_districts=5317'
)
DISTANCE_TEXT = '\ndistance to office: {:.1f} km'
OFFICE_POINT = float(os.environ['OFFICE_POINT_LATITUDE']), float(
    os.environ['OFFICE_POINT_LONGITUDE']
)
BAZARAKI_CATEGORY_APPARTMENTS = 'real-estate/houses-and-villas-rent'
BAZARAKI_CATEGORY_API_APPARTMENTS = 'real-estate/houses-and-villas-rent'
CATEGORY_APPARTMENTS = 'appartments'

CHAT_ID_MOTOBIKES = os.environ['CHAT_ID_MOTOBIKES']
BAZARAKI_CATEGORY_MOTOBIKES = 'car-motorbikes-boats-and-parts/motorbikes'
RAW_FILTER_MOTOBIKES = '?ordering=newest&price_min=1500'
CATEGORY_MOTOBIKES = 'motobikes'
logger = logging.getLogger(__name__)


class AppartmentBazaraki(Bazaraki):
    def get_curr_variants(self) -> Dict[str, str]:
        items = super().get_curr_variants()
        items = {
            k: v
            for k, v in items.items()
            if 'Limassol' in v['areaServed'] and v['price'] <= MAX_PRICE
        }
        try:
            url_api = f'{BAZARIKI_URL}/{BAZARAKI_CATEGORY_API_APPARTMENTS}/{API_FILTER_APPARTMENTS}'
            resp_api = run_with_retries(
                self.bot, requests.get, {'url': url_api}, self.logger
            )
            for i in resp_api.json()['results']:
                if str(i['id']) in items:
                    distance = distance_counter.haversine(OFFICE_POINT, i['geometry'])
                    items[str(i['id'])]['distance'] = DISTANCE_TEXT.format(distance)
        except:
            pass

        return items


def lambda_handler(event, context):
    logger.setLevel(logging.INFO)
    logger.addHandler(logging.StreamHandler())
    logger.info(f'{DEBUG = }')
    handler = AppartmentBazaraki(
        logger,
        f'{BAZARIKI_URL}/{BAZARAKI_CATEGORY_APPARTMENTS}/{RAW_FILTER_APPARTMENTS}',
        CATEGORY_APPARTMENTS,
        CHAT_ID_APPARTMENTS,
    )
    handler.lambda_handler()

    handler = Bazaraki(
        logger,
        f'{BAZARIKI_URL}/{BAZARAKI_CATEGORY_MOTOBIKES}/{RAW_FILTER_MOTOBIKES}',
        CATEGORY_MOTOBIKES,
        CHAT_ID_MOTOBIKES,
    )
    handler.lambda_handler()


if __name__ == '__main__':
    lambda_handler(None, None)
