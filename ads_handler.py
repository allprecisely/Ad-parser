from collections import defaultdict
import logging
from typing import Any, Dict, List, Optional

from http_client import Client
from settings import *

logger = logging.getLogger(__name__)


def filter_ads_from_http(
    http_client: Client, saved_ads: Dict[str, Dict[str, int]], disabled: List[str]
) -> ADS_BY_CATEGORY_TYPE:
    logger.info('Parsing ads from http')
    ads = {}
    for category, props in CATEGORIES_PROPS.items():
        if category not in disabled:
            ads[category] = http_client.get_updates(props, saved_ads)
    return ads


def filter_users_by_ads(
    users_ad_params: USERS_PARAMS_BY_CATEGORY_TYPE,
    new_ads: ADS_BY_CATEGORY_TYPE,
    users_settings: Any,
) -> Dict[str, Dict[str, List[str]]]:
    logger.info('Filtering users by ads')
    users_by_ads: Dict[str, Dict[str, List[str]]] = {
        category: defaultdict(list) for category in CATEGORIES_PROPS
    }
    for category, ads in new_ads.items():
        for ad in ads.values():
            ad_city = ad['location'].split()[0]
            try:
                for user_id, user_props in users_ad_params[category].items():
                    if (
                        users_settings.get('active')
                        and filtered_common(user_props, ad, ad_city)
                        and filtered_by_category(user_props, ad, category)
                    ):
                        users_by_ads[category][ad['id']].append(user_id)
            except Exception as exc:
                logger.exception(f'Could not filter ad {ad}  Exception: {exc}')
                MISTAKES.append(f'Could not filter ad {ad}  Exception: {exc}')
    return users_by_ads


def filtered_common(user, ad, ad_city) -> bool:
    return (
        ad_city in user['cities']
        and user['radius'] >= ad['radius']
        and _between(user, ad, 'price')
        and all(
            word.strip() not in ad['name']
            for word in user.get('excluded_words', '').split(',')
        )
    )


def filtered_by_category(user, ad, category) -> bool:
    if category == CATEGORY_RENT:
        return (
            _between(user, ad, 'area')
            and _in(user, ad, 'pets')
            and _in(user, ad, 'furnishing')
            and _in(user, ad, 'bedrooms')
            and _in(user, ad, 'short_term')
        )
    elif category == CATEGORY_MOTORBIKES:
        return _between(user, ad, 'mileage') and _eq(user, ad, 'type', 'types')
    elif category == CATEGORY_CARS:
        return (
            _between(user, ad, 'mileage')
            and _between(user, ad, 'year')
            and _in(user, ad, 'gearbox')
            and _in(user, ad, 'fuel')
            and _in(user, ad, 'type', 'types')
        )
    else:
        return False


def _between(user, ad, prop: str, u_prop: Optional[str] = None) -> bool:
    u_prop = u_prop or prop
    if not (a := ad.get(prop)):
        return True
    return user.get(f'{u_prop}_min', 0) <= a <= user.get(f'{u_prop}_max', float('inf'))


def _in(user, ad, prop: str, u_prop: Optional[str] = None) -> bool:
    return ((a := ad.get(prop)) and (u := user.get(u_prop or prop))) or a in u
