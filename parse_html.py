from collections import defaultdict
from typing import Dict

from bs4 import BeautifulSoup
from requests import Response

from settings import BAZARIKI_URL


def parse_bazariki(response: Response) -> Dict[str, str]:
    if not response or response.status_code >= 400:
        return {}
    soup = BeautifulSoup(response.text, 'html.parser')
    ul = soup.body.find(
        'ul', attrs={'class': 'list-simple__output js-list-simple__output'}
    )

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

        _id = id_tag['data-id']
        items[_id] = {'price_lowered': '', 'distance': ''}
        items[_id]['url'] = BAZARIKI_URL + li.find('a')['href']
        items[_id]['image'] = img['src']

        description_tag = li.find(
            'div', attrs={'class': 'announcement-block__description'}
        )
        description = description_tag.string.strip()
        if description:
            description = (
                '\ndescription: ' + description[:100] + '...' * (len(description) > 100)
            )
        items[_id]['description'] = description

        announced_tag = li.find('div', attrs={'class': 'announcement-block__date'})
        items[_id]['date'] = announced_tag.string.strip().split('\n')[0]

        for meta in li.findAll('meta'):
            if meta['itemprop'] == 'price':
                items[_id]['price'] = int(float(meta['content']))
            elif meta['itemprop'] == 'name':
                items[_id]['name'] = meta['content']
            elif meta['itemprop'] == 'areaServed':
                items[_id]['areaServed'] = meta['content']

    return items


def parse_single_ad(response: Response) -> Dict[str, str]:
    if not response or response.status_code >= 400:
        return []
    soup = BeautifulSoup(response.text, 'html.parser')
    images_tag = soup.body.find('div', attrs={'class': 'announcement__images'})
    return [img['src'] for img in images_tag.findAll('img')]
    