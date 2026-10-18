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


@app.post("/scrape_some_data")
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


@app.get("/send_house_price_data_to_streamlit")
def house_price_to_streamlit():
    # get data from gcp, send to streamlit 
    # what format should it be in?
    # pdb.set_trace()    
    client = storage.Client(project=PROJECT_ID)
    blob = client.bucket(BUCKET).blob("permits.geojson")
    data = json.loads(blob.download_as_text())
    return data
    # too much data for a browser, bit i think it's downloading entire csv.
    # we should think about trimming down the data on gcp for this reason otherwise things will be real slow


# upload zillow price data
# @app.get("/send_zillow_price_data_to_streamlit")
# def zillow_to_streamlit():


# will need to modify this once we know which graphs we are making


import pandas as pd
import io

@app.get("/send_weather_data_to_streamlit")
def weather_to_streamlit():
    # pdb.set_trace()
    client = storage.Client(project=PROJECT_ID)
    blob = client.bucket(BUCKET).blob("processed/noaa/weather_county_year.csv")
    data = json.loads(blob.download_as_text())
    return data

