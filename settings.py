import os

from dotenv import load_dotenv

# COMMON SETTINGS
load_dotenv()
TOKEN = os.environ['TOKEN']
STORAGE_CHAT_ID = os.environ['STORAGE_CHAT_ID']

DAYS_TO_EXPIRE = 14

### BAZARAKI
BAZARAKI_URL = 'https://www.bazaraki.com'

## Appartments
OFFICE_POINT = float(os.environ['OFFICE_POINT_LATITUDE']), float(
    os.environ['OFFICE_POINT_LONGITUDE']
)
APPARTMENT_MAX_PRICE = 1800

# filters
DEFAULT_FURNISHING = {
    1: 'Fully Furnished',
    1: 'Semi-Furnished',
}
DEFAULT_RUBRIC = 681
DEFAULT_SINGLE_DISTRICT = 'lemesos-district-limassol'

## Motorbikes
COMMON_AREA_MIN = 30

CATEGORY_RENT = 'rent'
CATEGORY_MOTORBIKES = 'motorbikes'
CATEGORY_APPARTMENTS = 'appartments'
CATEGORY_HOUSES = 'houses'
CATEGORY_CARS = 'cars'

CITIES = {
    'Limassol': (34.686703, 33.053791),
    'Larnaca': (34.923374, 33.627465),
    'Lefcosia': (35.172729, 33.365156),
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
}

USERS_FIELDS = ('id', 'active', 'created_at', 'updated_at', 'history_asked_at')
USERS_COMMON_FIELDS = (
    'id',
    'cities',
    'price_min',
    'price_max',
    'distance_to_center',
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
    'url',
    'images',
    'announcement_date',
    'created_at',
    'name',
    'price',
    'location',
    'coords',
    'distance_to_center',
    'description',
)
INT_FIELDS = {'year', 'mileage', 'area'}
EVALED_ADS_FIELDS = {'coords', 'images'}
EVALED_USERS_FIELDS = {'word_exceptions', 'types', 'furnishing', 'bedrooms', 'gearbox', 'cities'}

TEMPLATE_DESCRIPTION = '''{name}
price: {price} €
date: {announcement_date}
distance to center: {distance} ({location})
{category_description}

{description}

'''
CATEGORY_TEXT_RENT = 'type: {type}, area: {area} m², bedrooms: {bedrooms}'
CATEGORY_TEXT_MOTORBIKES = (
    'type: {type}, mileage: {mileage} km, engine: {engine}, condition: {condition}'
)
CATEGORY_TEXT_CARS = 'year: {year}, mileage: {mileage} km, gearbox: {gearbox}, fuel: {fuel}, condition: {condition}'

CATEGORIES = {
    CATEGORY_RENT: {
        'name': CATEGORY_RENT,
        'price_max': 2500,
        'path': '',
        'subcategories': [
            {'name': CATEGORY_HOUSES, 'path': 'real-estate-to-rent/houses'},
            {
                'name': CATEGORY_APPARTMENTS,
                'path': 'real-estate-to-rent/apartments-flats',
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
        'path': 'car-motorbikes-boats-and-parts/cars',
        'price_max': 20000,
        'category_fields': ('year', 'gearbox', 'mileage', 'condition', 'fuel'),
        'users_fields': USERS_CARS_FIELDS,
        'description': CATEGORY_TEXT_CARS,
    },
}
