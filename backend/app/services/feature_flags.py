from typing import Dict

from ..services.service_api import PersistService

##
## Feature Flags built on top of our persistence service
##
class FeatureFlags:
    def __init__(self, persist_service: PersistService):
        self.persist_service = persist_service

    def get_all(self) -> Dict[str, str]:
        rows = self.persist_service.do_sql([], {
                "query": "SELECT key, value FROM feature_flags",
                "params": [ ]
            })
        return {row[0]: row[1] for row in rows}
    
    def set(self, key: str, value: str):
        self.persist_service.do_sql([], {
            "query": """
                    INSERT INTO feature_flags (key, value) 
                    VALUES (?, ?)
                    ON CONFLICT (key) DO UPDATE SET 
                    value = excluded.value
                    """,  
            "params": [key, value]
        })       

    def get(self, key: str, default: str | None = None) -> str | None:
        rows = self.persist_service.do_sql([], {
                "query": "SELECT value FROM feature_flags WHERE key = ?",
                "params": [key]
            })
        return rows[0][0] if rows else default
    
    def delete(self, key:str):
        self.persist_service.do_sql([], {
            "query": "DELETE FROM feature_flags WHERE key = ?",
            "params": [key]
        })
