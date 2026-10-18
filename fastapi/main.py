from fastapi import FastAPI
from collectors.permits_api import scrape_data
from collectors.noaa_ingest import main
from collectors.zillow_api import zillow_prices


app = FastAPI()

# reference this in scheduler
@app.post("/collect/permits")
def collect_permits():
    return scrape_data()

@app.post("/collect/noaa")
def collect_noaa():
    return main()

@app.post("/collect/zillow")
def collect_zillow():
    return zillow_prices()
