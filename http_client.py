from contextlib import contextmanager
from datetime import datetime, timedelta
import logging
import re
# import string
import time
from typing import Any, Dict

from bs4 import BeautifulSoup
from requests import Response
# from translate import Translator
import requests

from distance_counter import haversine
from mistakes import MISTAKES
from settings import *
from utils import ADS_DICT, HttpFilter

logger = logging.getLogger(__name__)
TIME_FORMAT = '%d.%m.%Y'


class Client:
    def __init__(self):
        self.session = requests.Session()
        # self.translator = Translator(to_lang="en", from_lang='el')
        # self.translator = LibreTranslateAPI("https://translate.argosopentech.com/")

    def get_updates(self, category: ADS_DICT) -> ADS_DICT:
        ads = {}
        _filter = HttpFilter(
            price_max=category['price_max'],
            custom_filters=category.get('custom_filters', {}),
        ).http_query()

        for subcategory in category.get('subcategories', [category]):
            ads.update(self._get_ads(f"{BAZARAKI_URL}/{subcategory['path']}/{_filter}"))
        if category['name'] == CATEGORY_RENT:
            short_term_ads = self._get_ads(
                f"{BAZARAKI_URL}/real-estate-to-rent/short-term/{_filter}"
            )
            for ad in short_term_ads.values():
                ad['short_term'] = True
                if ad['price'] <= 800:
                    ad['price'] *= 30
            ads.update(short_term_ads)

        return ads

    def enrich_new_ads(self, ads_dict: ADS_DICT) -> None:
        logger.info('Enriching new ads')
        for category_name, ads in ads_dict.items():
            for ad in ads.values():
                response = self._get_with_retries(ad['url'], 5)
                if response.status_code >= 400:
                    continue
                ad.update(self._parse_ad_page(response, ad, category_name))

    def _get_ads(self, url: str) -> ADS_DICT:
        response = self._get_with_retries(url, 5)
        if response.status_code >= 400:
            return {}
        return self._parse_ads_page(response, url)

    def _get_with_retries(self, url, delay: int = 1):
        for i in range(3):
            try:
                response = self.session.get(url)
                response.raise_for_status()
                return response
            except Exception as exc:
                if i == 2:
                    logger.exception(
                        f'Could not parse add (%s): %s\n%s',
                        response.status_code,
                        url,
                        exc,
                    )
                    MISTAKES.append(
                        f'Could not parse add ({response.status_code}): {url}\n{exc}'
                    )
                time.sleep(delay)

    def _parse_ads_page(self, response: Response, url: str) -> ADS_DICT:
        ads = {}
        now = datetime.utcnow()
        today = now.strftime(TIME_FORMAT)
        yesterday = (now - timedelta(days=1)).strftime(TIME_FORMAT)
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
                ads.update(self._parse_li(li, today, yesterday, expired_date))
            except Exception as exc:
                logger.exception(f'Parse error for: {url}  Exception: {exc}')
                MISTAKES.append(f'Parse error for: {url}  Exception: {exc}')

        return ads

    def _parse_li(
        self, li: Any, today: str, yesterday: str, expired_date: datetime
    ) -> Dict[str, Any]:
        id_tag = li.find(
            'div',
            attrs={
                'class': 'announcement-block__favorites js-add-favorites js-favorites-handler'
            },
        )
        ad_id = id_tag['data-id']

        # \n\t22.10.2022 15:11,\n\t Limassol district, Germasogeia\n
        date_tag = li.find('div', attrs={'class': 'announcement-block__date'})
        ad_datetime_str = (
            date_tag.string.strip()
            .split('\n')[0]
            .replace('Today', today)
            .replace('Yesterday', yesterday)
        )
        match = re.match('.*(\d{2}\.\d{2}\.\d{4} \d{2}:\d{2}).*', ad_datetime_str)
        if not match:
            raise RuntimeError(f'Wrong date format (ad {ad_id}): {ad_datetime_str}')
        ad_datetime = datetime.strptime(match.group(1), '%d.%m.%Y %H:%M')

        if ad_datetime < expired_date:
            return

        item = {
            'id': ad_id,
            'url': BAZARAKI_URL + li.find('a')['href'],
            'images': [img['src']] if (img := li.find('img')) else [],
            'dt': ad_datetime,
        }

        for meta in li.findAll('meta'):
            if meta['itemprop'] == 'price':
                item['price'] = int(float(meta['content']))
            elif meta['itemprop'] == 'name':
                item['name'] = meta['content'].strip()
            elif meta['itemprop'] == 'areaServed':
                item['location'] = meta['content'].strip()

        return {item['id']: item}

    def _parse_ad_page(
        self, response: Response, ad_props: Dict[str, Any], category_name: str
    ) -> Dict[str, Any]:
        info = {}

        soup = BeautifulSoup(response.text, 'html.parser')

        images_tag = soup.body.find('div', attrs={'class': 'announcement__images'})
        if images_tag:
            info['images'] = [img['src'] for img in images_tag.findAll('img')][:10]

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
                coords = (
                    re.match('.*(\d{2}\.\d+ \d{2}\.\d+).*', coords_tag['data-coords'])
                    .group(1)
                    .split()
                )
                info['coords'] = float(coords[1]), float(coords[0])
            district_coords = CITIES.get(
                ad_props['location'].split()[0].strip(), CITIES['Limassol']
            )
            info['radius'] = haversine(district_coords, info['coords'])

        description_tag = soup.body.find(
            'div', attrs={'class': 'announcement-description'}
        )
        with _parse_tag('description_tag', ad_props['url']):
            description = description_tag.p.string.strip()
            if description:
                description = description[:150] + '...' * (len(description) > 150)
                # if any(c not in string.printable for c in description):
                #     description = self.translator.translate(description)
                info['description'] = description

        ul_tag = soup.body.find('ul', attrs={'class': 'chars-column'})
        with _parse_tag('ul_tag', ad_props['url']):
            for li_tag in ul_tag.findAll('li'):
                span_string = li_tag.find('span').string.strip().lower()
                for field in CATEGORIES_PROPS[category_name]['category_fields']:
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
