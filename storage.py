from datetime import datetime
import logging
from typing import Any, Dict, Optional, Set
import sqlite3

from settings import *
from utils import ADS_DICT, USERS_DICT

logger = logging.getLogger(__name__)


class Storage:
    def __init__(self) -> None:
        self.con = sqlite3.connect(
            "storage.db", detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
        )
        self.cur = self.con.cursor()
        self.create_tables()

    def create_tables(self) -> None:
        for category_name, props in CATEGORIES.items():
            fields = ','.join(AD_COMMON_FIELDS[1:] + props['category_fields'])
            self.cur.execute(
                f'CREATE TABLE IF NOT EXISTS {category_name}(id PRIMARY KEY,{fields})'
            )

            fields = ','.join(props['users_fields'][1:])
            self.cur.execute(
                f'CREATE TABLE IF NOT EXISTS users_{category_name}(id PRIMARY KEY,{fields})'
            )

        fields = ','.join(USERS_FIELDS[1:])
        self.cur.execute(f'CREATE TABLE IF NOT EXISTS users(id PRIMARY KEY,{fields})')

    def get_ad_history_ids(self) -> Dict[str, Set[str]]:
        ad_history_ids = {}
        for category_name in CATEGORIES:
            res = self.cur.execute(f'SELECT id FROM {category_name}')
            ad_history_ids[category_name] = {i[0] for i in res.fetchall()}
        return ad_history_ids

    def update_history(self, ads_dict: ADS_DICT) -> None:
        for category_name, ads in ads_dict.items():
            existed_fields = (
                AD_COMMON_FIELDS + CATEGORIES[category_name]['category_fields']
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
                    f'INSERT INTO {category_name}({fields}) VALUES({values})',
                    {**ad, **evaled},
                )
        self.con.commit()

    def get_users(self) -> USERS_DICT:
        users = {}
        for category_name, category_props in CATEGORIES.items():
            fields = ','.join(category_props['users_fields'])
            res = self.cur.execute(f'SELECT {fields} FROM users_{category_name}')
            users[category_name] = {
                row[0]: dict(zip(category_props['users_fields'], row))
                for row in res.fetchall()
            }
            for user_props_by_category in users[category_name].values():
                for field in EVALED_USERS_FIELDS:
                    if user_props_by_category.get(field):
                        user_props_by_category[field] = eval(
                            user_props_by_category[field]
                        )

        return users

    def save_user_ad_params(
        self, user_id: str, category: str, ad_params: Dict[str, Any]
    ) -> None:
        fields = ('id',) + tuple(
            f for f in ad_params if f in CATEGORIES[category]['users_fields']
        )
        values = ','.join(f':{field}' for field in fields)
        fields = ','.join(f'{field}' for field in fields)
        evaled = {
            field: str(value)
            for field, value in ad_params.items()
            if field in EVALED_USERS_FIELDS
        }
        self.cur.execute(
            f'INSERT OR REPLACE INTO users_{category}({fields}) VALUES({values})',
            {'id': user_id, **ad_params, **evaled},
        )
        self.con.commit()

    def is_user_existed_and_active(self, user_id: str) -> Optional[bool]:
        res = self.cur.execute('SELECT active FROM users WHERE id = ?', (user_id,))
        fetched = res.fetchone()
        print(fetched)
        return fetched[0] if fetched else None

    def save_user(self, user_id: str) -> bool:
        now = datetime.utcnow()
        self.cur.execute(
            (
                'INSERT INTO users(id,active,created_at,updated_at) VALUES (?,?,?,?)'
                'ON CONFLICT DO NOTHING'

            ),
            (user_id, False, now, now),
        )
        self.con.commit()

    def set_user_status(self, user_id: str, active: bool) -> bool:
        fields = ','.join(USERS_FIELDS)
        values = ','.join(f':{field}' for field in USERS_FIELDS)
        now = datetime.utcnow()
        self.cur.execute(
            (
                f'INSERT INTO users({fields}) VALUES ({values})'
                'ON CONFLICT DO UPDATE SET updated_at=excluded.updated_at, '
                'active=excluded.active WHERE active!=excluded.active'
            ),
            {
                'id': user_id,
                'active': active,
                'created_at': now,
                'updated_at': now,
                'history_asked_at': None,
            },
        )
        self.con.commit()

    def ad_params_by_user(self, user_id: str) -> Dict[str, Dict[str, Any]]:
        return {
            category_name: users[user_id]
            for category_name, users in self.get_users().items() if user_id in users
        }

    def delete_user(self) -> None:
        pass

    def get_ads_for_user_in_interval(self) -> ADS_DICT:
        pass
