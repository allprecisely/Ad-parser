import io
import json
import logging
from datetime import datetime, timedelta
import time
from typing import Any, Callable, Dict, List, Optional

import requests
import telegram

import distance_counter
from parse_html import (
    parse_bazaraki,
    parse_site_for_images_and_coords,
)
from settings import *
from utils import AppartmentFilter, run_with_retries


logger = logging.getLogger(__name__)


class Checker:
    def __init__(self, bot: telegram.Bot, category: str, chat_id: str) -> None:
        self.bot = bot
        storage_chat = run_with_retries(
            self.bot, self.bot.get_chat, dict(chat_id=STORAGE_CHAT_ID), logger
        )
        if not storage_chat:
            logger.error('No storage chat')
            exit(0)
        self.last_storage_msg_id = storage_chat.title[len(STORAGE_CHAT_PREFIX) :]

        self.category = category
        self.chat_id = chat_id

    def lambda_handler(self, send_also_to: Callable) -> None:
        logger.info(f'Start handling {self.category}')
        curr_variants = self.get_curr_variants()
        prev_variants = self.get_prev_variants()
        new_variants = self.get_new_variants(prev_variants, curr_variants)

        self.send_new_variants(new_variants, send_also_to)
        if new_variants:
            self.save_new_variants(prev_variants, new_variants)

    def get_curr_variants(self) -> Dict[str, str]:
        raise TimeoutError('Not overloaded function')

    def get_prev_variants(self) -> Dict[str, str]:
        if self.last_storage_msg_id == 'new':
            return {}

        msg = run_with_retries(
            self.bot,
            self.bot.edit_message_caption,
            dict(
                caption=str(datetime.now()),
                chat_id=STORAGE_CHAT_ID,
                message_id=self.last_storage_msg_id,
            ),
        )
        if msg:
            _file = msg.document.get_file()
            content = run_with_retries(self.bot, _file.download_as_bytearray, {})
            if content:
                prev_variants = json.loads(content)
                ts = (datetime.now() - timedelta(days=DAYS_TO_EXPIRE)).timestamp()
                prev_variants[self.category] = {
                    k: v
                    for k, v in prev_variants.get(self.category, {}).items()
                    if not v.get('ts') or v['ts'] > ts
                }
                return prev_variants
        logger.error('Could not get previous variants')
        exit(0)

    def get_new_variants(
        self, prev_variants: Dict[str, str], curr_variants: Dict[str, str]
    ) -> Dict[str, str]:
        new_variants = {}
        prev_variants = prev_variants.get(self.category, {})
        for k, v in curr_variants.items():
            if k in prev_variants:
                if v['price'] < prev_variants[k]['price']:
                    new_variants[k] = {**v, 'price_lowered': ' (lowered)'}
                continue
            time.sleep(1)
            response = run_with_retries(self.bot, requests.get, {'url': v['url']}, 5)
            parsed_ad = self.parse_site_for_images_and_coords(response)
            if MAX_DISTANCE.get(self.category) and parsed_ad.get('coords'):
                v['distance'] = distance_counter.haversine(OFFICE_POINT, parsed_ad['coords'])
            v['images'] = parsed_ad.get('images', v['images'])
            new_variants[k] = v
        logger.info(f'new/updated variants {new_variants.keys()}')
        return new_variants

    def send_new_variants(
        self,
        new_variants: Dict[str, str],
        send_also_to: Optional[Callable] = None,
    ) -> None:
        if self.last_storage_msg_id == 'new' or DEBUG or len(new_variants) > 10:
            logger.info(
                'send_new_variants skip: %s, %s', len(new_variants), new_variants.keys()
            )
            return
        for k, v in reversed(new_variants.items()):
            distance_text = ''
            if MAX_DISTANCE.get(self.category) and v.get('distance'):
                if v['distance'] > MAX_DISTANCE[self.category]:
                    continue
                distance_text = DISTANCE_TEXT.format(v['distance'])
            image_with_caption = telegram.InputMediaPhoto(
                media=v['images'][0],
                caption=TEMPLATE_DESCRIPTION.format(**v, distance_text=distance_text),
                caption_entities=[
                    telegram.MessageEntity(
                        type='text_link',
                        offset=0,
                        url=v['url'],
                        length=len(v['name']),
                    )
                ],
            )
            other_images = [
                telegram.InputMediaPhoto(img) for img in v['images'][1:5]
            ]
            media_group = [image_with_caption] + other_images
            msgs = run_with_retries(
                self.bot,
                self.bot.send_media_group,
                dict(
                    media=media_group,
                    chat_id=self.chat_id,
                    disable_notification=DISABLE_NOTIFICATIONS,
                ),
            )
            if msgs:
                new_variants[k]['msg_id'] = str(msgs[0].message_id)
                if send_also_to:
                    send_also_to(self.bot, v, media_group)
            else:
                logger.error(f'{k} variant was not loaded')

    def parse_site_for_images_and_coords(
        self, resp_images: requests.Response
    ) -> List[str]:
        return []

    def save_new_variants(
        self, prev_variants: Dict[str, str], new_variants: Dict[str, str]
    ) -> None:
        for v in new_variants.values():
            del v['description']
            del v['images']
        prev_variants[self.category] = {
            **prev_variants.get(self.category, {}),
            **new_variants,
        }
        if DEBUG:
            logger.info(
                'send_document: %s',
                {k: list(v) for k, v in prev_variants.items()},
            )
            return

        with io.StringIO() as _file:
            json.dump(prev_variants, _file, indent=4)
            _file.seek(0)
            msg = run_with_retries(
                self.bot,
                self.bot.send_document,
                dict(
                    document=_file,
                    filename='results.json',
                    caption=str(datetime.now()),
                    chat_id=STORAGE_CHAT_ID,
                    disable_notification=True,
                ),
            )
        if self.last_storage_msg_id != 'new':
            run_with_retries(
                self.bot,
                self.bot.delete_message,
                dict(chat_id=STORAGE_CHAT_ID, message_id=int(self.last_storage_msg_id)),
            )
        run_with_retries(
            self.bot,
            self.bot.set_chat_title,
            dict(
                title=f'{STORAGE_CHAT_PREFIX}{msg.message_id}', chat_id=STORAGE_CHAT_ID
            ),
        )
        run_with_retries(
            self.bot,
            self.bot.delete_message,
            dict(chat_id=STORAGE_CHAT_ID, message_id=int(msg.message_id) + 1),
        )


