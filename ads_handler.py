from collections import defaultdict
import logging
from typing import Any, Dict, List
from mistakes import MISTAKES

from http_client import Client
from settings import *
from utils import ADS_DICT

logger = logging.getLogger(__name__)


def filter_ads_from_http(
    http_client: Client, saved_ads: Dict[str, Dict[str, int]], disabled: List[str]
) -> ADS_DICT:
    logger.info('Parsing ads from http')
    ads = {}
    for category, props in CATEGORIES_PROPS.items():
        if category not in disabled:
            ads[category] = http_client.get_updates(props, saved_ads)
    return ads


def filter_users_by_ads(
    users_ad_params: Dict[str, List[Dict[str, Any]]],
    new_ads: ADS_DICT,
    users_settings: Dict[str, Any],
) -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
    logger.info('Filtering users by ads')
    users_by_ads = {category: defaultdict(list) for category in CATEGORIES_PROPS}
    for category, ads in new_ads.items():
        for ad in ads.values():
            district = ad['location'].split()[0]
            try:
                for user_id, user_props in users_ad_params[category].items():
                    short_term = users_settings.get(user_id, {}).get(
                        'show_short_term_rent'
                    )
                    if filtered_common(
                        user_props, ad, district
                    ) and filtered_by_category(category, ad, short_term):
                        users_by_ads[category][ad['id']].append(user_id)
            except Exception as exc:
                logger.exception(f'Could not filter ad {ad}  Exception: {exc}')
                MISTAKES.append(f'Could not filter ad {ad}  Exception: {exc}')
    return users_by_ads


def filtered_common(user, ad, district) -> bool:
    return (
        district in user['cities']
        and user['radius'] >= ad['radius']
        and user.get('price_min', 0)
        <= ad['price']
        <= user.get('price_max', float('inf'))
        and all(
            word.strip() not in ad['name']
            for word in user.get('excluded_words', '').split(',')
        )
    )


def filtered_by_category(user, ad, category, short_term: bool) -> bool:
    if category == CATEGORY_RENT:
        return (
            user.get('area_min', 0)
            <= int(ad['area'].split()[0])
            <= user.get('area_max', float('inf'))
            and user.get('pets', ad['pets']) == ad['pets']
            and ad['furnishing'] in user.get('furnishing', [ad['furnishing']])
            and ad['bedrooms'] in user.get('bedrooms', ad['bedrooms']).split(',')
            and (not ad.get('short_term') or short_term)
        )
    elif category == CATEGORY_MOTORBIKES:
        return user.get('mileage_min', 0) <= int(ad['mileage'].split()[0]) <= user.get(
            'mileage_max', float('inf')
        ) and ad['type'] in user.get('types', ad['type'])
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
