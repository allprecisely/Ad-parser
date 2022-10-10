import io
import json
import logging
import os
from datetime import datetime
import time

from dotenv import load_dotenv
import requests
from parse_html import parse_bazariki
import telegram
from telegram.utils.request import Request

import distance_counter

load_dotenv()
CHAT_ID = os.environ['CHAT_ID']
STORAGE_CHAT_ID = os.environ['STORAGE_CHAT_ID']
TOKEN = os.environ['TOKEN']
BAZARIKI_URL = 'https://www.bazaraki.com'
API_FILTER = '?rubric=681&c=1133&ordering=newest&q=&attrs__furnishing=1&attrs__furnishing=2&attrs__area_min=30&city_districts=5738&city_districts=5008&city_districts=5515&city_districts=5684&city_districts=5682&city_districts=5688&city_districts=5690&city_districts=5692&city_districts=5694&city_districts=5696&city_districts=5049&city_districts=5683&city_districts=5739&city_districts=5687&city_districts=5689&city_districts=5691&city_districts=5693&city_districts=5695&city_districts=5699&city_districts=5207&city_districts=5737&city_districts=5593&city_districts=5385&city_districts=5731&city_districts=5476&city_districts=5317&price_max=1500&'
RAW_FILTER = 'area_min---30/furnishing---1/furnishing---2/?type_view=line&ordering=newest&price_max=1500&city_districts=5738&city_districts=5008&city_districts=5515&city_districts=5684&city_districts=5682&city_districts=5688&city_districts=5690&city_districts=5692&city_districts=5694&city_districts=5696&city_districts=5049&city_districts=5683&city_districts=5739&city_districts=5687&city_districts=5689&city_districts=5691&city_districts=5693&city_districts=5695&city_districts=5699&city_districts=5207&city_districts=5737&city_districts=5593&city_districts=5385&city_districts=5731&city_districts=5476&city_districts=5317'
DUMP_FILE = 'previous_search.txt'
TEMPLATE_DESCRIPTION = '''{name}
price: {price}{price_lowered}
date: {date}{distance}
description: {description}

=========================
'''
DISTANCE_TEXT = '\ndistance to office: {distance:.1f} km'
OFFICE_POINT = float(os.environ['OFFICE_POINT_LATITUDE']), float(
    os.environ['OFFICE_POINT_LONGITUDE']
)
MAX_DISTANCE = 5
MAX_PRICE = 1200
logger = logging.getLogger(__name__)


def catch_exception(bot, f, kwargs, exc_text = None, tries = 3):
    for i in range(tries):
        try:
            return(f(**kwargs))
        except Exception as exc:
            if i == 0:
                logger.exception(f's-th went wrong, {f.__name__}')
            time.sleep(1)
    else:
        try:
            bot.send_message(
                text=f'{exc_text or f.__name__}: {exc}', chat_id=STORAGE_CHAT_ID
            )
        except:
            pass


def lambda_handler(event, context):
    bot = telegram.Bot(TOKEN, request=Request(connect_timeout=20, read_timeout=20))

    curr_variants = check_site(bot)
    if not curr_variants:
        return

    prev_variants = get_prev_variants(bot)
    new_variants = get_new_variants(prev_variants, curr_variants)
    deleted_variants = get_deleted_variants(prev_variants, curr_variants)

    send_new_variants(bot, new_variants, curr_variants)
    update_deleted_variants(bot, deleted_variants)
    save_new_variants(bot, new_variants, curr_variants)


def send_new_variants(bot, new_variants, curr_variants):
    for k, variant in new_variants.items():
        image = requests.get(variant['image']).content
        variant['distance'] = (
            DISTANCE_TEXT.format(**variant) if 'distance' in variant else ''
        )
        variant['price'] = int(float(variant['price']))
        variant.setdefault('price_lowered', '')
        variant['description'] = variant['description'][:100] + '...' * (
            len(variant['description']) > 100
        )
        msg = catch_exception(bot, bot.send_photo, dict(
            photo=image,
            caption=TEMPLATE_DESCRIPTION.format(**variant),
            caption_entities=[
                telegram.MessageEntity(
                    type='text_link',
                    offset=0,
                    url=BAZARIKI_URL + variant['href'],
                    length=len(variant['name']),
                )
            ],
            chat_id=CHAT_ID,
        ))
        curr_variants[k]['msg_id'] = str(msg.message_id)


