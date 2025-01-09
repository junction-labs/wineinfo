from functools import lru_cache
import os
from contextlib import closing
import sqlite3
from typing import List, Tuple
from fastapi import Depends, FastAPI
from .common.config import ServiceSettings
from .common.api import SQLRequest, PERSIST_SERVICE
from .common.baggage import create_baggage_middleware


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


# only reason we do this is so we can use implementation
# class in the data gen binary
@lru_cache()
def get_impl() -> PersistServiceImpl:
    return PersistServiceImpl(ServiceSettings())


app = FastAPI()
app.middleware("http")(create_baggage_middleware())


@app.post(PERSIST_SERVICE["do_sql"]["path"])
def do_sql(
    params: SQLRequest, impl: PersistServiceImpl = Depends(get_impl)
) -> List[Tuple]:
    with sqlite3.connect(impl.db_path) as conn:
        with closing(conn.cursor()) as cursor:
            cursor.execute(params.query, params.params)
            ret = cursor.fetchall()
            conn.commit()
            return ret
