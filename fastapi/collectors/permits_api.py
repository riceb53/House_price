import json
import os
import pandas as pd

import requests
from dotenv import load_dotenv
from fastapi import FastAPI
from google.cloud import storage

load_dotenv()  # reads your settings from the .env file (see .env_template)

URL = "https://services.arcgis.com/VTyQ9soqVukalItT/arcgis/rest/services/Residential_Construction_Permits_by_County/FeatureServer/24/query?outFields=*&where=1%3D1&f=geojson"

PROJECT_ID = os.environ["GCP_PROJECT_ID"]
BUCKET = os.environ["GCS_BUCKET_NAME"]


def scrape_data():
    features = []
    while True:
        params = {"resultOffset": len(features), "orderByFields": "OBJECTID"}
        page = requests.get(URL, params=params, timeout=120).json()
        features += page["features"]
        if not page.get("properties", {}).get("exceededTransferLimit"):
            break

    data = json.dumps({"type": "FeatureCollection", "features": features})
    bucket = storage.Client(project=PROJECT_ID).bucket(BUCKET)
    blob = bucket.blob("permits.geojson")
    blob.upload_from_string(data, content_type="application/json")

    
    rows = []
    for feature in features:
        properties = feature["properties"]
        for year in range(1980, 2023):
            row = {
                "fips": properties["GEOID"],
                "year": year,
                "permits": properties.get(f"ALL_PERMITS_{year}") or 0,
            }
            rows.append(row)
    all_rows = pd.DataFrame(rows)
    new_bucket = storage.Client(project=PROJECT_ID).bucket(BUCKET)
    new_blob = new_bucket.blob("permits_formatted.csv")
    new_blob.upload_from_string(all_rows.to_csv(index=False), content_type="text/csv")

    # return {"saved_to": f"gs://{BUCKET}/permits.geojson", "counties": len(features)}
    return {"saved": "and formatted"}


