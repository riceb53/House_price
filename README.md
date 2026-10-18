# Housing prices compared with local weather patterns and housing permits.
We want to see how local weather, unemployment rates and issued housing permits compare with real estate prices in a specific area.

## Team Members

| Name | GitHubID | Role / Focus |
| --- | --- | --- |
| Mikhail Vostrikov  | `https://github.com/riceb53/House_price/tree/mikhail` | Zillow price data, ETL & reporting |
| Gaziz Makhanov | `https://github.com/riceb53/House_price/tree/building-permits` | HUD permits API ingestion & FastAPI endpoints |
| Jagriti Bisen | `https://github.com/riceb53/House_price/tree/feature/noaa-ingest` | NOAA weather data ingestion & Streamlit app dashboard |
| Armand Domalewski | `https://github.com/riceb53/House_price/tree/feature/etl-merge` | ETL lead, FRED unemployment scraping (Playwright), & pipeline merge |
| Brian Rice | `https://github.com/riceb53/House_price/tree/feature/reorganization` | DevOps / Infrastructure, GCP Cloud Run/Scheduler, Docker, & repo setup |

---

## Problem Statement
In our group, as we were choosing our topic, one of the jokes we made was about the 7% mortgage interest rates and high prices across the US. And so we decided to make our project about real estate and whether building new housing increases supply and eases prices, or if new developments attract high earners and push prices up further. Does the weather in the area impact housing cost and how do unemployment rates play into all this.

Our permit data will be a little outdated, but should still provide a good understanding. By combining it with home values, weather stats, and local unemployment rates, we want to see how nnew residential construction impacts home prices over time.

---


---

## Data Sources and Integration Goal

### Sources
| # | Source & Link | Method | What it contains | Update frequency | Access requirements |
| --- | --- | --- | --- | --- | --- |
| 1 | [Zillow Research](https://www.zillow.com/research/data/) | File | Monthly home price index values per county since 2000 | Monthly | Free download, no key |
| 2 | [HUD Residential Construction Permits](https://services.arcgis.com/VTyQ9soqVukalItT/arcgis/rest/services/Residential_Construction_Permits_by_County/FeatureServer/24/query?outFields=*&where=1%3D1&f=geojson) | API | Annual building permit counts by house type: single-family, 2-unit, 3–4 unit, 5+ unit per county | Yearly | Free download, no key |
| 3 | [NOAA Climate Data](https://www.ncei.noaa.gov/pub/data/cirs/climdiv/) | File | Monthly average temperature and total precipitation per county since 1895 | Monthly | Free download, no key |
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
git clone https://github.com/riceb53/House_price.git
cd House_price
```

### 2. Configure environment variables
Copy the example file and fill in your own values:

```bash
cp fastapi/.env_template fastapi/.env
```

| Variable | Description | Example |
| --- | --- | --- |
| `GCP_PROJECT_ID` | GCP Project Id | `dsai692-section1123` |
| `GCS_BUCKET_NAME` | GCS Bucket name | `some_example_bucket_name_house_price` |
| `GCP_SERVICE_ACCOUNT_KEY` | GCP Service account key | `some_example_bucket_name_house_price` |

### 3. How to call your endpoint
To start the API server,
```python
fastapi run fastapi/main.py
```

```python
requests.post("http://localhost:8000/collect/permits")
```
Make sure it writes the data in the bucket.

### 4. Streamlit app
To start the API server,
```
streamlit run streamlit/streamlit_app.py
```
Then visit localhost:8501 in your browser


### 5. To deploy with docker and gcp
```
bash gcloud_command.sh
```

---
## Repository Structure
```
House_price
.
├── docs
│   └── noaa_weather_schema.md
├── fastapi
│   ├── collectors
│   │   ├── __init__.py
│   │   ├── noaa_ingest.py
│   │   ├── permits_api.py
│   │   └── zillow_api.py
│   ├── Dockerfile
│   ├── main.py
│   └── requirements.txt
├── Final Report.docx
├── gcloud_command.sh
├── misc_data
│   ├── processed_noaa_weather_county_year.csv
│   └── zillow_county_yearly.csv
├── README.md
└── streamlit
    ├── Dockerfile
    ├── edited_data.xlsx
    ├── requirements.txt
    └── streamlit_app.py

```
