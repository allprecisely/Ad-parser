import io
import json
import os
from datetime import datetime
import time

from dotenv import load_dotenv
import requests
from parse_html import parse_bazariki
import telegram

import distance_counter

load_dotenv()
CHAT_ID = os.environ['CHAT_ID']
STORAGE_CHAT_ID = os.environ['STORAGE_CHAT_ID']
TOKEN = os.environ['TOKEN']
BAZARIKI_URL = 'https://www.bazaraki.com'
API_FILTER = '?rubric=681&c=1133&ordering=newest&q=&attrs__furnishing=1&attrs__furnishing=2&attrs__area_min=30&city_districts=5738&city_districts=5008&city_districts=5515&city_districts=5684&city_districts=5682&city_districts=5688&city_districts=5690&city_districts=5692&city_districts=5694&city_districts=5696&city_districts=5049&city_districts=5683&city_districts=5739&city_districts=5687&city_districts=5689&city_districts=5691&city_districts=5693&city_districts=5695&city_districts=5699&city_districts=5207&city_districts=5737&city_districts=5593&city_districts=5385&city_districts=5731&city_districts=5476&city_districts=5317&'
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
LOCAL_STORAGE = False
MAX_DISTANCE = 5
MAX_PRICE = 1200


def lambda_handler(event, context):
    bot = telegram.Bot(TOKEN)

    current_search = check_site()
    if not current_search:
        return

    new_variants = get_new_variants(bot, current_search)
    for variant in new_variants.values():
        image = requests.get(variant['image']).content
        variant['distance'] = (
            DISTANCE_TEXT.format(**variant) if 'distance' in variant else ''
        )
        variant['price'] = int(float(variant['price']))
        variant.setdefault('price_lowered', '')
        variant['description'] = variant['description'][:100] + '...' * (
            len(variant['description']) > 100
        )
        bot.send_photo(
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
        )


def get_new_variants(bot: telegram.Bot, current_search):
    previous_search = set()
    prev_msg = None
    if LOCAL_STORAGE:
        if os.path.isfile(DUMP_FILE):
            with open(DUMP_FILE) as _file:
                previous_search = json.load(_file)
    else:
        prev_msg = bot.get_chat(chat_id=STORAGE_CHAT_ID).description
        if prev_msg:
            try:
                msg = bot.edit_message_caption(
                    caption=str(datetime.now()),
                    chat_id=STORAGE_CHAT_ID,
                    message_id=prev_msg,
                )
                previous_search = json.loads(
                    msg.document.get_file().download_as_bytearray()
                )
            except Exception as exc:
                bot.send_message(
                    text=f'prev msg incorrect1: {exc}', chat_id=STORAGE_CHAT_ID
                )

    new_variants = {}
    for k, v in current_search.items():
        if k not in previous_search:
            new_variants[k] = v
        elif v['price'] < previous_search[k]['price']:
            new_variants[k] = {**v, 'price_lowered': ' (lowered)'}

    if new_variants:
        if LOCAL_STORAGE:
            with open('previous_search.txt', 'w') as _file:
                json.dump(current_search, _file, indent=4)
        else:
            with io.StringIO() as _file:
                json.dump(current_search, _file, indent=4)
                _file.seek(0)
                msg = bot.send_document(
                    document=_file,
                    filename='results.json',
                    caption=str(datetime.now()),
                    chat_id=STORAGE_CHAT_ID,
                )
            bot.set_chat_description(
                description=str(msg.message_id), chat_id=STORAGE_CHAT_ID
            )
            if prev_msg:
                try:
                    bot.delete_message(
                        chat_id=STORAGE_CHAT_ID, message_id=int(prev_msg)
                    )
                except Exception as exc:
                    bot.send_message(
                        text=f'prev msg incorrect2: {exc}', chat_id=STORAGE_CHAT_ID
                    )
    return new_variants if previous_search else {}


def check_site():
    url = f'{BAZARIKI_URL}/real-estate/houses-and-villas-rent/{RAW_FILTER}'
    items = parse_bazariki(requests.get(url))

    items = {
        k: v
        for k, v in items.items()
        if float(v['price']) <= MAX_PRICE and 'Limassol' in v['areaServed']
    }

    url = f'{BAZARIKI_URL}/api/items/adverts-geometry/{API_FILTER}'
    response = requests.get(url)

    for i in response.json()['results']:
        if str(i['id']) in items:
            distance = distance_counter.haversine(OFFICE_POINT, i['geometry'])
            items[str(i['id'])]['distance'] = distance

    return items


if __name__ == '__main__':
    try:
        lambda_handler(None, None)
    except Exception as exc:
        bot = telegram.Bot(TOKEN)
        bot.send_message(
            text=f'@gilfanovii s-th went wrong: {exc}', chat_id=STORAGE_CHAT_ID
        )
