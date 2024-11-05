import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir, os.path.pardir)))
from backend.app.service_api import Wine
from backend.app.catalog import CatalogServiceImpl
from backend.app.recs import RecommendationServiceImpl
from backend.app.search import SearchServiceImpl 
import csv
import argparse
from pathlib import Path

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Generate wineinfo data")
    parser.add_argument(
        "--lines",
        default=1000,
        type=int,
        help="The number of lines to read from the source file. 0 means do the whole file",
    )
    parser.add_argument(
        "--src",
        default="backend/data/src/winemag-data-110k-v2.csv",
        help="The destination directory for the generated data",
    )
    args = parser.parse_args()

    if not os.path.exists(Path(CatalogServiceImpl.CATALOG_FILE).parent):
        os.mkdir(Path(CatalogServiceImpl.CATALOG_FILE).parent)

    catalog_service = CatalogServiceImpl("")#empty string so it doesn't load from file
    recommendation_service = RecommendationServiceImpl(True)
    search_service = SearchServiceImpl(True)
    search_service.open_index()
    recommendation_service.open_index()
    with open(CatalogServiceImpl.CATALOG_FILE, 'w', encoding='utf-8') as catalog_file:
        csv_writer = csv.DictWriter(catalog_file, Wine.model_fields)
        csv_writer.writeheader()
        with open(args.src, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            n= 0
            for row in reader:
                row = {k: v if v is not None else '' for k, v in row.items()}
                # clean up the 
                row['title'] = row['title'].removesuffix(" (" + row['region_1'] + ")")
                row['title'] = row['title'].removesuffix(" (" + row['province'] + ")")
                row['title'] = row['title'].strip()
                wine = Wine.model_validate(row)
                wine = catalog_service.add_wine(wine)
                csv_writer.writerow(wine.model_dump())
                recommendation_service.add_wine(wine)
                search_service.add_wine(wine)
                n = n + 1
                if n == args.lines:
                    break

    search_service.build_index()
    recommendation_service.build_index()
