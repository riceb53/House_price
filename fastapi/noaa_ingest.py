import io
import os
from pathlib import Path
from google.cloud import storage
from datetime import datetime, timezone
from dotenv import load_dotenv

import numpy as np
import pandas as pd
import requests

BASE_URL = "https://www.ncei.noaa.gov/pub/data/cirs/climdiv/"
VERSION = "v1.0.0"
OUTPUT_DIR = Path("data")

load_dotenv()

BUCKET_NAME = os.getenv("GCS_BUCKET_NAME")
START_YEAR = 1980

NOAA_TO_FIPS = {
    "01": "01", "02": "04", "03": "05", "04": "06", "05": "08",  # AL AZ AR CA CO
    "06": "09", "07": "10", "08": "12", "09": "13", "10": "16",  # CT DE FL GA ID
    "11": "17", "12": "18", "13": "19", "14": "20", "15": "21",  # IL IN IA KS KY
    "16": "22", "17": "23", "18": "24", "19": "25", "20": "26",  # LA ME MD MA MI
    "21": "27", "22": "28", "23": "29", "24": "30", "25": "31",  # MN MS MO MT NE
    "26": "32", "27": "33", "28": "34", "29": "35", "30": "36",  # NV NH NJ NM NY
    "31": "37", "32": "38", "33": "39", "34": "40", "35": "41",  # NC ND OH OK OR
    "36": "42", "37": "44", "38": "45", "39": "46", "40": "47",  # PA RI SC SD TN
    "41": "48", "42": "49", "43": "50", "44": "51", "45": "53",  # TX UT VT VA WA
    "46": "54", "47": "55", "48": "56", "49": "15", "50": "02",  # WV WI WY HI AK
}

#NOAA files have fixed-width columns
COLSPECS = [(0, 2), (2, 5), (5, 7), (7, 11)] + [(11 + 7 * i, 18 + 7 * i) for i in range(12)]
MONTHS = [f"m{i:02d}" for i in range(1, 13)]

def read_weather(raw, element):
    columns = ["noaa_state", "county", "element", "year"] + MONTHS
    df = pd.read_fwf(io.BytesIO(raw), colspecs=COLSPECS, names=columns, dtype=str)
    code = "02" if element == "tmpc" else "01"
    df = df[df["element"] == code].copy()
    df["state_fips"] = df["noaa_state"].map(NOAA_TO_FIPS)
    df = df.dropna(subset=["state_fips"])
    df["county_fips"] = df["state_fips"] + df["county"]
    df["year"] = df["year"].astype(int)

    #put the monthly values into rows
    df = df.melt(id_vars=["county_fips", "state_fips", "year"], value_vars=MONTHS, var_name="month", value_name="value")
    df["month"] = df["month"].str[1:].astype(int)
    df["value"] = pd.to_numeric(df["value"], errors="coerce")

    #remove NOAA's missing values
    if element == "tmpc":
        df.loc[df["value"] <= -99, "value"] = np.nan
    else:
        df.loc[df["value"] < 0, "value"] = np.nan
    return df

def extreme_months(df, high, low):
    #compare each month with the 1991–2020 baseline.
    baseline = df[df["year"].between(1991, 2020)]
    limits = baseline.groupby(["county_fips", "month"])["value"].quantile([0.1, 0.9]).unstack().rename(columns={0.1: "low", 0.9: "high"}).reset_index()
    df = df.merge(limits, on=["county_fips", "month"], how="left")
    df[high] = (df["value"] > df["high"]).astype(int)
    df[low] = (df["value"] < df["low"]).astype(int)
    return df.groupby(["county_fips", "year"])[[high, low]].sum()

def make_yearly(temp, rain):
    keys = ["county_fips", "year"]
    t = temp.groupby(keys).agg(state_fips=("state_fips", "first"), avg_temp_f=("value", "mean"), temp_months_valid=("value", "count"),)
    p = rain.groupby(keys).agg(total_precip_in=("value", "sum"), precip_months_valid=("value", "count"),)
    hot_cold = extreme_months(temp, "hot_months", "cold_months")
    wet_dry = extreme_months(rain, "wet_months", "dry_months")
    yearly = t.join(p, how="outer").join(hot_cold).join(wet_dry).reset_index()
    yearly["state_fips"] = yearly["state_fips"].fillna(yearly["county_fips"].str[:2])

    #only use years with all 12 months
    yearly["weather_complete_year"] = ((yearly["temp_months_valid"] == 12) & (yearly["precip_months_valid"] == 12))
    values = ["avg_temp_f", "total_precip_in", "hot_months", "cold_months", "wet_months", "dry_months"]
    yearly.loc[~yearly["weather_complete_year"], values] = np.nan
    yearly = yearly[yearly["year"] >= START_YEAR].copy()
    yearly["avg_temp_f"] = yearly["avg_temp_f"].round(2)
    yearly["total_precip_in"] = yearly["total_precip_in"].round(2)
    for col in ["hot_months", "cold_months", "wet_months", "dry_months", "temp_months_valid", "precip_months_valid"]: yearly[col] = yearly[col].astype("Int64")
    return yearly.sort_values(keys)

def main():
    OUTPUT_DIR.mkdir(exist_ok=True)
    if not BUCKET_NAME:
        raise ValueError("Set GCS_BUCKET_NAME first")
    bucket = storage.Client().bucket(BUCKET_NAME)
    date = requests.get(BASE_URL + "procdate.txt", timeout=60)
    date.raise_for_status()
    procdate = date.text.strip()

    files = {}
    for element in ["tmpc", "pcpn"]:
        name = f"climdiv-{element}cy-{VERSION}-{procdate}"
        response = requests.get(BASE_URL + name, timeout=180)
        response.raise_for_status()
        (OUTPUT_DIR / name).write_bytes(response.content)
        bucket.blob(f"raw/noaa/{procdate}/{name}").upload_from_string(response.content, content_type="text/plain")
        files[element] = response.content
        print("Downloaded", name)

    temp = read_weather(files["tmpc"], "tmpc")
    rain = read_weather(files["pcpn"], "pcpn")
    yearly = make_yearly(temp, rain)
    yearly["noaa_procdate"] = procdate
    yearly["ingested_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    output = OUTPUT_DIR / "weather_county_year.csv"
    yearly.to_csv(output, index=False)
    bucket.blob("processed/noaa/weather_county_year.csv").upload_from_filename(str(output), content_type="text/csv")
    print("Uploaded files to GCS")
    print("Saved", output, "with", len(yearly), "rows")

if __name__ == "__main__":
    main()
