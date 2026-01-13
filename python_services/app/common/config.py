from pydantic_settings import BaseSettings


class ServiceSettings(BaseSettings):
    sommelier_service: str = "http://localhost:8003"
    catalog_service: str = "http://localhost:8002"
    persist_service: str = "http://localhost:8001"
    use_junction: bool = False
    data_path: str = "python_services/data/gen"
    sandbox: str = ""
    search_demo_latency: bool = False
    embeddings_demo_failure: bool = False
    sommelier_demo_expensive: bool = False
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-20250514"
    anthropic_temperature: float = 1.0
    anthropic_max_tokens: int = 4096
    turbopuffer_api_key: str = ""
    turbopuffer_region: str = "gcp-us-central1"
    turbopuffer_namespace: str = "wineinfo"
    embedding_provider: str = "local"  # "local" or "openai"
    embedding_model: str = "BAAI/bge-base-en-v1.5"  # Local model or OpenAI model
    openai_api_key: str = ""
