import io
import os
import pandas as pd
from google.cloud import storage


def getcsv(bucket, name, col="fips"):
    raw = bucket.blob(name).download_as_bytes()
    df = pd.read_csv(io.BytesIO(raw), dtype={col: str})
    df[col] = df[col].str.zfill(5)
    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df = df.dropna(subset=["year"])
    df["year"] = df["year"].astype(int)
    return df


def merge_data(z, w, p):
    # only take full years
    z = z[z["months"] == 12].copy()
    w = w[w["weather_complete_year"] == True].copy()
    w = w.rename(columns={"county_fips": "fips"})

    p = p.copy()
    p["permits"] = pd.to_numeric(p["permits"], errors="coerce")
    p = p.groupby(["fips", "year"], as_index=False)["permits"].sum(min_count=1)

    df = z.merge(w[["fips", "year", "avg_temp_f", "total_precip_in"]], on=["fips", "year"], how="left")
    df = df.merge(p, on=["fips", "year"], how="left")
    df = df.sort_values(["fips", "year"])

    df["price_change_pct"] = df.groupby("fips")["avg_home_value"].pct_change(fill_method=None) * 100
    # dont count a gap of 2 years as a 1 year change
    df.loc[df.groupby("fips")["year"].diff() != 1, "price_change_pct"] = float("nan")

    # permits from earlier years
    for n in [2, 3]:
        old = p.copy()
        old["year"] = old["year"] + n
        old = old.rename(columns={"permits": f"permits_lag_{n}"})
        df = df.merge(old, on=["fips", "year"], how="left")

    return df


def main():
    name = os.getenv("GCS_BUCKET_NAME", "house_prices_bucket")
    bucket = storage.Client().bucket(name)

    z = getcsv(bucket, "zillow_county_yearly.csv")
    w = getcsv(bucket, "weather_county_year.csv", "county_fips")
    p = getcsv(bucket, "permits_formatted.csv")

    df = merge_data(z, w, p)
    bucket.blob("merged_county_year.csv").upload_from_string(df.to_csv(index=False), content_type="text/csv")
    print("uploaded merged_county_year.csv to", name)
    print("rows:", len(df), "counties:", df["fips"].nunique())


if __name__ == "__main__":
    main()
