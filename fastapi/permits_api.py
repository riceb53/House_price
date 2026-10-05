import json
import os

import requests
from dotenv import load_dotenv
from fastapi import FastAPI
from google.cloud import storage

load_dotenv()  # reads your settings from the .env file (see .env_template)

URL = "https://services.arcgis.com/VTyQ9soqVukalItT/arcgis/rest/services/Residential_Construction_Permits_by_County/FeatureServer/24/query?outFields=*&where=1%3D1&f=geojson"
PROJECT_ID = os.environ["GCP_PROJECT_ID"]
BUCKET = os.environ["GCS_BUCKET_NAME"]

app = FastAPI()


@app.get("/scrape_some_data")
def scrape_data():
    features = []
    while True:  # the server sends counties in batches, so keep asking for the next batch
        params = {"resultOffset": len(features), "orderByFields": "OBJECTID"}
        page = requests.get(URL, params=params, timeout=120).json()
        features += page["features"]
        if not page.get("properties", {}).get("exceededTransferLimit"):
            break

    data = json.dumps({"type": "FeatureCollection", "features": features})
    blob = storage.Client(project=PROJECT_ID).bucket(BUCKET).blob("permits.geojson")
    blob.upload_from_string(data, content_type="application/json")
    return {"saved_to": f"gs://{BUCKET}/permits.geojson", "counties": len(features)}