class BazarakiChecker(Checker):
    def __init__(
        self, bot: telegram.Bot, url: str, category: str, chat_id: str
    ) -> None:
        self.url = url
        super().__init__(bot, category, chat_id)

    def parse_site_for_images_and_coords(
        self, resp_images: requests.Response
    ) -> Dict[str, Any]:
        return parse_site_for_images_and_coords(resp_images)

    def get_curr_variants(self) -> Dict[str, Dict[str, Any]]:
        resp_http = run_with_retries(self.bot, requests.get, {'url': self.url}, 5)
        items = parse_bazaraki(resp_http, APPARTMENT_MAX_PRICE)
        if not items:
            logger.error('no new items')
            exit(0)

        return items


class AppartmentChecker(BazarakiChecker):
    def __init__(self, bot: telegram.Bot) -> None:
        self.filter = AppartmentFilter(
            price_max=APPARTMENT_MAX_PRICE,
            single_district=DEFAULT_SINGLE_DISTRICT,
            area_min=30,
            furnishing=list(DEFAULT_FURNISHING),
            rubric=DEFAULT_RUBRIC,
        )
        url = (
            f'{BAZARAKI_URL}/{BAZARAKI_CATEGORY_APPARTMENTS}/'
            + self.filter.http_query()
        )
        super().__init__(bot, url, CATEGORY_APPARTMENTS, CHAT_ID_APPARTMENTS)
