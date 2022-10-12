from datetime import datetime, timedelta
import logging
import re
from typing import Any, Dict, Optional

from bs4 import BeautifulSoup
from requests import Response

from settings import BAZARAKI_URL, DAYS_TO_EXPIRE

logger = logging.getLogger(__name__)


def parse_bazaraki(
    response: Response, max_price: Optional[int] = None
) -> Dict[str, Dict[str, Any]]:
    if not response or response.status_code >= 400:
        return {}
    soup = BeautifulSoup(response.text, 'html.parser')
    ul = soup.body.find(
        'ul', attrs={'class': 'list-simple__output js-list-simple__output'}
    )

    now = datetime.now()
    expired_date = now - timedelta(days=DAYS_TO_EXPIRE)

    items = {}
    for li in ul.findAll('li'):
        id_tag = li.find(
            'div',
            attrs={
                'class': 'announcement-block__favorites js-add-favorites js-favorites-handler'
            },
        )
        if not id_tag:
            continue

        img = li.find('img')
        if not img:
            continue

        announced_tag = li.find('div', attrs={'class': 'announcement-block__date'})
        announcement_date = announced_tag.string.strip().split('\n')[0]
        match = re.match('(\d{2}.\d{2}.\d{4}).*', announcement_date)
        if match and datetime.strptime(match.group(1), '%d.%m.%Y') < expired_date:
            continue

        item = {
            'url': BAZARAKI_URL + li.find('a')['href'],
            'images': [img['src']],
            'date': announcement_date,
            'price_lowered': '',
            'ts': int(now.timestamp()),
        }

        description_tag = li.find(
            'div', attrs={'class': 'announcement-block__description'}
        )
        description = description_tag.string.strip()
        if description:
            description = (
                '\ndescription: ' + description[:100] + '...' * (len(description) > 100)
            )
        item['description'] = description

        for meta in li.findAll('meta'):
            if meta['itemprop'] == 'price':
                item['price'] = int(float(meta['content']))
                if max_price and item['price'] > max_price:
                    continue
            elif meta['itemprop'] == 'name':
                item['name'] = meta['content']
            elif meta['itemprop'] == 'areaServed':
                item['areaServed'] = meta['content']

        items[id_tag['data-id']] = item

    return items


def parse_site_for_images_and_coords(response: Response) -> Dict[str, Any]:
    if not response or response.status_code >= 400:
        return {}
    soup = BeautifulSoup(response.text, 'html.parser')
    images_tag = soup.body.find('div', attrs={'class': 'announcement__images'})

    coords_tag = soup.body.find(
        'a', attrs={'class': 'announcement__location js-open-announcement-location'}
    )
    coords = None
    if coords_tag:
        if coords_tag.get('data-default-lat'):
            coords = float(coords_tag['data-default-lat']), float(
                coords_tag['data-default-lng']
            )
        else:
            # coords_tag['data-coords'] = SRID=4326;POINT (33.055763 34.700778)
            # ppc, lat and lng are in the wrong placec :(
            coords = map(
                float,
                coords_tag['data-coords'].split(maxsplit=1)[1][1:-1].split()[::-1],
            )

    return {
        'coords': coords,
        'images': [img['src'] for img in images_tag.findAll('img')],
    }
