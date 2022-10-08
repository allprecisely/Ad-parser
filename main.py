import os
from datetime import datetime

from dotenv import load_dotenv
import requests
import telegram

import distance_counter

load_dotenv()
CHAT_ID = os.environ['CHAT_ID']
STORAGE_CHAT_ID = os.environ['STORAGE_CHAT_ID']
TOKEN = os.environ['TOKEN']
BAZARIKI_URL = 'https://www.bazaraki.com'
FILTER = '?rubric=681&c=548&ordering=&q=&price_max=1500&attrs__furnishing=1&attrs__furnishing=2&attrs__area_min=30&cities=12'
DUMP_FILE = 'previous_search.txt'
TEMPLATE_DESCRIPTION = '''{title}
price: {price}
distance to office: {distance:.1f} km

=========================
'''
OFFICE_POINT = float(os.environ['OFFICE_POINT_LATITUDE']), float(
    os.environ['OFFICE_POINT_LONGITUDE']
)
LOCAL_STORAGE = False
MAX_DISTANCE = 5


def lambda_handler(event, context):
    bot = telegram.Bot(TOKEN)

    current_search = check_site()
    if not current_search:
        return

    new_variants = get_new_variants(bot, current_search)
    for variant in new_variants.values():
        image = requests.get(variant['image']).content
        bot.send_location(
            latitude=variant['geometry'][0],
            longitude=variant['geometry'][1],
            chat_id=CHAT_ID,
        )
        bot.send_photo(
            photo=image,
            caption=TEMPLATE_DESCRIPTION.format(**variant),
            caption_entities=[
                telegram.MessageEntity(
                    type='text_link',
                    offset=0,
                    url=variant['url'],
                    length=len(variant['title']),
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
                previous_search = set(i for i in _file.read().split() if i)
    else:
        prev_msg = bot.get_chat(chat_id=STORAGE_CHAT_ID).description
        if prev_msg:
            try:
                msg = bot.edit_message_caption(
                    caption=str(datetime.now()),
                    chat_id=STORAGE_CHAT_ID,
                    message_id=prev_msg,
                )
                previous_search = set(
                    msg.document.get_file().download_as_bytearray().decode().split()
                )
            except:
                bot.send_message(
                    text=f'prev msg incorrect: {exc}', chat_id=STORAGE_CHAT_ID
                )

    new_variants = {k: v for k, v in current_search.items() if k not in previous_search}

    if new_variants:
        if LOCAL_STORAGE:
            with open('previous_search.txt', 'w') as _file:
                _file.write(' '.join(current_search))
        else:
            msg = bot.send_document(
                document=' '.join(current_search).encode(),
                caption=str(datetime.now()),
                chat_id=STORAGE_CHAT_ID,
            )
            bot.set_chat_description(
                description=str(msg.message_id), chat_id=STORAGE_CHAT_ID
            )
            if prev_msg:
                try:
                    bot.delete_message(chat_id=STORAGE_CHAT_ID, message_id=int(prev_msg))
                except:
                    bot.send_message(
                        text=f'prev msg incorrect: {exc}', chat_id=STORAGE_CHAT_ID
                    )
    return new_variants if previous_search else {}


def check_site():
    url = f'{BAZARIKI_URL}/api/items/adverts-geometry/{FILTER}'
    response = requests.get(url)

    result = {}
    for i in response.json()['results']:
        if i['image']:
            distance = distance_counter.haversine(OFFICE_POINT, i['geometry'])
            if (
                distance <= MAX_DISTANCE
                and int(i['price'][1:].replace('.', '').strip()) <= 1200
            ):
                result[str(i['id'])] = {
                    'title': i['title'],
                    'price': i['price'],
                    'image': i['image'],
                    'url': BAZARIKI_URL + i['absolute_url'],
                    'geometry': i['geometry'],
                    'distance': distance,
                }

    return result


if __name__ == '__main__':
    try:
        lambda_handler(None, None)
    except Exception as exc:
        bot = telegram.Bot(TOKEN)
        bot.send_message(
            text=f'@gilfanovii s-th went wrong: {exc}', chat_id=STORAGE_CHAT_ID
        )
