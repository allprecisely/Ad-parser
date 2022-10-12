import argparse
from typing import List, Optional

import telegram
from telegram.utils.request import Request

from custom_logic import send_variants_to_self_group
from model import BazarakiChecker, AppartmentChecker
from settings import *
from utils import Filter, init_logger


def main(argv: Optional[List[str]] = None):
    init_logger()

    parser = argparse.ArgumentParser()
    parser.add_argument('--disable', nargs='*', default=[])
    args = parser.parse_args(argv)

    bot = telegram.Bot(TOKEN, request=Request(connect_timeout=20, read_timeout=20))

    if CATEGORY_APPARTMENTS not in args.disable:
        handler = AppartmentChecker(bot)
        handler.lambda_handler(send_variants_to_self_group)

    if CATEGORY_MOTORBIKES not in args.disable:
        query = Filter(price_min=1500).http_query()
        handler = BazarakiChecker(
            bot,
            f'{BAZARAKI_URL}/{BAZARAKI_CATEGORY_MOTORBIKES}/' + query,
            CATEGORY_MOTORBIKES,
            CHAT_ID_MOTORBIKES,
        )
        handler.lambda_handler(send_variants_to_self_group)


if __name__ == '__main__':
    main()
