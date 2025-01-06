import os, sys

sys.path.append(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), os.path.pardir, os.path.pardir)
    )
)
from python_services.app.common.config import ServiceSettings
from python_services.app.common.api import Wine
from python_services.app.catalog_app import CatalogServiceImpl
from python_services.app.recs_app import RecsServiceImpl
from python_services.app.search_app import SearchServiceImpl
from python_services.app.persist_app import PersistServiceImpl
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
    catalog_service = CatalogServiceImpl(service_settings, True)
    recs_service = RecsServiceImpl(service_settings, True)
    search_service = SearchServiceImpl(service_settings, True)
    search_service.open_index()
    recs_service.open_index()
    with open(catalog_service.file_name, "w", encoding="utf-8") as catalog_file:
        csv_writer = csv.DictWriter(catalog_file, Wine.model_fields)
        csv_writer.writeheader()
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
                wine = catalog_service.add_wine(wine)
                csv_writer.writerow(wine.model_dump())
                recs_service.add_wine(wine)
                search_service.add_wine(wine)
                n = n + 1
                if n == args.lines:
                    break

    search_service.build_index()
    recs_service.build_index()
