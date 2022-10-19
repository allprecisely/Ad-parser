from time import time
from typing import Any, Dict, List
import logging

import telegram
from telegram.request import HTTPXRequest

from mistakes import MISTAKES
from settings import *

logger = logging.getLogger(__name__)


class Tg:
    def __init__(self) -> None:
        self.bot = telegram.Bot(TOKEN, request=HTTPXRequest(connect_timeout=20, read_timeout=20))


    def send_ads(self, ads_by_category: Dict[str, Dict[str, List[Dict[str, Any]]]]) -> None:
        for category_name, ads_by_user in ads_by_category.items():
            for user_id, ads in ads_by_user.items():
                for ad in reversed(ads):
                    category_description = CATEGORIES[category_name]['description'].format(
                        **ad
                    )
                    description = TEMPLATE_DESCRIPTION.format(
                        **ad, category_description=category_description
                    )

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
                other_images = [telegram.InputMediaPhoto(img) for img in ad['images'][1:5]]
                media_group = [image_with_caption] + other_images

                self.send_media_ad(bot, media_group, user_id)


    def send_media_ad(self, media_group, user_id) -> None:
        i = len(media_group)
        while True:
            try:
                return self.bot.send_media_group(
                    media=media_group[:i] + media_group[i + 1 :],
                    chat_id=user_id,
                )
            except telegram.error.RetryAfter as exc:
                logger.info(f'again reload {exc.retry_after}')
                time.sleep(exc.retry_after)
            except Exception as exc:
                i -= 1
                if i == 0:
                    logger.exception('Some images are broken, %s', media_group)
                    MISTAKES.append(f'Some images are broken, {media_group}')
                    return
                time.sleep(1)

    def send_mistakes(self, mistakes: List[str]):
        self.bot.send_message(chat_id=STORAGE_CHAT_ID, text='\n'.join(mistakes))
