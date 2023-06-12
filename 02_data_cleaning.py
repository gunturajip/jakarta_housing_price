import numpy as np
import pandas as pd
import requests
import urllib.parse
import json
import os
import re

from datetime import datetime
from google.oauth2.service_account import Credentials
from geopy.geocoders import Nominatim

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException

df = pd.read_csv("scraped_data.csv")

target_table = "real_estate.jakarta"
target_table_2 = "real_estate.most_recent"
project_id = "jakarta-housing-price"
credential_file = "jakarta-housing-price-595a9cff2797.json"
credential = Credentials.from_service_account_file(credential_file)
job_location = "asia-southeast2"

query_most_recent = pd.read_gbq(f"SELECT * FROM `{project_id}.{target_table_2}`", project_id=project_id, credentials=credential)
query_most_recent["date"] = query_most_recent["date"].dt.tz_localize(None)

month_mapping = {
    "(?i)Januari": "January",
    "(?i)Februari": "February",
    "(?i)Maret": "March",
    "(?i)April": "April",
    "(?i)Mei": "May",
    "(?i)Juni": "June",
    "(?i)Juli": "July",
    "(?i)Agustus": "August",
    "(?i)September": "September",
    "(?i)Oktober": "October",
    "(?i)November": "November",
    "(?i)Desember": "December"
}

def convert_price(price):
    number_split = price.split(" ")

    numeric = float(number_split[0].replace(",", "."))
    suffix = number_split[1]

    if "triliun" in suffix.lower():
        multiplier = 10**12
    elif "miliar" in suffix.lower():
        multiplier = 10**9
    elif "juta" in suffix.lower():
        multiplier = 10**6
    else:
        multiplier = 1

    numeric *= multiplier
    return numeric

geolocator = Nominatim(user_agent="my_user_agent")

def get_district(text):
    match = re.search(r"Bintaro.*", text)
    if match:
        text = match.group(0)

    if "Kav" in text:
        text = text.replace("Kav", "Kavling")

    cities = ["Jakarta Utara", "Jakarta Timur", "Jakarta Selatan", "Jakarta Barat", "Jakarta Pusat"]

    try:
        location = geolocator.geocode(text)
        if location is not None:
            address = location.raw["display_name"]
            for city in cities:
                if city in address:
                    district = address.split(city)[0].strip()
                    district = district.split(",")
                    district = district[-2].strip()
                    break
            result = f"{district}, {city}"
        else:
            result = np.nan
    except:
        result = np.nan

    return result

def get_latitude_longitude(text):
    if text is not None and not pd.isnull(text):
        location = geolocator.geocode(text)
        if location is not None:
            address = location.raw
            latitude = address["lat"]
            longitude = address["lon"]
            latitude_longitude = f"{latitude}, {longitude}"
        else:
            latitude_longitude = np.nan
    else:
        latitude_longitude = np.nan

    return latitude_longitude

df["Date"] = df["Date"].str.replace("Diperbarui sejak ", "").str.replace(",", "")
df["Date"] = df["Date"].replace(month_mapping, regex=True)
df["Date"] = pd.to_datetime(df["Date"])

df["Price IDR"] = df["Price"].str.split("\n").str[0].str.replace("Rp ", "")
df["Price IDR"] = df["Price IDR"].apply(convert_price)

df["Monthly Payment IDR"] = df["Price"].str.split("\n").str[1].str.replace("Cicilan : ", "").str.replace(" per bulan", "")
df["Monthly Payment IDR"] = df["Monthly Payment IDR"].apply(convert_price)

df["Scraped Timestamp"] = pd.to_datetime(df["Scraped Timestamp"])

df = df.drop("Price", axis=1)
df = df[["Date", "Title", "Link", "Location", "Latitude", "Longitude", "Bedroom", "Bathroom", "Garage", "Land m2", "Building m2", "Price IDR", "Monthly Payment IDR", "Agent", "Scraped Timestamp"]]
df.columns = df.columns.str.lower().str.replace(" ", "_")

for col in ["latitude", "longitude", "bedroom", "bathroom", "garage", "land_m2", "building_m2", "price_idr", "monthly_payment_idr"]:
    df[col] = df[col].astype(float)

df = df.drop_duplicates(subset=["title", "location", "bedroom", "bathroom", "garage", "land_m2", "building_m2"]).reset_index(drop=True)

condition = (
    (df["title"] == query_most_recent["title"][0]) &
    (df["link"] == query_most_recent["link"][0]) &
    (df["location"] == query_most_recent["address"][0]) &
    (df["agent"] == query_most_recent["agent"][0])
)

df = df[~condition]

unique_locations = pd.DataFrame({"location": df["location"].unique()})
unique_locations["district"] = unique_locations["location"].apply(get_district)
unique_locations["latitude_longitude"] = unique_locations["district"].apply(get_latitude_longitude)

merged_df = df.merge(unique_locations, on="location", how="left")
merged_df_without_null = merged_df.dropna(subset=["district"]).reset_index(drop=True)
merged_df_without_null = merged_df_without_null.rename(columns={"location": "address"})
merged_df_without_null = merged_df_without_null[["date", "title", "link", "address", "district", "latitude_longitude", "bedroom", "bathroom", "garage", "land_m2", "building_m2", "price_idr", "monthly_payment_idr", "agent", "scraped_timestamp"]]

merged_df_without_null.to_csv("cleaned_data.csv", index=False)

most_recent = merged_df_without_null[merged_df_without_null["scraped_timestamp"] == merged_df_without_null["scraped_timestamp"].min()]
most_recent.to_csv("most_recent_data.csv", index=False)