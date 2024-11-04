import os
from catalog import Wine
from catalog import CATALOG_FILE, CatalogServiceImpl
from recs import RECS_DIR, RecommendationServiceImpl
from search import SEARCH_DIR, SearchServiceImpl 
import csv
import argparse

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
        default="backend/src_data/winemag-data-110k-v2.csv",
        help="The destination directory for the generated data",
    )
    args = parser.parse_args()

    if not os.path.exists("backend/gen_data"):
        os.mkdir("backend/gen_data")

    catalog_service = CatalogServiceImpl()
    recommendation_service = RecommendationServiceImpl(RECS_DIR, True)
    search_service = SearchServiceImpl(SEARCH_DIR, True)
    search_service.open_index()
    recommendation_service.open_index()
    with open(CATALOG_FILE, 'w', encoding='utf-8') as catalog_file:
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
