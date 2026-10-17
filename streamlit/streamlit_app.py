import io
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from google.cloud import storage

st.set_page_config(page_title="County Housing Explorer", layout="wide")
st.title("County Housing Explorer")
st.caption("Housing prices, building permits and weather across US counties")

bucket = "house_prices_bucket"
project = "houseprice-510122"
map_url = "https://raw.githubusercontent.com/plotly/datasets/master/geojson-counties-fips.json"


@st.cache_data
def getcsv(name, fipscol="fips"):
    # getting the csv from gcp
    client = storage.Client(project=project)
    file = client.bucket(bucket).blob(name)
    df = pd.read_csv(io.BytesIO(file.download_as_bytes()), dtype={fipscol: str})
    df[fipscol] = df[fipscol].str.zfill(5)
    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df = df.dropna(subset=["year"])
    df["year"] = df["year"].astype(int)
    return df


def linechart(df, col, label, k):
    if df[col].notna().sum() == 0:
        st.info("No data for this chart yet")
        return
    fig = px.line(df.sort_values("year"), x="year", y=col, markers=True,
                  labels={"year": "Year", col: label})
    fig.update_xaxes(tickformat="d", dtick=5)
    st.plotly_chart(fig, use_container_width=True, key=k)


def dots(df, x, y, xname, yname, k):
    if df[[x, y]].dropna().empty:
        st.info("No data for this chart yet")
        return
    fig = px.scatter(df, x=x, y=y, labels={x: xname, y: yname})
    st.plotly_chart(fig, use_container_width=True, key=k)


try:
    zillow = getcsv("zillow_county_yearly.csv")
    weather = getcsv("weather_county_year.csv", "county_fips")
except Exception as e:
    st.error(f"Could not read the files from GCP: {e}")
    st.info("Try running gcloud auth application-default login")
    st.stop()

zillow = zillow[zillow.year <= 2025].copy()
weather = weather[weather.year <= 2025].copy()
weather = weather.rename(columns={"county_fips": "fips"})
weather = weather[weather.weather_complete_year == True]

# join the weather and house prices using fips and year
df = zillow.merge(weather[["fips", "year", "avg_temp_f", "total_precip_in"]],
                  on=["fips", "year"], how="left")
df = df.sort_values(["fips", "year"])
df["price_change_pct"] = df.groupby("fips")["avg_home_value"].pct_change(fill_method=None) * 100

try:
    permits = getcsv("permits_formatted.csv")
    permits["permits"] = pd.to_numeric(permits["permits"], errors="coerce")
    permits = permits.groupby(["fips", "year"], as_index=False)["permits"].sum(min_count=1)
    df = df.merge(permits, on=["fips", "year"], how="left")
except Exception:
    permits = pd.DataFrame(columns=["fips", "year", "permits"])
    df["permits"] = float("nan")

states = sorted(df.state.dropna().unique())
state = st.sidebar.selectbox("State", states, index=states.index("CA") if "CA" in states else 0)

counties = df[df.state == state][["county", "fips"]].drop_duplicates().sort_values("county")
names = dict(zip(counties.county, counties.fips))
county = st.sidebar.selectbox("County", list(names),
                              index=list(names).index("San Francisco County") if "San Francisco County" in names else 0)
fips = names[county]
county_df = df[df.fips == fips].sort_values("year")

# 10 year map needs data going back 10 years
years = sorted(county_df[county_df.year >= 2010].year.unique())
year = st.sidebar.select_slider("Year", options=years, value=years[-1])
selected = county_df[county_df.year == year].iloc[0]

lags = [n for n in [2, 3] if year - n in set(permits.year)]
lag = st.sidebar.radio("Permit lag (years)", lags, horizontal=True) if lags else None

tab1, tab2, tab3 = st.tabs(["County Explorer", "Permits vs. Prices", "Weather & Housing"])

