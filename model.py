from copy import deepcopy
import io
import json
import logging
from datetime import datetime
from typing import Dict

import requests
import telegram
from telegram.utils.request import Request

from parse_html import parse_bazariki, parse_single_ad
from settings import *
from utils import run_with_retries


class Bazaraki:
    def __init__(
        self, logger: logging.Logger, url_http: str, category: str, chat_id: str
    ) -> None:
        self.logger = logger
        self.bot = telegram.Bot(
            TOKEN, request=Request(connect_timeout=20, read_timeout=20)
        )

        storage_chat = run_with_retries(
            self.bot, self.bot.get_chat, dict(chat_id=STORAGE_CHAT_ID), logger
        )
        if not storage_chat:
            logger.error('No storage chat')
            exit(0)
        self.last_storage_msg_id = storage_chat.title[len(STORAGE_CHAT_PREFIX) :]

        self.url_http = url_http
        self.category = category
        self.chat_id = chat_id

    def lambda_handler(self) -> None:
        self.logger.info(f'Start handling {self.category}')
        curr_variants = self.get_curr_variants()
        prev_variants = self.get_prev_variants()
        new_variants = self.get_new_variants(prev_variants, curr_variants)
        # deleted_variants = self.get_deleted_variants(prev_variants, curr_variants)

        self.send_new_variants(new_variants)
        # self.update_deleted_variants(deleted_variants)
        if new_variants:
            self.save_new_variants(prev_variants, new_variants)

    def get_curr_variants(self) -> Dict[str, str]:
        resp_http = run_with_retries(
            self.bot, requests.get, {'url': self.url_http}, self.logger
        )
        items = parse_bazariki(resp_http)
        if not items:
            self.logger.error('no new items')
            exit(0)

        return items

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
            self.logger,
        )
        if msg:
            _file = msg.document.get_file()
            content = run_with_retries(
                self.bot, _file.download_as_bytearray, {}, self.logger
            )
            if content:
                return json.loads(content)
        self.logger.error('no prev variants')
        exit(0)

    def get_new_variants(
        self, prev_variants: Dict[str, str], curr_variants: Dict[str, str]
    ) -> Dict[str, str]:
        new_variants = {}
        prev_variants = prev_variants.get(self.category, {})
        for k, v in curr_variants.items():
            if k not in prev_variants:
                new_variants[k] = v
            elif v['price'] < prev_variants[k]['price']:
                new_variants[k] = {**v, 'price_lowered': ' (lowered)'}
        self.logger.info(f'new/updated variants {new_variants.keys()}')
        return new_variants

    def get_deleted_variants(
        self, prev_variants: Dict[str, str], curr_variants: Dict[str, str]
    ) -> Dict[str, str]:
        return {
            k: v
            for k, v in prev_variants.get(self.category, {}).items()
            if k not in curr_variants and 'msg_id' in v
        }

    def send_new_variants(self, new_variants: Dict[str, str]) -> None:
        if DEBUG or len(new_variants) > 10:
            self.logger.info(
                'send_new_variants skip: %s, %s', len(new_variants), new_variants.keys()
            )
            return
        for k, v in reversed(new_variants.items()):
            resp_images = run_with_retries(
                self.bot, requests.get, {'url': v['url']}, self.logger
            )
            images = parse_single_ad(resp_images) or [v['image']]
            image_with_caption = telegram.InputMediaPhoto(
                media=images[0],
                caption=TEMPLATE_DESCRIPTION.format(**v),
                caption_entities=[
                    telegram.MessageEntity(
                        type='text_link',
                        offset=0,
                        url=v['url'],
                        length=len(v['name']),
                    )
                ],
            )
            other_images = [telegram.InputMediaPhoto(img) for img in images[1:5]]
            msgs = run_with_retries(
                self.bot,
                self.bot.send_media_group,
                dict(
                    media=[image_with_caption] + other_images,
                    chat_id=self.chat_id,
                    disable_notification=DISABLE_NOTIFICATIONS,
                ),
                self.logger,
            )
            # chat for myself
            if v['price'] <= 1200:
                run_with_retries(
                    self.bot,
                    self.bot.send_media_group,
                    dict(
                        media=[image_with_caption] + other_images,
                        chat_id='-1001838129908',
                        disable_notification=DISABLE_NOTIFICATIONS,
                    ),
                    self.logger,
                )
            if msgs:
                new_variants[k]['msg_id'] = str(msgs[0].message_id)
            else:
                self.logger.error(f'{k} variant was not loaded')

    def update_deleted_variants(self, deleted_variants: Dict[str, str]) -> None:
        if DEBUG:
            self.logger.info('delete_variants: %s', deleted_variants.keys())
            return
        for v in deleted_variants.values():
            if 'msg_id' not in v:
                continue
            text = f"{v['name']}\nprice: {v['price']}"
            run_with_retries(
                self.bot,
                self.bot.edit_message_caption,
                dict(
                    caption=text,
                    caption_entities=[
                        telegram.MessageEntity(
                            type='strikethrough', offset=0, length=len(text)
                        )
                    ],
                    chat_id=self.chat_id,
                    message_id=v['msg_id'],
                ),
                self.logger,
            )

    def save_new_variants(
        self, prev_variants: Dict[str, str], new_variants: Dict[str, str]
    ) -> None:
        updated_variants = deepcopy(prev_variants)
        updated_variants[self.category] = {
            **prev_variants[self.category],
            **new_variants,
        }
        if DEBUG:
            self.logger.info(
                'send_document: %s',
                {k: v.keys() for k, v in updated_variants.items()},
            )
            return

        with io.StringIO() as _file:
            json.dump(updated_variants, _file, indent=4)
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
                self.logger,
            )
        if self.last_storage_msg_id != 'new':
            run_with_retries(
                self.bot,
                self.bot.delete_message,
                dict(chat_id=STORAGE_CHAT_ID, message_id=int(self.last_storage_msg_id)),
                self.logger,
            )
        run_with_retries(
            self.bot,
            self.bot.set_chat_title,
            dict(
                title=f'{STORAGE_CHAT_PREFIX}{msg.message_id}', chat_id=STORAGE_CHAT_ID
            ),
            self.logger,
        )
        run_with_retries(
            self.bot,
            self.bot.delete_message,
            dict(chat_id=STORAGE_CHAT_ID, message_id=int(msg.message_id) + 1),
            self.logger,
        )
