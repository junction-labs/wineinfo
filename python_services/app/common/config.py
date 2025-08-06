from pydantic_settings import BaseSettings


class ServiceSettings(BaseSettings):
    sommelier_service: str = "http://localhost:8001"
    search_service: str = "http://localhost:8002"
    embeddings_service: str = "http://localhost:8003"
    persist_service: str = "http://localhost:8004"
    use_junction: bool = False
    data_path: str = "python_services/data/gen"
    sommelier_demo_include_cellar: bool = False
    search_demo_latency: bool = False
    embeddings_demo_failure: bool = False
