from typing import Any, Dict, List

import telegram

from settings import ADDITIONAL_SELF_CHAT, DISABLE_NOTIFICATIONS
from utils import run_with_retries


def send_variants_to_self_group(
    bot: telegram.Bot, v: Dict[str, str], media_group: List[Any]
) -> None:
    if not ADDITIONAL_SELF_CHAT:
        return
    if v['price'] > 1200:
        return
    run_with_retries(
        bot,
        bot.send_media_group,
        dict(
            media=media_group,
            chat_id=ADDITIONAL_SELF_CHAT,
            disable_notification=DISABLE_NOTIFICATIONS,
        ),
    )
