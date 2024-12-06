import os
from typing import List, Dict, Tuple
from .service_api import PersistService, SQLRequest, ServiceSettings
from contextlib import closing
import sqlite3

class PersistServiceImpl(PersistService):
    def __init__(self, settings: ServiceSettings, reset: bool = False):
        self.db_path = os.path.join(settings.data_path, "persist_data.db")
        if reset:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("DROP TABLE IF EXISTS cellar")
            cursor.execute(
                """
                CREATE TABLE cellar (
                    id INTEGER PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    wine_id INTEGER NOT NULL
                )
                """
            )
            conn.commit()
            cursor.execute("DROP TABLE IF EXISTS feature_flags")
            cursor.execute(
                """
                CREATE TABLE feature_flags (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )
            conn.commit()
            conn.close


    def do_sql(self, headers: Dict, sql_request: SQLRequest) -> List[Tuple]:
        with sqlite3.connect(self.db_path) as conn:
            with closing(conn.cursor()) as cursor:
                cursor.execute(sql_request.query, sql_request.params)
                ret =  cursor.fetchall()
                conn.commit()
                return ret
    