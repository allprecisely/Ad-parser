from dataclasses import dataclass
import os

from dotenv import load_dotenv

# COMMON SETTINGS
load_dotenv()
ADDITIONAL_APPARTMENTS_CHAT = os.environ['ADDITIONAL_APPARTMENTS_CHAT']
ADDITIONAL_SELF_CHAT = os.environ['ADDITIONAL_SELF_CHAT']
STORAGE_CHAT_ID = os.environ['STORAGE_CHAT_ID']
STORAGE_CHAT_PREFIX = 'GII bot storage '
TOKEN = os.environ['TOKEN']

TEMPLATE_DESCRIPTION = '''{name}
price: {price}{price_lowered}
date: {date}{distance_text}{description}

'''
DISABLE_NOTIFICATIONS = os.getenv('DISABLE_NOTIFICATIONS') == 'True'
DAYS_TO_EXPIRE = 14
DEBUG = os.getenv('DEBUG') == 'True'

### BAZARAKI
BAZARAKI_URL = 'https://www.bazaraki.com'
CATEGORY_APPARTMENTS = 'appartments'
CATEGORY_MOTORBIKES = 'motorbikes'

MAX_DISTANCE = {
    CATEGORY_APPARTMENTS: 5,
    CATEGORY_MOTORBIKES: None,
}

## Appartments
DISTANCE_TEXT = '\ndistance to office: {:.1f} km'
OFFICE_POINT = float(os.environ['OFFICE_POINT_LATITUDE']), float(
    os.environ['OFFICE_POINT_LONGITUDE']
)
CHAT_ID_APPARTMENTS = os.environ['CHAT_ID_APPARTAMENTS']
BAZARAKI_CATEGORY_APPARTMENTS = 'real-estate-to-rent/houses'
BAZARAKI_CATEGORY_APPARTMENTS2 = 'real-estate-to-rent/apartments-flats'
BAZARAKI_CATEGORY_API_APPARTMENTS = 'api/items/adverts-geometry'
APPARTMENT_MAX_PRICE=1800

# filters
DEFAULT_FURNISHING = {
    1: 'Fully Furnished',
    1: 'Semi-Furnished',
}
DEFAULT_RUBRIC=681
DEFAULT_SINGLE_DISTRICT = 'lemesos-district-limassol'

## Motorbikes
CHAT_ID_MOTORBIKES = os.environ['CHAT_ID_MOTORBIKES']
BAZARAKI_CATEGORY_MOTORBIKES = 'car-motorbikes-boats-and-parts/motorbikes'
RAW_FILTER_MOTORBIKES = '?ordering=newest&price_min=1500'
