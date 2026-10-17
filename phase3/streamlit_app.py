"""Simple housing dashboard. Housing and weather are real; other data is pending."""
import os
import pandas as pd
import requests
import streamlit as st
from data_utils import load_data

st.set_page_config(page_title="County Housing Explorer", layout="wide")
st.title("County Housing Explorer")
st.caption("Housing prices, permits, weather, and unemployment")

# Read the CSV directly, or use FastAPI if API_URL is set.
try:
    api_url = os.getenv("API_URL", "")
    if api_url:
        response = requests.get(api_url.rstrip("/") + "/merged", timeout=45)
        response.raise_for_status()
        data = pd.DataFrame(response.json())
    else:
        data = load_data()
except (OSError, ValueError, requests.RequestException) as error:
    st.error(f"Could not load data: {error}")
    st.stop()

if data.empty:
    st.warning("No data found")
    st.stop()

st.info("Real Zillow + NOAA data. Permits and unemployment are not connected yet.")

# Use county FIPS because some county names exist in multiple states.
counties = data[["county_fips", "county", "state"]].drop_duplicates()
counties = counties.sort_values(["state", "county"])
county_options = {
    f"{row.county}, {row.state}": row.county_fips
    for row in counties.itertuples(index=False)
}
chosen_county = st.sidebar.selectbox("County", list(county_options))
fips = county_options[chosen_county]

years = sorted(data["year"].unique())
year = st.sidebar.select_slider("Year", options=years, value=years[-1])
lag = st.sidebar.radio("Permit lag (years)", [2, 3], horizontal=True)

county_data = data[data["county_fips"] == fips].sort_values("year")
selected = county_data[county_data["year"] == year]

first, second, third = st.tabs(["County Explorer", "Permits vs. Prices", "Weather & Economy"])

with first:
    st.subheader(f"{chosen_county} — {year}")
    if selected.empty:
        st.warning("No data for this county and year")
    else:
        row = selected.iloc[0]
        a, b, c = st.columns(3)
        a.metric("Home value", f"${row['home_value']:,.0f}")
        b.metric("Annual price change", f"{row['price_change_pct']:.1f}%" if pd.notna(row["price_change_pct"]) else "N/A")
        c.metric("Annual permits", f"{row['permits']:,.0f}" if pd.notna(row["permits"]) else "N/A")
        a.metric("Unemployment", f"{row['unemployment_rate']:.1f}%" if pd.notna(row["unemployment_rate"]) else "N/A")
        b.metric("Temperature", f"{row['temp_f']:.1f} °F" if pd.notna(row["temp_f"]) else "N/A")
        c.metric("Precipitation", f"{row['precip_in']:.1f} in" if pd.notna(row["precip_in"]) else "N/A")

    st.subheader("County locations")
    if data[["lat", "lon"]].notna().all(axis=1).any():
        locations = data[data["year"] == year].dropna(subset=["lat", "lon"])
        st.map(locations.rename(columns={"lat": "latitude", "lon": "longitude"}))
    else:
        st.caption("Map will appear when county coordinates are added.")

    st.subheader("Trends")
    a, b = st.columns(2)
    with a:
        st.write("Home values")
        st.line_chart(county_data, x="year", y="home_value")
    with b:
        st.write("Temperature")
        st.line_chart(county_data, x="year", y="temp_f")

with second:
    st.subheader("Permits vs. Prices")
    st.write("Home values over time")
    st.line_chart(county_data, x="year", y="home_value")
    if data["permits"].notna().any():
        st.write("Annual permits")
        st.line_chart(county_data, x="year", y="permits")
        st.write(f"Permits {lag} years earlier vs. annual price change")
        st.scatter_chart(data, x=f"permits_lag_{lag}", y="price_change_pct")
    else:
        st.info("Permits charts will be available after we add permits.geojson.")

with third:
    st.subheader("Weather & Economy")
    a, b = st.columns(2)
    with a:
        st.write("Average temperature")
        st.line_chart(county_data, x="year", y="temp_f")
        st.write("Annual precipitation")
        st.line_chart(county_data, x="year", y="precip_in")
    with b:
        st.write("Annual housing price change")
        st.line_chart(county_data, x="year", y="price_change_pct")
        if data["unemployment_rate"].notna().any():
            st.write("Unemployment")
            st.line_chart(county_data, x="year", y="unemployment_rate")
        else:
            st.info("Unemployment chart will appear when that source is available.")

st.subheader("Data table")
st.dataframe(county_data, hide_index=True, use_container_width=True)
