"""County housing dashboard using data stored in Google Cloud Storage."""

import io

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from google.cloud import storage

st.set_page_config(page_title="County Housing Explorer", layout="wide")
st.title("County Housing Explorer")
st.caption("Housing prices, building permits, and weather across US counties")

BUCKET = "house_prices_bucket"
PROJECT = "houseprice-510122"
COUNTY_MAP = "https://raw.githubusercontent.com/plotly/datasets/master/geojson-counties-fips.json"


@st.cache_data
def read_file(filename, fips_column="fips"):
    # Read each CSV directly from Google Cloud Storage, not from the Mac.
    client = storage.Client(project=PROJECT)
    blob = client.bucket(BUCKET).blob(filename)
    df = pd.read_csv(io.BytesIO(blob.download_as_bytes()), dtype={fips_column: str})
    df[fips_column] = df[fips_column].str.zfill(5)
    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    return df.dropna(subset=["year"])


def line_graph(df, column, y_label):
    # Use readable axis titles instead of CSV column names.
    if df[column].notna().sum() == 0:
        st.info("No data available for this graph yet.")
        return
    fig = px.line(df.sort_values("year"), x="year", y=column, markers=True,
                  labels={"year": "Year", column: y_label})
    fig.update_xaxes(tickformat="d", dtick=5)  # 2020 instead of 2,020 or 2020.0
    fig.update_layout(height=320, margin=dict(l=0, r=0, t=15, b=0))
    st.plotly_chart(fig, use_container_width=True, key=f"chart_{key}")


def scatter_graph(df, x, y, x_label, y_label):
    if df.dropna(subset=[x, y]).empty:
        st.info("No data available for this graph yet.")
        return
    fig = px.scatter(df, x=x, y=y, labels={x: x_label, y: y_label})
    fig.update_layout(height=320, margin=dict(l=0, r=0, t=15, b=0))
    st.plotly_chart(fig, use_container_width=True)


# Load Zillow and NOAA from the team's GCP bucket.
try:
    zillow = read_file("zillow_county_yearly.csv")
    weather = read_file("weather_county_year.csv", "county_fips")
except Exception as error:
    st.error(f"Could not load Zillow or weather from GCP: {error}")
    st.info("Sign in on your Mac using: gcloud auth application-default login")
    st.stop()

# Only complete calendar years are included in the dashboard.
zillow = zillow[zillow["year"] <= 2025].copy()
weather = weather[weather["year"] <= 2025].copy()
weather = weather.rename(columns={"county_fips": "fips"})
if "weather_complete_year" in weather.columns:
    weather = weather[weather["weather_complete_year"] == True]

# Match yearly housing prices with weather using county FIPS and year.
data = zillow.merge(
    weather[["fips", "year", "avg_temp_f", "total_precip_in"]],
    on=["fips", "year"], how="left"
)
data = data.sort_values(["fips", "year"])
data["price_change_pct"] = data.groupby("fips")["avg_home_value"].pct_change(fill_method=None) * 100

# Permits are optional for now, until the formatted CSV is in GCP.
try:
    permits = read_file("permits_formatted.csv")
    permits["permits"] = pd.to_numeric(permits["permits"], errors="coerce")
    permits = permits.groupby(["fips", "year"], as_index=False)["permits"].sum(min_count=1)
    data = data.merge(permits, on=["fips", "year"], how="left")
    has_permits = True
except Exception:
    permits = pd.DataFrame(columns=["fips", "year", "permits"])
    data["permits"] = float("nan")
    has_permits = False

# Keep the main filters. The residential permits map also has its own year slider.
states = sorted(data["state"].dropna().unique())
state_index = states.index("CA") if "CA" in states else 0
state = st.sidebar.selectbox("State", states, index=state_index)
county_list = data[data["state"] == state][["fips", "county"]].drop_duplicates().sort_values("county")
county_choices = {row.county: row.fips for row in county_list.itertuples(index=False)}
names = list(county_choices)
county_index = names.index("San Francisco County") if "San Francisco County" in names else 0
county = st.sidebar.selectbox("County", names, index=county_index)
fips = county_choices[county]
years = sorted(data["year"].astype(int).unique())
year = st.sidebar.select_slider("Year", options=years, value=years[-1])
lag = st.sidebar.radio("Permit lag (years)", [2, 3], index=1, horizontal=True)

county_data = data[data["fips"] == fips].sort_values("year")
selected = county_data[county_data["year"] == year]

tab1, tab2, tab3 = st.tabs(["County Explorer", "Permits vs. Prices", "Weather & Housing"])

