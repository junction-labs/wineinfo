import os, sys
import random

sys.path.append(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), os.path.pardir, os.path.pardir)
    )
)
from python_services.app.common.config import ServiceSettings
from python_services.app.common.api import Wine
from python_services.app.services.embeddings_service_impl import EmbeddingsServiceImpl
from python_services.app.services.search_service_impl import SearchServiceImpl
from python_services.app.services.persist_service_impl import PersistServiceImpl
import csv
import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate wineinfo data")
    parser.add_argument(
        "--lines",
        default=1000,
        type=int,
        help="The number of lines to read from the source file. 0 means do the whole file",
    )
    parser.add_argument(
        "--src",
        default="python_services/data/src/winemag-data-110k-v2.csv",
        help="The source file to read from",
    )
    args = parser.parse_args()

    service_settings = ServiceSettings()
    if not os.path.exists(service_settings.data_path):
        os.mkdir(service_settings.data_path)

    persist_service = PersistServiceImpl(service_settings, True)
    embeddings_service = EmbeddingsServiceImpl(service_settings, True)
    search_service = SearchServiceImpl(service_settings, True)
    search_service.open_index()
    embeddings_service.open_index()
    
    # give a couple of customers a decent cellar
    all_wine_ids = []
    with open(args.src, "r", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        n = 0
        for row in reader:
            row = {k: v if v is not None else "" for k, v in row.items()}
            # clean up the
            row["title"] = row["title"].removesuffix(" (" + row["region_1"] + ")")
            row["title"] = row["title"].removesuffix(" (" + row["province"] + ")")
            row["title"] = row["title"].strip()
            wine = Wine.model_validate(row)
            wine = persist_service.add_wine(wine)
            all_wine_ids.append(wine.id)
            embeddings_service.add_wine(wine)
            search_service.add_wine(wine)
            n = n + 1
            if n == args.lines:
                break

    search_service.build_index()
    embeddings_service.build_index()
    customer1_wines = random.sample(all_wine_ids, min(100, len(all_wine_ids)))
    customer2_wines = random.sample(all_wine_ids, min(100, len(all_wine_ids)))
    
    for wine_id in customer1_wines:
        persist_service.add_wine_to_cellar(1, wine_id)
    for wine_id in customer2_wines:
        persist_service.add_wine_to_cellar(2, wine_id)
