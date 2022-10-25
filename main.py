import argparse
import asyncio
import logging
from typing import List, Optional
from mistakes import MISTAKES
from storage import Storage

from http_client import Client
from tg import Tg
from utils import init_logger
from ads_handler import filter_users_by_ads, filter_new_ads, parse_ads_from_http

logger = logging.getLogger(__name__)


def main(argv: Optional[List[str]] = None):
    init_logger()

    parser = argparse.ArgumentParser()
    parser.add_argument('--disable', nargs='*', default=[])
    parser.add_argument('--migrate-only', action='store_true')
    parser.add_argument('--upload-db-only', action='store_true')
    args = parser.parse_args(argv)

    storage = Storage()
    if args.migrate_only:
        return
    http_client = Client()
    tg = Tg()

    saved_ads = storage.get_saved_ads()
    parsed_ads = parse_ads_from_http(http_client, args.disable)
    new_ads = filter_new_ads(saved_ads, parsed_ads)
    http_client.enrich_new_ads(new_ads)
    storage.upsert_new_ads(new_ads)
    if args.upload_db_only:
        return

    # do not send ads, if storage was empty
    new_ads = {k: v for k, v in new_ads.items() if saved_ads.get(k)}

    users_ad_params = storage.get_users_ad_params()
    users_by_ads = filter_users_by_ads(users_ad_params, new_ads)
    users_settings = storage.get_users_settings()
    asyncio.run(tg.send_ads(users_by_ads, new_ads, users_settings))


if __name__ == '__main__':
    main()
