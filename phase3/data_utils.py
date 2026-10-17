"""Read the merged CSV and calculate annual price change and permit lags."""
from pathlib import Path
import os
import pandas as pd

DATA_FILE = os.getenv("DATA_FILE", str(Path(__file__).parent / "data" / "merged.csv"))


def load_data():
    data = pd.read_csv(DATA_FILE, dtype={"county_fips": str})
    data["county_fips"] = data["county_fips"].str.zfill(5)
    data = data.sort_values(["county_fips", "year"])

    # Only call it annual growth if the previous observation is one year earlier.
    previous_price = data.groupby("county_fips")["home_value"].shift(1)
    previous_year = data.groupby("county_fips")["year"].shift(1)
    data["price_change_pct"] = (data["home_value"] / previous_price - 1) * 100
    data.loc[data["year"] - previous_year != 1, "price_change_pct"] = float("nan")

    # We'll see these values once real permits data is added.
    for lag in [2, 3]:
        previous_permits = data.groupby("county_fips")["permits"].shift(lag)
        lagged_year = data.groupby("county_fips")["year"].shift(lag)
        data[f"permits_lag_{lag}"] = previous_permits
        data.loc[data["year"] - lagged_year != lag, f"permits_lag_{lag}"] = float("nan")

    return data
