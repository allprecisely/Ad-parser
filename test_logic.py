import pytest

from ads_handler import filter_users_by_ads
from settings import *

# fmt: off
OK_ADS = {'rent': {'1': {'id': '1', 'price': 100, 'location': 'Limassol s-th', 'radius': 10, 'name': 'SUPER FLAT', 'images': ['url']}}}
OK_SETTINGS = {'id': '1', 'active': '1'}
EMPTY_FILTERED = {'rent': {}, 'cars': {}, 'motorbikes': {}}


@pytest.mark.parametrize(
    'users_ad_params,new_ads,users_settings,filtered',
    [
        (
            # all ok
            {'rent': {'1': {'id': '1', 'cities': ['Limassol'], 'radius': 10, 'furnishing': 'Fully Furnished'}}},
            OK_ADS,
            OK_SETTINGS,
            {'rent': {'1': ['1']}, 'cars': {}, 'motorbikes': {}},
        ),
        (
            # not active
            {'rent': {'1': {'id': '1', 'cities': ['Limassol'], 'radius': 10}}},
            OK_ADS,
            {'id': '1', 'active': 0},
            EMPTY_FILTERED,
        ),
        (
            # without images
            {'rent': {'1': {'id': '1', 'cities': ['Limassol'], 'radius': 10}}},
            {'rent': {'1': {'id': '1', 'price': 100, 'location': 'Limassol s-th', 'radius': 10, 'name': 'SUPER FLAT', 'images': []}}},
            OK_SETTINGS,
            EMPTY_FILTERED,
        ),
        (
            # settings without images
            {'rent': {'1': {'id': '1', 'cities': ['Limassol'], 'radius': 10}}},
            {'rent': {'1': {'id': '1', 'price': 100, 'location': 'Limassol s-th', 'radius': 10, 'name': 'SUPER FLAT', 'images': []}}},
            {'id': '1', 'active': '1', 'ads_without_photo': 1},
            {'rent': {'1': ['1']}, 'cars': {}, 'motorbikes': {}},
        ),
        (
            # high price
            {'rent': {'1': {'id': '1', 'cities': ['Limassol'], 'radius': 10, 'price_max': 0}}},
            OK_ADS,
            OK_SETTINGS,
            EMPTY_FILTERED,
        ),
        (
            # low price
            {'rent': {'1': {'id': '1', 'cities': ['Limassol'], 'radius': 10, 'price_min': 9999}}},
            OK_ADS,
            OK_SETTINGS,
            EMPTY_FILTERED,
        ),
        (
            # wrong cities
            {'rent': {'1': {'id': '1', 'cities': ['Lefkosia', 'Famagusta'], 'radius': 10}}},
            OK_ADS,
            OK_SETTINGS,
            EMPTY_FILTERED,
        ),
        (
            # pets not allowed
            {'rent': {'1': {'id': '1', 'cities': ['Limassol'], 'radius': 10, 'pets': ['Allowed']}}},
            {'rent': {'1': {'id': '1', 'price': 100, 'location': 'Limassol s-th', 'radius': 10, 'name': 'SUPER FLAT', 'images': ['url'], 'pets': 'Not allowed'}}},
            OK_SETTINGS,
            EMPTY_FILTERED,
        ),
        (
            # not in radius
            {'rent': {'1': {'id': '1', 'cities': ['Limassol'], 'radius': 0}}},
            OK_ADS,
            OK_SETTINGS,
            EMPTY_FILTERED,
        ),
        (
            # excluded words match
            {'rent': {'1': {'id': '1', 'cities': ['Limassol'], 'radius': 10, 'excluded_words': ['test', 'apart']}}},
            {'rent': {'1': {'id': '1', 'price': 100, 'location': 'Limassol s-th', 'radius': 10, 'name': 'SUPER TesT FLAT', 'images': ['url']}}},
            OK_SETTINGS,
            EMPTY_FILTERED,
        ),
        (
            # excluded words not match
            {'rent': {'1': {'id': '1', 'cities': ['Limassol'], 'radius': 10, 'excluded_words': ['test', 'apart']}}},
            OK_ADS,
            OK_SETTINGS,
            {'rent': {'1': ['1']}, 'cars': {}, 'motorbikes': {}},
        ),
        (
            # area low
            {'rent': {'1': {'id': '1', 'cities': ['Limassol'], 'radius': 10, 'area_min': 30}}},
            {'rent': {'1': {'id': '1', 'price': 100, 'location': 'Limassol s-th', 'radius': 10, 'name': 'SUPER FLAT', 'images': ['url'], 'area': 25}}},
            OK_SETTINGS,
            EMPTY_FILTERED,
        ),
        (
            # area ok
            {'rent': {'1': {'id': '1', 'cities': ['Limassol'], 'radius': 10, 'area_min': 30, 'area_max': 40}}},
            {'rent': {'1': {'id': '1', 'price': 100, 'location': 'Limassol s-th', 'radius': 10, 'name': 'SUPER FLAT', 'images': ['url'], 'area': 35}}},
            OK_SETTINGS,
            {'rent': {'1': ['1']}, 'cars': {}, 'motorbikes': {}},
        ),
        (
            # short term allowed
            {'rent': {'1': {'id': '1', 'cities': ['Limassol'], 'radius': 10, 'short_term': ['bla']}}},
            {'rent': {'1': {'id': '1', 'price': 100, 'location': 'Limassol s-th', 'radius': 10, 'name': 'SUPER FLAT', 'images': ['url'], 'short_term': True}}},
            OK_SETTINGS,
            {'rent': {'1': ['1']}, 'cars': {}, 'motorbikes': {}},
        ),
        (
            # short term not allowed
            {'rent': {'1': {'id': '1', 'cities': ['Limassol'], 'radius': 10}}},
            {'rent': {'1': {'id': '1', 'price': 100, 'location': 'Limassol s-th', 'radius': 10, 'name': 'SUPER FLAT', 'images': ['url'], 'short_term': True}}},
            OK_SETTINGS,
            EMPTY_FILTERED,
        ),
        (
            # bedrooms match
            {'rent': {'1': {'id': '1', 'cities': ['Limassol'], 'radius': 10, 'bedrooms': ['1', '2', '3']}}},
            {'rent': {'1': {'id': '1', 'price': 100, 'location': 'Limassol s-th', 'radius': 10, 'name': 'SUPER FLAT', 'images': ['url'], 'bedrooms': '2'}}},
            OK_SETTINGS,
            {'rent': {'1': ['1']}, 'cars': {}, 'motorbikes': {}},
        ),
        (
            # bedrooms not match
            {'rent': {'1': {'id': '1', 'cities': ['Limassol'], 'radius': 10, 'bedrooms': ['1', '2', '3']}}},
            {'rent': {'1': {'id': '1', 'price': 100, 'location': 'Limassol s-th', 'radius': 10, 'name': 'SUPER FLAT', 'images': ['url'], 'bedrooms': 'apart'}}},
            OK_SETTINGS,
            EMPTY_FILTERED,
        ),
        (
            # also cars
            {
                'rent': {'1': {'id': '1', 'cities': ['Limassol'], 'radius': 10}},
                'cars': {'1': {'id': '1', 'cities': ['Limassol'], 'radius': 10}},
            },
            {
                'rent': OK_ADS['rent'],
                'cars': OK_ADS['rent'],
            },
            OK_SETTINGS,
            {'rent': {'1': ['1']}, 'cars': {'1': ['1']}, 'motorbikes': {}},
        ),
        (
            # several users
            {
                'rent': {
                    '1': {'id': '1', 'cities': ['Limassol'], 'radius': 10},
                    '2': {'id': '2', 'cities': ['Limassol'], 'radius': 10},
                },
            },
            {
                'rent': {
                    '1': {'id': '1', 'price': 100, 'location': 'Limassol s-th', 'radius': 10, 'name': 'SUPER FLAT', 'images': ['url']},
                    '2': {'id': '2', 'price': 100, 'location': 'Limassol s-th', 'radius': 10, 'name': 'SUPER FLAT', 'images': ['url']},
                },
            },
            OK_SETTINGS,
            {'rent': {'1': ['1', '2'], '2': ['1', '2']}, 'cars': {}, 'motorbikes': {}},
        ),
    ],
    ids = [
        'all ok', 'not active', 'without images', 'settings without images',
        'high price', 'low price', 'wrong cities', 'pets not allowed', 'not in radius',
        'excluded words match', 'excluded words not match', 'area low', 'area ok',
        'short term allowed', 'short term not allowed', 'bedrooms match',
        'bedrooms not match', 'also cars', 'several users'
    ]
)
# fmt: on
def test_filter_users_by_ads(
    users_ad_params: USERS_PARAMS_BY_CATEGORY_TYPE,
    new_ads: ADS_BY_CATEGORY_TYPE,
    users_settings: Any,
    filtered: Dict[str, Dict[str, List[str]]],
):
    assert filter_users_by_ads(users_ad_params, new_ads, users_settings) == filtered