with tab1:
    st.subheader(f"{county}, {state} — {year}")
    if selected.empty:
        st.warning("No data for this county in the selected year.")
    else:
        row = selected.iloc[0]
        a, b, c = st.columns(3)
        a.metric("Average Home Value", f"${row['avg_home_value']:,.0f}")
        b.metric("Annual Home Value Change", f"{row['price_change_pct']:.1f}%" if pd.notna(row["price_change_pct"]) else "N/A")
        c.metric("Residential Permits", f"{row['permits']:,.0f}" if pd.notna(row["permits"]) else "N/A")
        a.metric("Average Temperature", f"{row['avg_temp_f']:.1f} °F" if pd.notna(row["avg_temp_f"]) else "N/A")
        b.metric("Annual Precipitation", f"{row['total_precip_in']:.1f} in" if pd.notna(row["total_precip_in"]) else "N/A")

    a, b = st.columns(2)
    with a:
        st.write("**Average Home Value Over Time**")
        line_graph(county_data, "avg_home_value", "Average Home Value ($)")
    with b:
        st.write("**Annual Home Value Change**")
        line_graph(county_data, "price_change_pct", "Home Value Change (%)")

    st.subheader(f"US Housing Prices — {year}")
    all_counties = data[data["year"] == year]
    fig = go.Figure(go.Choropleth(
        geojson=COUNTY_MAP, locations=all_counties["fips"],
        z=all_counties["avg_home_value"],
        text=all_counties["county"] + ", " + all_counties["state"],
        colorscale="Blues", colorbar_title="Average Home Value ($)",
    ))
    fig.update_geos(scope="usa")
    fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=430)
    st.plotly_chart(fig, use_container_width=True)

    # Always show the 10-year map. No expandable dropdown.
    st.subheader(f"10-Year Home Value Change — {year - 10} to {year}")
    before = data[data["year"] == year - 10][["fips", "avg_home_value"]].rename(
        columns={"avg_home_value": "old_value"})
    now = all_counties.merge(before, on="fips", how="inner")
    now = now[now["old_value"] > 0].copy()
    now["ten_year_change"] = (now["avg_home_value"] / now["old_value"] - 1) * 100
    if now.empty:
        st.info("Not enough data from 10 years earlier to display this map.")
    else:
        fig = go.Figure(go.Choropleth(
            geojson=COUNTY_MAP, locations=now["fips"], z=now["ten_year_change"],
            text=now["county"] + ", " + now["state"],
            colorscale="RdYlGn", colorbar_title="10-Year Change (%)",
        ))
        fig.update_geos(scope="usa")
        fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=430)
        st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.subheader("Building Permits vs. Housing Prices")

    # Keep the original independent Year slider above the permits map.
    if has_permits and not permits.empty:
        min_year = int(permits["year"].min())
        max_year = int(permits["year"].max())
    else:
        min_year, max_year = 1980, 2022
    permits_year = st.slider("Year", min_year, max_year, max_year, key="permits_map_year")

    if not has_permits:
        st.info("Permits charts will appear when permits_formatted.csv is available in GCP.")
    else:
        # This map uses its own slider; the county charts still use sidebar filters.
        permits_map = permits[permits["year"] == permits_year]
        st.write(f"**Residential Permits Across US Counties — {permits_year}**")
        if permits_map.empty:
            st.info("No permits data for this year.")
        else:
            fig = go.Figure(go.Choropleth(
                geojson=COUNTY_MAP, locations=permits_map["fips"], z=permits_map["permits"],
                colorscale="Blues", colorbar_title="Number of Permits",
            ))
            fig.update_geos(scope="usa")
            fig.update_layout(height=430, margin=dict(l=0, r=0, t=0, b=0))
            st.plotly_chart(fig, use_container_width=True)

        a, b = st.columns(2)
        with a:
            st.write("**Residential Permits Over Time**")
            line_graph(county_data, "permits", "Number of Permits")
        with b:
            st.write("**Average Home Value Over Time**")
            line_graph(county_data, "avg_home_value", "Average Home Value ($)")

        # Shift permits into the year when we want to compare home-value changes.
        earlier_permits = permits.copy()
        earlier_permits["year"] = earlier_permits["year"] + lag
        earlier_permits = earlier_permits.rename(columns={"permits": "earlier_permits"})
        comparison = data.merge(earlier_permits, on=["fips", "year"], how="left")
        comparison = comparison[comparison["year"] == year]
        st.write(f"**Permits {lag} Years Earlier vs. Home Value Change in {year}**")
        scatter_graph(comparison, "earlier_permits", "price_change_pct",
                      "Permits Issued Earlier", "Annual Home Value Change (%)")
        st.caption("Each point represents a county. A relationship does not prove cause and effect.")

with tab3:
    st.subheader(f"Weather & Housing — {county}, {state}")
    a, b = st.columns(2)
    with a:
        st.write("**Average Annual Temperature**")
        line_graph(county_data, "avg_temp_f", "Average Temperature (°F)")
        st.write("**Total Annual Precipitation**")
        line_graph(county_data, "total_precip_in", "Precipitation (inches)")
    with b:
        st.write("**Annual Home Value Change**")
        line_graph(county_data, "price_change_pct", "Home Value Change (%)")
        st.write("**Temperature vs. Home Value Change**")
        scatter_graph(county_data, "avg_temp_f", "price_change_pct",
                      "Average Temperature (°F)", "Annual Home Value Change (%)")
    st.caption("Weather provides context; these charts do not establish causation.")

