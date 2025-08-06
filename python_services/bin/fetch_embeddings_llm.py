import argparse
import os, sys

sys.path.append(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), os.path.pardir, os.path.pardir)
    )
)
from app.common.config import ServiceSettings
from app.services.embeddings_service_impl import EmbeddingsServiceImpl
from app.common.api import EmbeddingsSearchRequest

parser = argparse.ArgumentParser(description="Generate wineinfo data")
parser.add_argument(
    "--data",
    default="/app/data/gen",
    type=str,
    help="Path to the data directory",
)

args = parser.parse_args()
settings = ServiceSettings()
settings.data_path = args.data
impl = EmbeddingsServiceImpl(settings, False)
print(impl.catalog_search(EmbeddingsSearchRequest(query="red wine", limit=10)))
