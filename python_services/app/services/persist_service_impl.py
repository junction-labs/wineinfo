import os
from contextlib import closing
import sqlite3
from typing import List, Tuple
from ..common.config import ServiceSettings
from ..common.api import SQLRequest, Wine, PaginatedList
from fastapi import HTTPException


class PersistServiceImpl:
    def __init__(self, settings: ServiceSettings, reset: bool = False):
        self.db_path = os.path.join(settings.data_path, "persist_data.db")
        if reset:
            self._init_database()

    def _init_database(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("DROP TABLE IF EXISTS cellar")
        cursor.execute("DROP TABLE IF EXISTS wine")
        
        cursor.execute(
            """
            CREATE TABLE cellar (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                wine_id INTEGER NOT NULL
            )
            """
        )
        
        cursor.execute(
            """
            CREATE TABLE wine (
                id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                country TEXT NOT NULL,
                description TEXT NOT NULL,
                designation TEXT NOT NULL,
                points TEXT NOT NULL,
                price TEXT NOT NULL,
                province TEXT NOT NULL,
                region_1 TEXT NOT NULL,
                region_2 TEXT NOT NULL,
                variety TEXT NOT NULL,
                winery TEXT NOT NULL
            )
            """
        )
        
        conn.commit()
        conn.close()

    def add_wine(self, wine: Wine) -> Wine:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO wine (title, country, description, designation, points, price, province, region_1, region_2, variety, winery)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (wine.title, wine.country, wine.description, wine.designation, wine.points, wine.price, wine.province, wine.region_1, wine.region_2, wine.variety, wine.winery)
            )
            wine.id = cursor.lastrowid
            conn.commit()
            return wine

    def get_wine(self, ids: List[int]) -> List[Wine]:
        if not ids:
            return []
            
        wines = []
        missing_ids = []
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            placeholders = ','.join(['?' for _ in ids])
            cursor.execute(
                f"SELECT id, title, country, description, designation, points, price, province, region_1, region_2, variety, winery FROM wine WHERE id IN ({placeholders})",
                ids
            )
            
            found_ids = set()
            for row in cursor.fetchall():
                wine = Wine(
                    id=row[0],
                    title=row[1],
                    country=row[2],
                    description=row[3],
                    designation=row[4],
                    points=row[5],
                    price=row[6],
                    province=row[7],
                    region_1=row[8],
                    region_2=row[9],
                    variety=row[10],
                    winery=row[11]
                )
                wines.append(wine)
                found_ids.add(wine.id)
            
            missing_ids = [wine_id for wine_id in ids if wine_id not in found_ids]
            
        if missing_ids:
            raise HTTPException(
                status_code=404, detail=f"Wines not found: {missing_ids}"
            )
            
        return wines

    def get_wines_by_user_id(self, user_id: int) -> List[Wine]:
        """Get all wines in a user's cellar by user_id"""
        wines = []
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT w.id, w.title, w.country, w.description, w.designation, w.points, w.price, w.province, w.region_1, w.region_2, w.variety, w.winery 
                FROM wine w
                INNER JOIN cellar c ON w.id = c.wine_id
                WHERE c.user_id = ?
                """,
                (user_id,)
            )
            
            for row in cursor.fetchall():
                wine = Wine(
                    id=row[0],
                    title=row[1],
                    country=row[2],
                    description=row[3],
                    designation=row[4],
                    points=row[5],
                    price=row[6],
                    province=row[7],
                    region_1=row[8],
                    region_2=row[9],
                    variety=row[10],
                    winery=row[11]
                )
                wines.append(wine)
            
        return wines

    def get_all_wines_paginated(self, page: int, page_size: int) -> PaginatedList[Wine]:
        offset = (page - 1) * page_size
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM wine")
            total = cursor.fetchone()[0]
            
            cursor.execute(
                "SELECT id, title, country, description, designation, points, price, province, region_1, region_2, variety, winery FROM wine LIMIT ? OFFSET ?",
                (page_size, offset)
            )
            
            wines = []
            for row in cursor.fetchall():
                wine = Wine(
                    id=row[0],
                    title=row[1],
                    country=row[2],
                    description=row[3],
                    designation=row[4],
                    points=row[5],
                    price=row[6],
                    province=row[7],
                    region_1=row[8],
                    region_2=row[9],
                    variety=row[10],
                    winery=row[11]
                )
                wines.append(wine)
        
        return PaginatedList[Wine](
            items=wines,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=(total + page_size - 1) // page_size,
        )

    def do_sql(self, params: SQLRequest) -> List[Tuple]:
        with sqlite3.connect(self.db_path) as conn:
            with closing(conn.cursor()) as cursor:
                cursor.execute(params.query, params.params)
                ret = cursor.fetchall()
                conn.commit()
                return ret