def update_deleted_variants(bot: telegram.Bot, deleted_variants):
    for variant in deleted_variants.values():
        if 'msg_id' not in variant:
            continue
        price = int(float(variant['price']))
        text = variant['name'] + f'\nprice: {price}'
        catch_exception(bot, bot.edit_message_caption , dict(
            caption=text,
            caption_entities=[
                telegram.MessageEntity(
                    type='bold',
                    offset=0,
                    length=len(text)
                )
            ],
            chat_id=CHAT_ID,
            message_id=variant['msg_id']
        ))

def get_prev_variants(bot: telegram.Bot):
    prev_msg = bot.get_chat(chat_id=STORAGE_CHAT_ID)
    if not prev_msg:
        bot.send_message(
            text=f'could not find prev msg: {exc}', chat_id=STORAGE_CHAT_ID
        )
        exit(0)
    if 'new' in prev_msg.title.lower():
        return {}
    msg = catch_exception(bot, bot.edit_message_caption, dict(
        caption=str(datetime.now()),
        chat_id=STORAGE_CHAT_ID,
        message_id=prev_msg.title[len('GII bot storage '):],
    ))
    if msg:
        prev_variants = catch_exception(bot, json.loads, dict(
            s=msg.document.get_file().download_as_bytearray()
        ))
        if prev_variants:
            return prev_variants
    exit(0)


def get_new_variants(prev_variants, curr_variants):
    new_variants = {}
    i = 0
    for k, v in curr_variants.items():
        i += 1
        if k not in prev_variants:
            new_variants[k] = v
        elif float(v['price']) < float(prev_variants[k]['price']):
            new_variants[k] = {**v, 'price_lowered': ' (lowered)'}
        if i == 10:
            break
    return new_variants


def get_deleted_variants(prev_variants, curr_variants):
    return {k: v for k, v in prev_variants.items() if k not in curr_variants and 'msg_id' in v}


def save_new_variants(bot: telegram.Bot, new_variants, curr_variants):
    if not new_variants:
        return
    with io.StringIO() as _file:
        json.dump(curr_variants, _file, indent=4)
        _file.seek(0)
        msg = catch_exception(bot, bot.send_document, dict(
            document=_file,
            filename='results.json',
            caption=str(datetime.now()),
            chat_id=STORAGE_CHAT_ID,
        ))
    prev_msg = catch_exception(bot, bot.get_chat, dict(chat_id=STORAGE_CHAT_ID))
    if prev_msg:
        if 'new' not in prev_msg.title:
            catch_exception(bot, bot.delete_message, dict(
                chat_id=STORAGE_CHAT_ID, message_id=int(prev_msg.title[len('GII bot storage ')])
            ))
    catch_exception(bot, bot.set_chat_title, dict(
        title=f'GII bot storage {msg.message_id}', chat_id=STORAGE_CHAT_ID
    ))
    if prev_msg and 'new' not in prev_msg.title:
        catch_exception(bot, bot.delete_message, dict(
            chat_id=STORAGE_CHAT_ID, message_id=int(prev_msg)
        ))


def check_site(bot):
    url_http = f'{BAZARIKI_URL}/real-estate/houses-and-villas-rent/{RAW_FILTER}'
    resp_http = catch_exception(bot, requests.get, {'url': url_http})
    items = parse_bazariki(resp_http)
    if not items:
        exit()

    items = {
        k: v
        for k, v in items.items()
        if float(v['price']) <= MAX_PRICE and 'Limassol' in v['areaServed']
    }

    try:
        url_api = f'{BAZARIKI_URL}/api/items/adverts-geometry/{API_FILTER}'
        resp_api = catch_exception(bot, requests.get, {'url': url_api})
        for i in resp_api.json()['results']:
            if str(i['id']) in items:
                distance = distance_counter.haversine(OFFICE_POINT, i['geometry'])
                items[str(i['id'])]['distance'] = distance
    except:
        pass

    return items


if __name__ == '__main__':
    try:
        lambda_handler(None, None)
    except Exception as exc:
        logger.exception('s-th went wrong')
        bot = telegram.Bot(TOKEN)
        bot.send_message(
            text=f'@gilfanovii s-th went wrong: {exc}', chat_id=STORAGE_CHAT_ID
        )
