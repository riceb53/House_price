# NOAA weather data

processed file: processed/noaa/weather_county_year.csv
raw files: raw/noaa/<procdate>/

one row for each county and year, starting from 1980.
we can merge this with the other data using county_fips and year.

columns:

county_fips - 5 digit county code, keep as text so zeros don't get removed
state_fips - 2 digit state code
year - year of the data
avg_temp_f - average temperature for the year in F
total_precip_in - total precipitation for the year in inches
hot_months - number of unusually hot months
cold_months - number of unusually cold months
wet_months - number of unusually wet months
dry_months - number of unusually dry months
temp_months_valid - number of months with temperature data
precip_months_valid - number of months with precipitation data
weather_complete_year - true if all 12 months have temperature and precipitation data
noaa_procdate - date of the NOAA file
ingested_at - time the data was collected

for hot, cold, wet and dry months, the code compares each month with the same month from 1991 to 2020.

notes:
- if a year is incomplete, the yearly weather values are left empty
- missing values stay empty, not zero
- NOAA county weather data covers the contiguous US, not Alaska, Hawaii or DC
- Connecticut county codes may need checking before the merge
- the processed csv is replaced when the script runs again
