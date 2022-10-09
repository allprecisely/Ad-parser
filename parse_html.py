from collections import defaultdict

from bs4 import BeautifulSoup
from requests import Response


def parse_bazariki(response: Response):
    print(1)
    if not response or response.status_code >= 400:
        return {}
    soup = BeautifulSoup(response.text, 'html.parser')
    ul = soup.body.find('ul', attrs={'class':'list-simple__output js-list-simple__output'})

    items = defaultdict(dict)
    for li in ul.findAll('li'):
        id_tag = li.find('div', attrs={'class':'announcement-block__favorites js-add-favorites js-favorites-handler'})
        if not id_tag:
            continue

        img = li.find('img')
        if not img:
            continue

        _id = id_tag['data-id']
        items[_id]['href'] = li.find('a')['href']
        items[_id]['image'] = img['src']

        description = li.find('div', attrs={'class':'announcement-block__description'})
        items[_id]['description'] = description.string.strip()

        announced_tag = li.find('div', attrs={'class':'announcement-block__date'})
        items[_id]['date'] = announced_tag.string.strip().split('\n')[0]

        for meta in li.findAll('meta'):
            items[_id][meta['itemprop']] = meta['content']
    print(2)
    return items
