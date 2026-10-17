import io

import pandas as pd
import requests
import streamlit as st
import plotly.graph_objects as go
from google.cloud import storage



# download from gcs
client = storage.Client(project="houseprice-510122")
blob = client.bucket("house_prices_bucket").blob("zillow_county_yearly.csv")
data = io.StringIO(blob.download_as_text())
df = pd.read_csv(data, dtype={"fips": str})

most_recent_year = df[df["year"] == df["year"].max()]


# beginning of ai code
fig = go.Figure(go.Choropleth(
    geojson="https://raw.githubusercontent.com/plotly/datasets/master/geojson-counties-fips.json",
    locations=most_recent_year["fips"],
    z=most_recent_year["avg_home_value"],
    text=most_recent_year["county"] + ", " + most_recent_year["state"],
    colorscale="Viridis",    
    zmin=most_recent_year["avg_home_value"].quantile(0.05),
    zmax=most_recent_year["avg_home_value"].quantile(0.95),
))

fig.update_layout(geo_scope="usa")
st.plotly_chart(fig)


end = df["year"].max()
start = end - 10

wide = df[df["year"].isin([start, end])].pivot_table(
    index=["fips", "county", "state"], columns="year", values="avg_home_value"
).dropna().reset_index()
wide["pct_change"] = (wide[end] / wide[start] - 1) * 100

fig3 = go.Figure(go.Choropleth(
    geojson="https://raw.githubusercontent.com/plotly/datasets/master/geojson-counties-fips.json",
    locations=wide["fips"],
    z=wide["pct_change"],
    text=wide["county"] + ", " + wide["state"],
    colorscale="RdYlGn",
    zmin=wide["pct_change"].quantile(0.05),
    zmax=wide["pct_change"].quantile(0.95),
    colorbar_title="% change",
))
fig3.update_layout(geo_scope="usa", title=f"Home Value % Change, {start}–{end}")
st.plotly_chart(fig3)


# end of ai code



blob = client.bucket("house_prices_bucket").blob("permits_formatted.csv")
data = io.StringIO(blob.download_as_text())
permit_data = pd.read_csv(data, dtype={"fips": str})


# more ai code to make a chart
year = st.slider("Year", 1980, 2022, 2022)
p = permit_data[permit_data["year"] == year]
zmax = permit_data["permits"].quantile(0.95) 
fig = go.Figure(go.Choropleth(
    geojson="https://raw.githubusercontent.com/plotly/datasets/master/geojson-counties-fips.json",
    locations=p["fips"],
    z=p["permits"],
    colorscale="Blues",
    # zmin=0,
    # zmax=p["permits"].quantile(0.95),
    zmin=0,
    zmax=zmax,
    colorbar_title="Permits",
))
fig.update_layout(geo_scope="usa", title=f"Residential Permits, {year}")
st.plotly_chart(fig)


# end of more ai code to make a chart


bucket = client.bucket("house_prices_bucket")
blob = bucket.blob("weather_county_year.csv")

data = io.StringIO(blob.download_as_text())
weather = pd.read_csv(data, dtype={"county_fips": str})
weather = weather.rename(columns={"county_fips": "fips"})

permits = permit_data.groupby("year")["permits"].sum()
price = df.groupby("year")["avg_home_value"].median()

fig = go.Figure()
fig.add_trace(go.Bar(x=permits.index, y=permits.values, name="Permits (US total)"))
fig.add_trace(go.Scatter(x=price.index, y=price.values, name="Median home value", yaxis="y2"))
fig.update_layout(
    title="Building vs. Home Prices, US",
    yaxis=dict(title="Permits"),
    yaxis2=dict(title="Median home value ($)", overlaying="y", side="right"),
)
st.plotly_chart(fig)


