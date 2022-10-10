import time

import telegram

from settings import *


def run_with_retries(bot, f, kwargs, logger):
    for i in range(3):
        try:
            return(f(**kwargs))
        except telegram.error.RetryAfter as exc:
            logger.info(f'again reload {exc.retry_after}')
            time.sleep(exc.retry_after)
        except Exception as exc:
            if i == 0:
                logger.exception(f's-th went wrong, {f.__name__}')
            time.sleep(1)
    else:
        try:
            bot.send_message(
                text=f'{f.__name__}: {exc}', chat_id=STORAGE_CHAT_ID
            )
        except:
            pass
