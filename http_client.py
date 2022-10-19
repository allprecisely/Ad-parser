from contextlib import contextmanager
from datetime import datetime, timedelta
import logging
import re
import string
from typing import Any, Dict

from bs4 import BeautifulSoup
from requests import Response
from distance_counter import haversine
from translate import Translator
import requests

from mistakes import MISTAKES
from settings import *
from utils import ADS_DICT, HttpFilter, run_with_retries

logger = logging.getLogger(__name__)


class Client:
    def __init__(self):
        self.session = requests.Session()

    def get_updates(self, category: ADS_DICT) -> ADS_DICT:
        ads = {}
        _filter = HttpFilter(
            price_max=category['price_max'],
            custom_filters=category.get('custom_filters', {}),
        ).http_query()

        for subcategory in category.get('subcategories', [category]):
            ads.update(
                self._get_ads(
                    f"{BAZARAKI_URL}/{subcategory['path']}/{_filter}",
                    subcategory['name'],
                )
            )

        return ads

    def enrich_new_ads(self, ads_dict: ADS_DICT) -> None:
        translator = Translator(to_lang="en", from_lang='el')
        for category_name, ads in ads_dict.items():
            for ad in ads.values():
                response = run_with_retries(self.session.get, {'url': ad['url']}, 3)
                if response.status_code >= 400:
                    MISTAKES.append(
                        f"Could not parse add ({response.status_code}): {ad['url']}"
                    )
                    continue
                ad.update(self._parse_ad_page(response, ad, translator, category_name))

    def _get_ads(self, url: str, category: str) -> ADS_DICT:
        response = run_with_retries(self.session.get, {'url': url}, 5)
        if response.status_code >= 400:
            MISTAKES.append(
                f'Could not parse all {category} page ({response.status_code}): {url}'
            )
            return {}
        return self._parse_ads_page(response, url)

    def _parse_ads_page(self, response: Response, url: str) -> ADS_DICT:
        ads = {}
        now = datetime.now()
        expired_date = now - timedelta(days=DAYS_TO_EXPIRE)

        soup = BeautifulSoup(response.text, 'html.parser')
        ul = soup.body.find(
            'ul', attrs={'class': 'list-simple__output js-list-simple__output'}
        )
        if not ul:
            MISTAKES.append(f'Not ul_tag for: {url}')
            return

        lis = ul.findAll('li', attrs={'class': 'announcement-container'})
        if not lis:
            MISTAKES.append(f'Not announcement-containers for: {url}')
            return

        for li in lis:
            try:
                ads.update(self._parse_li(li, now, expired_date))
            except Exception as exc:
                logger.exception(f'Parse error for: {url}  Exception: {exc}')
                MISTAKES.append(f'Parse error for: {url}  Exception: {exc}')

        return ads

    def _parse_li(
        self, li: Any, now: datetime, expired_date: datetime
    ) -> Dict[str, Any]:
        id_tag = li.find(
            'div',
            attrs={
                'class': 'announcement-block__favorites js-add-favorites js-favorites-handler'
            },
        )
        if not id_tag:
            logger.warning('No id_tag in ad')
            return {}

        img = li.find('img')
        if not img:
            return {}

        announced_tag = li.find('div', attrs={'class': 'announcement-block__date'})
        announcement_date = announced_tag.string.strip().split('\n')[0]
        match = re.match('(\d{2}.\d{2}.\d{4}).*', announcement_date)
        if match and datetime.strptime(match.group(1), '%d.%m.%Y') < expired_date:
            return

        item = {
            'id': id_tag['data-id'],
            'url': BAZARAKI_URL + li.find('a')['href'],
            'images': [img['src']],
            'announcement_date': announcement_date,
            'created_at': now.strftime('%d.%m.%Y'),
        }

        for meta in li.findAll('meta'):
            if meta['itemprop'] == 'price':
                item['price'] = int(float(meta['content']))
            elif meta['itemprop'] == 'name':
                item['name'] = meta['content'].strip()
            elif meta['itemprop'] == 'areaServed':
                item['location'] = meta['content']

        return {item['id']: item}

    def _parse_ad_page(
        self,
        response: Response,
        ad_props: Dict[str, Any],
        translator: Translator,
        category_name: str,
    ) -> Dict[str, Any]:
        info = {}

        soup = BeautifulSoup(response.text, 'html.parser')

        images_tag = soup.body.find('div', attrs={'class': 'announcement__images'})
        with _parse_tag('images_tag', ad_props['url']):
            info['images'] = [img['src'] for img in images_tag.findAll('img')][:7]

        coords_tag = soup.body.find(
            'a', attrs={'class': 'announcement__location js-open-announcement-location'}
        )
        with _parse_tag('coords_tag', ad_props['url']):
            if coords_tag.get('data-default-lat'):
                info['coords'] = float(coords_tag['data-default-lat']), float(
                    coords_tag['data-default-lng']
                )
            else:
                # coords_tag['data-coords'] = SRID=4326;POINT (33.055763 34.700778)
                info['coords'] = map(
                    float,
                    coords_tag['data-coords'].split(maxsplit=1)[1][1:-1].split()[::-1],
                )
            district_coords = CITIES.get(
                ad_props['location'].split()[0], CITIES['Limassol']
            )
            info['distance_to_center'] = haversine(district_coords, info['coords'])

        description_tag = soup.body.find(
            'div', attrs={'class': 'announcement-description'}
        )
        with _parse_tag('description_tag', ad_props['url']):
            description = description_tag.p.string.strip()
            if description:
                description = description[:150] + '...' * (len(description) > 150)
                if any(c not in string.printable for c in description):
                    description = translator.translate(description)
                info['description'] = description

        ul_tag = soup.body.find('ul', attrs={'class': 'chars-column'})
        with _parse_tag('ul_tag', ad_props['url']):
            for li_tag in ul_tag.findAll('li'):
                span_string = li_tag.find('span').string.strip().lower()
                for field in CATEGORIES[category_name]['category_fields']:
                    if field in span_string:
                        a_tag = li_tag.find('a')
                        if a_tag:
                            info[field] = a_tag.string.strip()
                        else:
                            info[field] = li_tag.find(
                                'span', attrs={'class': 'value-chars'}
                            ).string.strip()
                        if field in INT_FIELDS:
                            info[field] = int(info[field].split()[0])
                        break

        return info


@contextmanager
def _parse_tag(tag_name: str, url: str) -> Any:
    try:
        yield
    except Exception as exc:
        logger.exception(f'Can not parse {tag_name} on: {url}  Exception: {exc}')
        MISTAKES.append(f'Can not parse {tag_name} on: {url}  Exception: {exc}')
