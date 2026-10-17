"""Combine the yearly Zillow and NOAA files using county FIPS and year."""
from pathlib import Path
import pandas as pd

folder = Path(__file__).parent / "data"

# Keep FIPS as text so codes like 01001 keep their leading zero.
zillow = pd.read_csv(folder / "zillow_county_yearly.csv", dtype={"fips": str})
weather = pd.read_csv(folder / "weather_county_year.csv", dtype={"county_fips": str})

# Only compare complete years (2026 is partial in these files).
zillow = zillow[zillow["months"] == 12].copy()
weather = weather[weather["weather_complete_year"] == True].copy()

# Give matching columns the same names.
zillow = zillow.rename(columns={"fips": "county_fips", "avg_home_value": "home_value"})
weather = weather.rename(columns={"avg_temp_f": "temp_f", "total_precip_in": "precip_in"})

zillow["county_fips"] = zillow["county_fips"].str.zfill(5)
weather["county_fips"] = weather["county_fips"].str.zfill(5)

# Zillow is the main dataset. Missing weather stays empty, not zero.
merged = zillow[["county_fips", "county", "state", "year", "home_value"]].merge(
    weather[["county_fips", "year", "temp_f", "precip_in"]],
    on=["county_fips", "year"],
    how="left",
    validate="one_to_one",
)

# We will replace these empty columns when their real source is available.
merged["permits"] = float("nan")
merged["unemployment_rate"] = float("nan")
merged["lat"] = float("nan")
merged["lon"] = float("nan")

merged = merged.sort_values(["state", "county", "year"])
merged.to_csv(folder / "merged.csv", index=False)

print("Created data/merged.csv")
print("Rows:", len(merged))
print("Counties:", merged["county_fips"].nunique())
print("Years:", merged["year"].min(), "to", merged["year"].max())
print("Rows with weather:", merged["temp_f"].notna().sum())
