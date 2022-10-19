import argparse
import logging
from typing import List, Optional
from mistakes import MISTAKES
from storage import Storage

from http_client import Client
from tg import Tg
from utils import init_logger
from ads_handler import filter_ads_by_users, filter_new_ads, parse_ads_from_http

logger = logging.getLogger(__name__)


def main(argv: Optional[List[str]] = None):
    init_logger()

    parser = argparse.ArgumentParser()
    parser.add_argument('--disable', nargs='*', default=[])
    parser.add_argument('--migrate-only', action='store_true')
    args = parser.parse_args(argv)

    storage = Storage()
    if args.migrate_only:
        return
    http_client = Client()
    tg = Tg

    parsed_ads = parse_ads_from_http(http_client, args.disable)
    ad_history_ids = storage.get_ad_history_ids()
    new_ads = filter_new_ads(ad_history_ids, parsed_ads)
    http_client.enrich_new_ads(new_ads)
    storage.update_history(new_ads)

    users = storage.get_users()
    ads_by_users = filter_ads_by_users(users, new_ads)
    tg.send_ads(ads_by_users)
    tg.send_mistakes(MISTAKES)


if __name__ == '__main__':
    main()
