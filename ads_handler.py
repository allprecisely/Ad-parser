from collections import defaultdict
import logging
from typing import Any, Dict, List
from mistakes import MISTAKES

from http_client import Client
from settings import *
from utils import ADS_DICT

logger = logging.getLogger(__name__)


def parse_ads_from_http(http_client: Client, disabled: List[str]) -> ADS_DICT:
    ads = {}
    for category, props in CATEGORIES_PROPS.items():
        if category not in disabled:
            ads[category] = http_client.get_updates(props)
    return ads


def filter_new_ads(
    saved_ads: Dict[str, Dict[str, int]], new_ads_from_site: ADS_DICT
) -> ADS_DICT:
    new_ads = {category: {} for category in CATEGORIES_PROPS}
    for category, ads in new_ads_from_site.items():
        for ad_id, props in ads.items():
            if old_price := saved_ads[category].get(ad_id):
                if old_price <= props['price']:
                    continue
                props['lowered'] = f'from {old_price} to {props["price"]}'
            new_ads[category][ad_id] = props

    return new_ads


def filter_users_by_ads(
    users_ad_params: Dict[str, List[Dict[str, Any]]], new_ads: ADS_DICT
) -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
    users_by_ads = {category: defaultdict(list) for category in CATEGORIES_PROPS}
    for category, ads in new_ads.items():
        for ad in ads.values():
            district = ad['location'].split()[0]
            try:
                for user_id, user_props in users_ad_params[category].items():
                    if filtered_common(
                        user_props, ad, district
                    ) and filtered_by_category(category, ad):
                        users_by_ads[category][ad['id']].append(user_id)
            except Exception as exc:
                logger.exception(f'Could not filter ad {ad}  Exception: {exc}')
                MISTAKES.append(f'Could not filter ad {ad}  Exception: {exc}')
    return users_by_ads


def filtered_common(user, ad, district) -> bool:
    return (
        user['district'] == district
        and user['radius'] >= ad['radius']
        and user.get('price_min', 0)
        <= ad['price']
        <= user.get('price_max', float('inf'))
        and all(
            word.strip() not in ad['name']
            for word in user.get('excluded_words', '').split(',')
        )
    )

def filtered_by_category(user, ad, category) -> bool:
    if category == CATEGORY_RENT:
        return (
            user.get('area_min', 0)
            <= int(ad['area'].split()[0])
            <= user.get('area_max', float('inf'))
            and user.get('pets', ad['pets']) == ad['pets']
            and ad['furnishing'] in user.get('furnishing', [ad['furnishing']])
            and ad['bedrooms'] in user.get('bedrooms', ad['bedrooms']).split(',')
        )
    elif category == CATEGORY_MOTORBIKES:
        return (
            user.get('mileage_min', 0)
            <= int(ad['mileage'].split()[0])
            <= user.get('mileage_max', float('inf'))
        )
    elif category == CATEGORY_CARS:
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
