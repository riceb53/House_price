# zillow data download

import io
import os

import pandas as pd
import requests
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from google.cloud import storage
from google.oauth2 import service_account

load_dotenv()  # read.env

service_account_key = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
project_id = os.getenv("GCP_PROJECT_ID")
bucket_name = os.getenv("GCS_BUCKET_NAME")
file_name = "zillow_county_yearly.csv"

# zhvi all homes
url = ("https://files.zillowstatic.com/research/public_csvs/zhvi/"
       "County_zhvi_uc_sfrcondo_tier_0.33_0.67_sm_sa_month.csv")


def store_to_gcs(service_account_key, project_id, bucket_name, file_name,
                 data):
    # same steps from class
    # credentials = service_account.Credentials.from_service_account_file(
        # service_account_key)
    client = storage.Client(project=project_id)
    bucket = client.bucket(bucket_name)
    file = bucket.blob(file_name)
    file.upload_from_string(data, content_type="text/csv")


def get_zillow_data():
    response = requests.get(url, timeout=120)
    # no junk to bucket
    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="zillow download failed")
    df = pd.read_csv(io.BytesIO(response.content))

    # dont need these cols
    df = df.drop(columns=["RegionID", "SizeRank", "RegionType",
                          "StateName", "Metro"])

    # its wide rn (1 col per month) so melt it into 1 row per county per month
    df = pd.melt(df,
                 id_vars=["RegionName", "State", "StateCodeFIPS",
                          "MunicipalCodeFIPS"],
                 var_name="date", value_name="home_value")
    df = df.dropna(subset=["home_value"])  # some countys miss months
    df["year"] = pd.to_datetime(df["date"]).dt.year  # 2000-01-31 -> 2000

    # pandas reads "06" as 6 so gotta pad the zeros back
    df["fips"] = (df["StateCodeFIPS"].astype(str).str.zfill(2)
                  + df["MunicipalCodeFIPS"].astype(str).str.zfill(3))

    # avg the months into years. count = how many months got averaged,
    # under 12 means its a partial year
    yearly = df.groupby(["fips", "RegionName", "State", "year"])["home_value"]
    yearly = yearly.agg(["mean", "count"]).reset_index()
    yearly.columns = ["fips", "county", "state", "year",
                      "avg_home_value", "months"]
    yearly["avg_home_value"] = yearly["avg_home_value"].round(2)
    return yearly


def zillow_prices():
    yearly = get_zillow_data()
    csv_data = yearly.to_csv(index=False)
    store_to_gcs(service_account_key, project_id, bucket_name, file_name,
                 csv_data)
    return {"saved_to": f"gs://{bucket_name}/{file_name}",
            "rows": len(yearly),
            "counties": yearly["fips"].nunique()}


# run w/o the server
if __name__ == "__main__":
    print(zillow_prices())