with tab1:
    st.subheader(f"{county}, {state} - {year}")
    a, b, c = st.columns(3)
    a.metric("Average Home Value", f"${selected.avg_home_value:,.0f}")
    b.metric("Annual Home Value Change", f"{selected.price_change_pct:.1f}%" if pd.notna(selected.price_change_pct) else "N/A")
    c.metric("Residential Permits", f"{selected.permits:,.0f}" if pd.notna(selected.permits) else "N/A")
    a.metric("Average Temperature", f"{selected.avg_temp_f:.1f} °F" if pd.notna(selected.avg_temp_f) else "N/A")
    b.metric("Annual Precipitation", f"{selected.total_precip_in:.1f} in" if pd.notna(selected.total_precip_in) else "N/A")

    a, b = st.columns(2)
    with a:
        st.write("**Average Home Value Over Time**")
        linechart(county_df, "avg_home_value", "Average Home Value ($)", "home1")
    with b:
        st.write("**Annual Home Value Change**")
        linechart(county_df, "price_change_pct", "Home Value Change (%)", "price1")

    all_data = df[df.year == year]
    # beginning of ai code
    st.subheader(f"US Housing Prices - {year}")
    fig = go.Figure(go.Choropleth(geojson=map_url, locations=all_data.fips,
                                  z=all_data.avg_home_value,
                                  text=all_data.county + ", " + all_data.state,
                                  colorscale="Blues", colorbar_title="Average Home Value ($)"))
    fig.update_geos(scope="usa")
    fig.update_layout(height=430, margin=dict(l=0, r=0, t=0, b=0))
    st.plotly_chart(fig, use_container_width=True, key="us_prices")

    old = df[df.year == year - 10][["fips", "avg_home_value"]]
    old = old.rename(columns={"avg_home_value": "old_price"})
    ten = all_data.merge(old, on="fips")
    ten = ten[ten.old_price > 0].copy()
    if not ten.empty:
        ten["change"] = (ten.avg_home_value / ten.old_price - 1) * 100
        st.subheader(f"10-Year Home Value Change - {year - 10} to {year}")
        fig = go.Figure(go.Choropleth(geojson=map_url, locations=ten.fips,
                                      z=ten.change, text=ten.county + ", " + ten.state,
                                      colorscale="RdYlGn", colorbar_title="10-Year Change (%)"))
        fig.update_geos(scope="usa")
        fig.update_layout(height=430, margin=dict(l=0, r=0, t=0, b=0))
        st.plotly_chart(fig, use_container_width=True, key="ten_year_map")
    # end of ai code

with tab2:
    st.subheader("Building Permits vs. Housing Prices")
    common_years = sorted(set(permits.year) & set(df.year))
    if not common_years:
        st.info("Permits will show here once permits_formatted.csv is uploaded to GCP")
    else:
        py = st.select_slider("Year", options=common_years, value=common_years[-1], key="permit_year")
        pm = permits[permits.year == py]
        # more ai code to make a map
        st.write(f"**Residential Permits Across US Counties - {py}**")
        fig = go.Figure(go.Choropleth(geojson=map_url, locations=pm.fips,
                                      z=pm.permits, colorscale="Blues",
                                      colorbar_title="Number of Permits"))
        fig.update_geos(scope="usa")
        fig.update_layout(height=430, margin=dict(l=0, r=0, t=0, b=0))
        st.plotly_chart(fig, use_container_width=True, key="permit_map")
        # end of more ai code

        a, b = st.columns(2)
        with a:
            st.write("**Residential Permits Over Time**")
            linechart(county_df, "permits", "Number of Permits", "permit_line")
        with b:
            st.write("**Average Home Value Over Time**")
            linechart(county_df, "avg_home_value", "Average Home Value ($)", "home2")

        if lag:
            # comparing permits from a few years before
            prev = permits.copy()
            prev["year"] = prev.year + lag
            prev = prev.rename(columns={"permits": "old_permits"})
            comp = df.merge(prev, on=["fips", "year"], how="left")
            comp = comp[comp.year == year]
            st.write(f"**Permits {lag} Years Earlier vs. Home Value Change in {year}**")
            dots(comp, "old_permits", "price_change_pct", "Permits Issued Earlier",
                 "Annual Home Value Change (%)", "lag_dots")
            st.caption("Each dot is a county. This doesn't prove cause and effect")

with tab3:
    st.subheader(f"Weather & Housing - {county}, {state}")
    a, b = st.columns(2)
    with a:
        st.write("**Average Annual Temperature**")
        linechart(county_df, "avg_temp_f", "Average Temperature (°F)", "temp_line")
        st.write("**Total Annual Precipitation**")
        linechart(county_df, "total_precip_in", "Precipitation (inches)", "rain_line")
    with b:
        st.write("**Annual Home Value Change**")
        linechart(county_df, "price_change_pct", "Home Value Change (%)", "price2")
        st.write("**Temperature vs. Home Value Change**")
        dots(county_df, "avg_temp_f", "price_change_pct", "Average Temperature (°F)",
             "Annual Home Value Change (%)", "weather_dots")
    st.caption("Weather may be related to prices, but these charts don't show causation")
