import os
from typing import Any, Dict, List

from dotenv import load_dotenv

# TYPES
# {category: {ad_id: {id: 123, price: 123...}}}
AD_TYPE = Dict[str, Any]
ADS_TYPE = Dict[str, AD_TYPE]
ADS_BY_CATEGORY_TYPE = Dict[str, ADS_TYPE]

# {category: {user_id: {id: uid, area: 30...}}}
USER_PARAMS_TYPE = Dict[str, Any]
USERS_PARAMS_TYPE = Dict[str, USER_PARAMS_TYPE]
USERS_PARAMS_BY_CATEGORY_TYPE = Dict[str, USERS_PARAMS_TYPE]

# {category: {ad_id: {user_id: {id: uid, }}}}

# COMMON SETTINGS
load_dotenv()
TOKEN = os.environ['TOKEN']
STORAGE_CHAT_ID = os.environ['STORAGE_CHAT_ID']
MISTAKES: List[Any] = []

DAYS_TO_EXPIRE = 14

### BAZARAKI
BAZARAKI_URL = 'https://www.bazaraki.com'

## Motorbikes
COMMON_AREA_MIN = 30

CATEGORY_RENT = 'rent'
CATEGORY_MOTORBIKES = 'motorbikes'
CATEGORY_CARS = 'cars'

CITIES = {
    'Limassol': (34.686703, 33.053791),
    'Larnaca': (34.923374, 33.627465),
    'Lefkosia': (35.172729, 33.365156),
    'Paphos': (34.776770, 32.422453),
    'Famagusta': (35.121793, 33.939288),
}
CHECKBOX = {
    'furnishing': ('Fully Furnished', 'Semi-Furnished', 'Unfurnished'),
    'types': ('Moped', 'Others'),
    'gearbox': ('Manual', 'Automatic'),
    'pets': ('only ads with allowed pets',),
    'bedrooms': ('1', '2', '3', '4', '5', 'Studio', '6 and more'),
    'cities': tuple(CITIES),
    'short_term': ('Show short term ads',),
}

USERS_FIELDS = (
    'id',
    'active',
    'show_location',
    'without_sound',
    'ads_without_photo',
    'history_asked_at',
    'created_at',
    'updated_at',
)
USER_FIELDS_TO_SHOW = (
    'show_location',
    'without_sound',
    'ads_without_photo',
)
USERS_COMMON_FIELDS = (
    'id',
    'cities',
    'price_min',
    'price_max',
    'radius',
    'word_exceptions',
)
USERS_RENT_FIELDS = USERS_COMMON_FIELDS + (
    'area_min',
    'area_max',
    'pets',
    'types',
    'parking',
    'furnishing',
    'bedrooms',
    'short_term',
)
USERS_MOTORBIKES_FIELDS = USERS_COMMON_FIELDS + (
    'mileage_min',
    'mileage_max',
    'conditions',
    'types',
)
USERS_CARS_FIELDS = USERS_COMMON_FIELDS + (
    'mileage_min',
    'mileage_max',
    'gearbox',
    'year_min',
    'year_max',
)
AD_COMMON_FIELDS = (
    'id',
    'dt',
    'added_at',
    'name',
    'price',
    'location',
    'coords',
    'radius',
    'description',
    'url',
    'images',
)
INT_FIELDS = {'year', 'mileage', 'area'}
EVALED_ADS_FIELDS = {'coords', 'images'}
EVALED_USERS_FIELDS = {
    'word_exceptions',
    'types',
    'furnishing',
    'bedrooms',
    'gearbox',
    'cities',
    'pets',
    'short_term',
}

TEMPLATE_DESCRIPTION = '''{name}
price: {price} €
date: {dt}
distance to center: {radius} ({location})
{extra}

{description}

'''
CATEGORY_TEXT_RENT = 'type: {type}, area: {area} m², bedrooms: {bedrooms}'
CATEGORY_TEXT_MOTORBIKES = (
    'type: {type}, mileage: {mileage} km, engine: {engine}, condition: {condition}'
)
CATEGORY_TEXT_CARS = 'year: {year}, mileage: {mileage} km, gearbox: {gearbox}, fuel: {fuel}, condition: {condition}'

CATEGORIES_PROPS: Dict[str, Dict[str, Any]] = {
    CATEGORY_RENT: {
        'name': CATEGORY_RENT,
        'price_max': 2500,
        'path': '',
        'subcategories': [
            {'name': 'houses', 'path': 'real-estate-to-rent/houses'},
            {
                'name': 'apartments',
                'path': 'real-estate-to-rent/apartments-flats',
            },
            {
                'name': 'short_term',
                'path': 'real-estate-to-rent/short-term',
            },
        ],
        'custom_filters': {'area_min': COMMON_AREA_MIN},
        'category_fields': (
            'area',
            'pets',
            'type',
            'parking',
            'furnishing',
            'bedrooms',
            'short_term',
        ),
        'users_fields': USERS_RENT_FIELDS,
        'description': CATEGORY_TEXT_RENT,
    },
    CATEGORY_MOTORBIKES: {
        'name': CATEGORY_MOTORBIKES,
        'path': 'car-motorbikes-boats-and-parts/motorbikes',
        'price_max': 12000,
        'category_fields': ('type', 'mileage', 'condition', 'engine'),
        'users_fields': USERS_MOTORBIKES_FIELDS,
        'description': CATEGORY_TEXT_MOTORBIKES,
    },
    CATEGORY_CARS: {
        'name': CATEGORY_CARS,
        'path': 'car-motorbikes-boats-and-parts/cars-trucks-and-vans',
        'price_max': 20000,
        'category_fields': ('year', 'gearbox', 'mileage', 'condition', 'fuel'),
        'users_fields': USERS_CARS_FIELDS,
        'description': CATEGORY_TEXT_CARS,
    },
}
