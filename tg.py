from datetime import datetime
import json
from time import time
from typing import Any, Dict, List, Tuple
import logging

import telegram
from telegram.request import HTTPXRequest

from mistakes import MISTAKES
from settings import *
from utils import ADS_DICT

logger = logging.getLogger(__name__)
ERR_PREFIX = 'Something went wrong while upload, '


class Tg:
    def __init__(self) -> None:
        self.bot = telegram.Bot(
            TOKEN, request=HTTPXRequest(connect_timeout=20, read_timeout=20)
        )

    async def send_ads(
        self,
        users_by_ads: Dict[str, Dict[str, List[str]]],
        new_ads: ADS_DICT,
        users_settings: Any,
    ) -> None:
        for category, ads in users_by_ads.items():
            for ad_id, user_ids in ads.items():
                message = self._form_message(category, new_ads[ad_id])
                for user_id in user_ids:
                    await self._send_media_ad(
                        message, user_id, users_settings, new_ads[ad_id].get('coords')
                    )
        if MISTAKES:
            await self.send_mistakes(MISTAKES)

    def _form_message(self, category: str, ad: Dict[str, Any]) -> Any:
        extra = CATEGORIES_PROPS[category]['description'].format(**ad)
        description = TEMPLATE_DESCRIPTION.format(**ad, extra=extra)
        if lowered := ad.get('lowered'):
            description = description.replace('€\n', f'€ (lowered {lowered})\n')

        if not ad['images']:
            return description

        image_with_caption = telegram.InputMediaPhoto(
            media=ad['images'][0],
            caption=description,
            caption_entities=[
                telegram.MessageEntity(
                    type='text_link',
                    offset=0,
                    url=ad['url'],
                    length=len(ad['name']),
                ),
                telegram.MessageEntity(
                    type='bold',
                    offset=description.find('price: ') + len('price: '),
                    length=len(str(ad['price'])) + 2,
                ),
            ],
        )
        other_images = [telegram.InputMediaPhoto(img) for img in ad['images'][1:]]
        return [image_with_caption] + other_images

    async def _send_media_ad(
        self,
        message: Any,
        user_id: str,
        users_settings: Any,
        coords: Tuple[float, float],
    ) -> None:
        attempts = len(message) if isinstance(message, list) else 1
        while True:
            try:
                await self._send_media_ad_try(
                    message, user_id, users_settings, coords, attempts
                )
            except telegram.error.RetryAfter as exc:
                logger.info(f'again reload {exc.retry_after}')
                time.sleep(exc.retry_after)
            except Exception as exc:
                attempts -= 1
                if attempts == 0:
                    logger.exception('%s%s\n%s', ERR_PREFIX, message, exc)
                    MISTAKES.append('{ERR_PREFIX}{message}\n{exc}')
                    return
                time.sleep(1)

    async def _send_media_ad_try(
        self,
        message: Any,
        user_id: str,
        users_settings: Any,
        coords: Tuple[float, float],
        attempts: int,
    ) -> None:
        disable_notification = ads_without_photo = False
        if settings := users_settings.get(user_id):
            disable_notification = settings.get('without_sound', False)
            ads_without_photo = settings.get('ads_without_photo', False)
            if settings.get('show_location') and coords:
                await self.bot.send_location(
                    user_id, *coords, disable_notification=disable_notification
                )
        if isinstance(message, list):
            await self.bot.send_media_group(
                media=message[:attempts] + message[attempts + 1 :],
                chat_id=user_id,
                disable_notification=disable_notification,
            )
        if ads_without_photo:
            await self.bot.send_message(
                user_id, message, disable_notification=disable_notification
            )

    async def send_mistakes(self, mistakes: List[str]):
        with open(f'{datetime.now()}_dump.txt', 'w') as _file:
            json.dump(mistakes, _file, indent=4)
        try:
            await self.bot.send_message(STORAGE_CHAT_ID, '\n'.join(mistakes))
        except Exception:
            logger.exception('Coud not send file with mistakes')
