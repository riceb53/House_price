"""Small FastAPI service for county housing data."""
import os

import pandas as pd
from fastapi import FastAPI, Query

from data_utils import DATA_FILE, load_data

app = FastAPI(title="County Housing API")


def json_rows(data):
    # Missing pandas values need to become JSON null.
    return data.astype(object).where(pd.notna(data), None).to_dict("records")


@app.get("/health")
def health():
    return {"status": "ok", "demo_data": os.path.basename(DATA_FILE) == "sample_county_year.csv"}


@app.get("/counties")
def counties():
    data = load_data()
    return json_rows(data[["county_fips", "county"]].drop_duplicates())


@app.get("/merged")
def merged(fips: str = None, start_year: int = None, end_year: int = None,
           lag: int = Query(2, ge=2, le=3)):
    data = load_data()
    if fips:
        data = data[data["county_fips"] == fips.zfill(5)]
    if start_year:
        data = data[data["year"] >= start_year]
    if end_year:
        data = data[data["year"] <= end_year]
    data = data.copy()
    data["permits_lagged"] = data[f"permits_lag_{lag}"]
    return json_rows(data)


@app.get("/prices")
def prices():
    return json_rows(load_data()[["county_fips", "year", "home_value", "price_change_pct"]])


@app.get("/permits")
def permits():
    return json_rows(load_data()[["county_fips", "year", "permits"]])


@app.get("/weather")
def weather():
    return json_rows(load_data()[["county_fips", "year", "temp_f", "precip_in"]])
