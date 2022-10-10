import logging
import os

from model import Bazaraki

from settings import *

CHAT_ID = os.environ['CHAT_ID_MOTOBIKES']
BAZARAKI_CATEGORY = 'car-motorbikes-boats-and-parts/motorbikes'
RAW_FILTER = '?ordering=newest&price_min=1500'
CATEGORY = 'motobikes'
logger = logging.getLogger(__name__)


def lambda_handler(event, context):
    logger.setLevel(logging.INFO)
    logger.addHandler(logging.StreamHandler())
    url = f'{BAZARIKI_URL}/{BAZARAKI_CATEGORY}/{RAW_FILTER}'
    handler = Bazaraki(logger, url, CATEGORY, CHAT_ID)
    handler.lambda_handler()


if __name__ == '__main__':
    lambda_handler(None, None)
