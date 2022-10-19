from collections import defaultdict
import logging
from typing import Any, Dict, List, Set
from mistakes import MISTAKES

from http_client import Client
from settings import *
from utils import ADS_DICT

logger = logging.getLogger(__name__)


def parse_ads_from_http(http_client: Client, disabled: List[str]) -> ADS_DICT:
    ads = {}
    for category_name, category_props in CATEGORIES.items():
        if category_name not in disabled:
            ads[category_name] = http_client.get_updates(category_props)
    return ads


def filter_new_ads(ad_history_ids: Dict[str, Set[str]], ads: ADS_DICT) -> ADS_DICT:
    return {
        category_name: {
            k: v for k, v in ads.get(category_name, {}).items() if k not in ad_history_ids_by_category
        }
        for category_name, ad_history_ids_by_category in ad_history_ids.items()
    }


def filter_ads_by_users(
    users_by_category: Dict[str, List[Dict[str, Any]]], ads: ADS_DICT
) -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
    ads_by_users = defaultdict(lambda: defaultdict(list))
    for category_name, ads in ads.items():
        for ad in ads.values():
            district = ad['location'].split()[0]
            try:
                for user_id, user_props in users_by_category[category_name].items():
                    if filtered_common(
                        user_props, ad, district
                    ) and filtered_by_category(category_name, ad):
                        ads_by_users[category_name][user_id].append(ad)
            except Exception as exc:
                logger.exception(f'Could not filter ad {ad}  Exception: {exc}')
                MISTAKES.append(f'Could not filter ad {ad}  Exception: {exc}')
    return ads_by_users


def filtered_common(user, ad, district) -> bool:
    return (
        user['district'] == district
        and user['distance_to_center'] >= ad['distance_to_center']
        and user.get('price_min', 0)
        <= ad['price']
        <= user.get('price_max', float('inf'))
        and all(
            word.strip() not in ad['name']
            for word in user.get('excluded_words', '').split(',')
        )
    )


def filtered_by_category(user, ad, category_name) -> bool:
    if category_name == CATEGORY_RENT:
        return (
            user.get('area_min', 0)
            <= int(ad['area'].split()[0])
            <= user.get('area_max', float('inf'))
            and user.get('pets', ad['pets']) == ad['pets']
            and ad['furnishing'] in user.get('furnishing', [ad['furnishing']])
            and ad['bedrooms'] in user.get('bedrooms', ad['bedrooms']).split(',')
        )
    elif category_name == CATEGORY_MOTORBIKES:
        return (
            user.get('mileage_min', 0)
            <= int(ad['mileage'].split()[0])
            <= user.get('mileage_max', float('inf'))
        )
    elif category_name == CATEGORY_CARS:
        return (
            user.get('mileage_min', 0)
            <= int(ad['mileage'].split()[0])
            <= user.get('mileage_max', float('inf'))
            and ad['gearbox'] in user.get('gearbox', [ad['gearbox']])
            and user.get('year_min', 0)
            <= int(ad['year'])
            <= user.get('year_max', float('inf'))
            and ad['fuel'] in user.get('fuel', [ad['fuel']])
        )
