# Housing prices compared with local weather patterns and housing permits.
We want to see how local weather, unemployment rates and issued housing permits compare with real estate prices in a specific area.

## Team Members

| Name | GitHubID | Role / Focus |
| --- | --- | --- |
| Mikhail Vostrikov | `https://github.com/riceb53/House_price/tree/mikhail` | Zillow price data, ETL & report lead |
| Gaziz Makhanov | `https://github.com/riceb53/House_price/tree/building-permits` | HUD permits API ingestion & FastAPI endpoints |
| Jagriti Bisen | `https://github.com/riceb53/House_price/tree/feature/noaa-ingest` | NOAA weather data ingestion & Streamlit app dashboard |
| Armand Domalewski | `https://github.com/armanddomalewski/feature-etl-merge` | ETL lead, FRED unemployment scraping (Playwright), & pipeline merge |
| Brian Rice | `feature/reorganization` | DevOps / Infrastructure, GCP Cloud Run/Scheduler, Docker, & repo setup |
---

## Problem Statement
In our group, as we were choosing our topic, one of the jokes we made was about the 7% mortgage intrest rates and insane pricess across the US. And so we decided to make our project about real estate and whether building new housing increases supply and eases prices, or if new developments attract high earners and push prices up further. Does the weather in the area impact housing cost and how do unemployment rates play into all this.

Our permit data will be a little outdated, but should still provide a good understanding. By combining it with home values, weather stats, and local unemployment rates, we want to seee how new residential building impact home prices over time.

---


---

## Data Sources and Integration Goal

### Sources
| # | Source & Link | Method | What it contains | Update frequency | Access requirements |
| --- | --- | --- | --- | --- | --- |
| 1 | [Zillow Research](https://www.zillow.com/research/data/) | File | Monthly home price index values per county since the 2000 | Monthly | Free download, no key |
| 2 | [HUD Residential Construction Permits](https://services.arcgis.com/VTyQ9soqVukalItT/arcgis/rest/services/Residential_Construction_Permits_by_County/FeatureServer/24/query?outFields=*&where=1%3D1&f=geojson) | API | Annual building permit counts by house type: single-family, 2-unit, 3–4 unit, 5+ unit per county | Yearly | Free download, no key |
| 3 | [NOAA Climate Data](https://www.ncei.noaa.gov/pub/data/cirs/climdiv/) | File | Monthly average temperature and total preciptation per county since 1895 | Monthly | Free download, no key |
| 4 | [FRED County Unemployment](https://fred.stlouisfed.org/data/CASANF0URN) | Scraped | Monthly county unemployment rate tables | Monthly | Free download, no key |


### Integration Goal
We join all four datasets on 5-digit county FIPS codes and the year. Monthly Zillow price index values, NOAA weather metrics, and FRED unemployment rates are transformed to fit on one table and map.

---

## Setup Instructions (Locally)

### Prerequisites
- Python 3.11+
- A GCP service account key with access to PROJECT/BUCKET/DATASET
- Any source API keys listed in the table below

### 1. Clone the repository
```bash
git clone https://github.com/ORG/REPO.git
cd REPO
```

### 2. Configure environment variables
Copy the example file and fill in your own values:

```bash
cp .env_template .env
```

| Variable | Description | Example |
| --- | --- | --- |
| `GCP_SERVICE_ACCOUNT_KEY` | Absolute path to your service account JSON | `/Users/you/.ssh/key.json` |
| `SOURCE_API_KEY` | Key for SOURCE NAME (free tier) | `abc123...` |
| `API_SERVICE_URL` | Where the web app reaches the API | `http://api-server:8000` |

### 4. How to call your endpoint
To start the API server,
```python
fastapi run mycode.py
```

```python
requests.post("http://localhost:8000/something", json=something)
```
Make sure it writes the data in the bucket.

---
## Repository Structure
```
.
├── your_code.py
├── .env_template
└── README.md
```
