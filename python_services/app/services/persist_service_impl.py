import os
from contextlib import closing
import sqlite3
from typing import List, Tuple
from ..common.config import ServiceSettings
from ..common.api import SQLRequest


class PersistServiceImpl:
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
                    user_id INTEGER NOT NULL,
                    wine_id INTEGER NOT NULL
                )
                """
            )
            conn.commit()
            conn.close

    def do_sql(self, params: SQLRequest) -> List[Tuple]:
        with sqlite3.connect(self.db_path) as conn:
            with closing(conn.cursor()) as cursor:
                cursor.execute(params.query, params.params)
                ret = cursor.fetchall()
                conn.commit()
                return ret
