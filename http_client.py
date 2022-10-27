from contextlib import contextmanager
from datetime import datetime, timedelta
import logging
import re
import time
from typing import Any, Dict, Optional

from bs4 import BeautifulSoup, NavigableString, Tag
from requests import Response
import requests

from distance_counter import haversine
from settings import *
from utils import HttpFilter

logger = logging.getLogger(__name__)
TIME_FORMAT = '%d.%m.%Y'


class Client:
    def __init__(self):
        self.session = requests.Session()
        # self.translator = Translator(to_lang="en", from_lang='el')
        # self.translator = LibreTranslateAPI("https://translate.argosopentech.com/")

    def get_updates(
        self, props: Dict[str, Any], saved_ads: Dict[str, Dict[str, int]]
    ) -> ADS_TYPE:
        ads = {}
        _filter = HttpFilter(
            price_max=props['price_max'],
            custom_filters=props.get('custom_filters', {}),
        ).http_query()

        for subcategory in props.get('subcategories', [props]):
            ads.update(
                self._get_ads(
                    f"{BAZARAKI_URL}/{subcategory['path']}/{_filter}",
                    saved_ads[props['name']],
                    short_term=(subcategory['name'] == 'short_term'),
                )
            )

        return ads

    def enrich_new_ads(self, new_ads: ADS_BY_CATEGORY_TYPE) -> None:
        logger.info(
            'Enriching new ads {}'.format({k: len(v) for k, v in new_ads.items()})
        )
        for category_name, ads in new_ads.items():
            for ad in ads.values():
                if not (response := self._get_with_retries(ad['url'], 5)):
                    return None
                try:
                    ad.update(
                        self._parse_ad_page(response, ad, category_name, ad['url'])
                    )
                except Exception as exc:
                    logger.exception(
                        f'Could not parse ad (%s): %s\n%s',
                        response.status_code,
                        ad['url'],
                        exc,
                    )
                    MISTAKES.append(
                        f'Could not parse ad ({response.status_code}): {ad["url"]}\n{exc}'
                    )

    def _get_ads(
        self, url: str, saved_ads_by_category: Dict[str, int], short_term: bool = False
    ) -> ADS_TYPE:
        if not (response := self._get_with_retries(url, 5)):
            return {}
        return self._parse_ads_page(response, url, saved_ads_by_category, short_term)

    def _get_with_retries(self, url: str, delay: int = 1) -> Optional[Response]:
        exc: Optional[Exception] = None
        for _ in range(3):
            try:
                response = self.session.get(url)
                response.raise_for_status()
                return response
            except Exception as _exc:
                exc = _exc
                time.sleep(delay)
        logger.exception(
            f'Could not parse ad (%s): %s\n%s', response.status_code, url, exc
        )
        MISTAKES.append(f'Could not parse ad ({response.status_code}): {url}\n{exc}')
        return None

    def _parse_ads_page(
        self,
        response: Response,
        url: str,
        saved_ads_by_category: Dict[str, int],
        short_term: bool = False,
    ) -> ADS_TYPE:
        ads = {}
        now = datetime.utcnow()
        today = now.strftime(TIME_FORMAT)
        yesterday = (now - timedelta(days=1)).strftime(TIME_FORMAT)
        expired_date = now - timedelta(days=DAYS_TO_EXPIRE)

        soup = BeautifulSoup(response.text, 'html.parser')
        if not soup.body:
            MISTAKES.append(f'Not body for: {url}')
            return {}
        ul = soup.body.find(
            'ul', attrs={'class': 'list-simple__output js-list-simple__output'}
        )
        if not ul or isinstance(ul, NavigableString):
            MISTAKES.append(f'Not ul_tag for: {url}')
            return {}

        lis = ul.findAll('li', attrs={'class': 'announcement-container'})
        if not lis:
            MISTAKES.append(f'Not announcement-containers for: {url}')
            return {}

        for li in lis:
            try:
                ads.update(
                    self._parse_li(
                        li,
                        now,
                        today,
                        yesterday,
                        expired_date,
                        saved_ads_by_category,
                        short_term,
                    )
                )
            except Exception as exc:
                logger.exception(f'Parse error for: {url}  Exception: {exc}')
                MISTAKES.append(f'Parse error for: {url}  Exception: {exc}')

        return ads

    def _parse_li(
        self,
        li: Any,
        now: datetime,
        today: str,
        yesterday: str,
        expired_date: datetime,
        saved_ads_by_category: Dict[str, int],
        short_term: bool = False,
    ) -> AD_TYPE:
        id_tag = li.find(
            'div',
            attrs={
                'class': 'announcement-block__favorites js-add-favorites js-favorites-handler'
            },
        )
        ad_id = id_tag['data-id']
        price = int(float(li.find('meta', attrs={'itemprop': 'price'})['content']))
        if short_term and price <= 800:
            price *= 30
        lowered = False
        if ad_id in saved_ads_by_category:
            if int(saved_ads_by_category[ad_id]) <= price:
                return {}
            lowered = True

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
            return {}

        item = {
            'id': ad_id,
            'url': BAZARAKI_URL + li.find('a')['href'],
            'images': [img['src']] if (img := li.find('img')) else [],
            'dt': ad_datetime,
            'name': li.find('meta', attrs={'itemprop': 'name'})['content'].strip(),
            'location': li.find('meta', attrs={'itemprop': 'areaServed'})[
                'content'
            ].strip(),
            'price': price,
            'added_at': now,
        }
        if short_term:
            item['short_term'] = True
        if lowered:
            item['lowered'] = True
        return {item['id']: item}

    def _parse_ad_page(
        self, response: Response, ad: AD_TYPE, category_name: str, url: str
    ) -> AD_TYPE:
        info: AD_TYPE = {}
        soup = BeautifulSoup(response.text, 'html.parser')
        if not soup.body:
            MISTAKES.append(f'Not body for: {url}')
            return {}

        # images
        images_tag = soup.body.find('div', attrs={'class': 'announcement__images'})
        if images_tag and not isinstance(images_tag, NavigableString):
            info['images'] = [img['src'] for img in images_tag.findAll('img')][:10]

        # coords
        coords_tag = soup.body.find(
            'a', attrs={'class': 'announcement__location js-open-announcement-location'}
        )
        assert isinstance(coords_tag, Tag)
        if data_coords := coords_tag.get('data-coords'):
            # data_coords = SRID=4326;POINT (33.055763 34.700778)
            assert isinstance(data_coords, str)
            assert (m := re.match('.*(\d{2}\.\d+ \d{2}\.\d+).*', data_coords))
            coords = m.group(1).split()
            info['coords'] = float(coords[1]), float(coords[0])
        else:
            assert isinstance((lat := coords_tag['data-default-lat']), str)
            assert isinstance((lng := coords_tag['data-default-lng']), str)
            info['coords'] = float(lat), float(lng)
        info['radius'] = haversine(CITIES[ad['location'].split()[0]], info['coords'])

        # description
        description_tag = soup.body.find(
            'div', attrs={'class': 'announcement-description'}
        )
        with _parse_tag('description_tag', ad['url']):
            assert (
                isinstance(description_tag, Tag)
                and description_tag.p
                and description_tag.p.string
            )
            description = description_tag.p.string.strip()
            if description:
                description = description[:150] + '...' * (len(description) > 150)
                # TODO: translation
                # if any(c not in string.printable for c in description):
                #     description = self.translator.translate(description)
                info['description'] = description

        # category props
        ul_tag = soup.body.find('ul', attrs={'class': 'chars-column'})
        with _parse_tag('ul_tag', ad['url']):
            assert isinstance(ul_tag, Tag)
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
