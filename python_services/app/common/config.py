from pydantic_settings import BaseSettings

class ServiceSettings(BaseSettings):
    catalog_service: str = "http://localhost:8001"
    search_service: str = "http://localhost:8002"
    recs_service: str = "http://localhost:8003"
    persist_service: str = "http://localhost:8004"
    use_junction: bool = False
    data_path: str = "python_services/data/gen"
    catalog_demo_mojibake: bool = False
    search_demo_latency: bool = False
    recs_demo_failure: bool = False

STANDARD_HEADER_NAMES = [ "x-username", "x-tenantid" ]
