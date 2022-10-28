from datetime import datetime
import logging
import pathlib
from typing import Any, Dict, Optional
import sqlite3

from settings import *

logger = logging.getLogger(__name__)


class Storage:
    def __init__(self) -> None:
        _path = (pathlib.Path(__file__).parent / 'storage.db').absolute()
        self.con = sqlite3.connect(
            _path, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
        )
        self.cur = self.con.cursor()
        self.create_tables()

    def create_tables(self) -> None:
        for category, props in CATEGORIES_PROPS.items():
            fields = ','.join(AD_COMMON_FIELDS[1:] + props['category_fields'])
            self.cur.execute(
                f'CREATE TABLE IF NOT EXISTS {category}(id PRIMARY KEY,{fields})'
            )

            fields = ','.join(props['users_fields'][1:])
            self.cur.execute(
                f'CREATE TABLE IF NOT EXISTS users_{category}(id PRIMARY KEY,{fields})'
            )

        fields = ','.join(USERS_FIELDS[1:])
        self.cur.execute(f'CREATE TABLE IF NOT EXISTS users(id PRIMARY KEY,{fields})')

    def get_saved_ads(self) -> Dict[str, Dict[str, int]]:
        logger.info('Getting saved ads')
        ad_history_ids = {}
        for category in CATEGORIES_PROPS:
            res = self.cur.execute(f'SELECT id,price FROM {category}')
            ad_history_ids[category] = {i[0]: i[1] for i in res.fetchall()}
        return ad_history_ids

    def upsert_new_ads(self, new_ads: ADS_BY_CATEGORY_TYPE) -> None:
        logger.info('Upserting new ads')
        for category, ads in new_ads.items():
            existed_fields = (
                AD_COMMON_FIELDS + CATEGORIES_PROPS[category]['category_fields']
            )
            for ad in ads.values():
                values = ','.join(
                    f':{field}' for field in ad if field in existed_fields
                )
                fields = ','.join(f'{field}' for field in ad if field in existed_fields)
                evaled = {
                    field: str(value)
                    for field, value in ad.items()
                    if field in EVALED_ADS_FIELDS
                }
                self.cur.execute(
                    f'INSERT OR REPLACE INTO {category}({fields}) VALUES({values})',
                    {**ad, **evaled},
                )
        self.con.commit()

    def get_users_ad_params(
        self, user_id: Optional[str] = None
    ) -> USERS_PARAMS_BY_CATEGORY_TYPE:
        logger.info('Gettings users ad params')
        users = {}
        for category, category_props in CATEGORIES_PROPS.items():
            fields = ','.join(category_props['users_fields'])
            query = f'SELECT {fields} FROM users_{category}'
            if user_id:
                query += f' WHERE id = {user_id}'
            users[category] = {
                row[0]: {k: v for k, v in zip(category_props['users_fields'], row) if v}
                for row in self.cur.execute(query).fetchall()
            }
            for user_props_by_category in users[category].values():
                for field in EVALED_USERS_FIELDS:
                    if user_props_by_category.get(field):
                        user_props_by_category[field] = eval(
                            user_props_by_category[field]
                        )
        return users

    def upsert_user_ad_params(
        self, user_id: str, category: str, ad_params: USER_PARAMS_TYPE
    ) -> None:
        filtered = {
            k: v
            for k, v in ad_params.items()
            if k in CATEGORIES_PROPS[category]['users_fields']
        }
        filtered['id'] = user_id
        fields = ','.join(filtered)
        values = ','.join(f':{k}' for k in filtered)
        excluded = ','.join(f'{k}=excluded.{k}' for k in filtered)
        evaled = {
            field: str(value)
            for field, value in filtered.items()
            if field in EVALED_USERS_FIELDS
        }
        self.cur.execute(
            (
                f'INSERT INTO users_{category}({fields}) VALUES ({values})'
                f'ON CONFLICT DO UPDATE SET {excluded}'
            ),
            {**filtered, **evaled},
        )
        self.con.commit()

    def get_users_settings(self, user_id: Optional[str] = None) -> Optional[Any]:
        logger.info('Getting users settings')
        query = f'SELECT {",".join(USERS_FIELDS)} FROM users'
        if user_id:
            query += f' WHERE id = {user_id}'
        res = self.cur.execute(query)
        fetched = res.fetchall()
        if user_id:
            return (
                {k: v for k, v in zip(USERS_FIELDS, fetched[0]) if v is not None}
                if fetched
                else None
            )
        return {
            x[0]: {k: v for k, v in zip(USERS_FIELDS, x) if v is not None}
            for x in fetched
        }

    def upsert_user_settings(self, user_id: str, **kwargs) -> None:
        kwargs['id'] = user_id
        kwargs['updated_at'] = datetime.utcnow()
        fields = ','.join(kwargs)
        values = ','.join(f':{k}' for k in kwargs)
        excluded = ','.join(f'{k}=excluded.{k}' for k in kwargs)
        self.cur.execute(
            (
                f'INSERT INTO users({fields}) VALUES ({values})'
                f'ON CONFLICT DO UPDATE SET {excluded},updated_at=excluded.updated_at'
            ),
            kwargs,
        )
        self.con.commit()

    def delete_user_params_by_category(self, user_id: str, category: str) -> None:
        self.cur.execute(f'DELETE FROM users_{category} WHERE id = ?', (user_id,))
        self.con.commit()
    
    def delete_user(self, user_id: str) -> None:
        for category in CATEGORIES_PROPS:
            self.cur.execute(f'DELETE FROM users_{category} WHERE id = ?', (user_id,))
        self.cur.execute(f'DELETE FROM users WHERE id = ?', (user_id,))
        self.con.commit()

    def get_ads_for_user_in_interval(self) -> ADS_BY_CATEGORY_TYPE:
        pass
