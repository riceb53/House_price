from playwright.sync_api import sync_playwright
import time 
import json

unemployment_all_time =[]

def state_eid_scrape(page):
    url = "https://fred.stlouisfed.org/release/tables?rid=116&eid=253528"
    page.goto(url)
    page.wait_for_selector("td.fred-release-element a")
    state_name_eid_date = page.query_selector_all("td.fred-release-element a")
    state_eids = []
    for row in state_name_eid_date:
            state_name = row.inner_text().strip()
            state_eid_url = row.get_attribute("href")
            eid = state_eid_url.split("eid=")[-1]
            state_eids.append({"state_name": state_name, "eid": eid})
    return state_eids

        
def page_scrape(page, eid, od):
    url = f"https://fred.stlouisfed.org/release/tables?rid=116&eid={eid}&od={od}"
    page.goto(url)
    page.wait_for_selector("tr.leaf")
    data = page.query_selector_all("tr.leaf")
    current_month_year = page.query_selector("th#table-unit-subheading1").inner_text().strip()
    previous_month_year = page.query_selector("th#table-unit-subheading2").inner_text().strip()
    year_ago_month_year = page.query_selector("th#table-unit-subheading3").inner_text().strip()
    state_name = page.query_selector("h2#release-element-name-title").inner_text().strip()
    state_county_unemployment = []
    for row in data:
        county = row.query_selector("span.fred-rls-elm-nm").inner_text().strip()
        a = row.query_selector("span.fred-rls-elm-nm a")
        link = a.get_attribute("href")
        series_id = link.split("/")[-1]
        values = row.query_selector_all("td.fred-rls-elm-vl-td")
        current = values[0].inner_text().strip()
        previous_month = values[1].inner_text().strip()
        year_ago = values[2].inner_text().strip()
        state_county_unemployment.append({"state_name": state_name, "county": county,
                            "series_id": series_id,
                            "current_month_year": current_month_year, 
                            "current": current,
                            "previous_month_year": previous_month_year,
                            "previous_month": previous_month,
                            "year_ago_month_year": year_ago_month_year,
                            "year_ago": year_ago,
                            "observation_date": od})
    return state_county_unemployment


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()
    state_eids = state_eid_scrape(page)
    for row in state_eids:
        eid = row["eid"] 
        for year in range(2000, 2026):
            print(f"{row['state_name']} {year}")
            try:
                date = f"{year}-12-01"
                state_county_unemployment = page_scrape(page, eid, date)
                unemployment_all_time.extend(state_county_unemployment)    
            except Exception as e: 
                print(f"Error {e} collecting data from {row['state_name']} in {year}")
            time.sleep(1)
    print(len(unemployment_all_time))
    with open("raw_fred_data.json", "w") as f:
        json.dump(unemployment_all_time, f)
    browser.close()


