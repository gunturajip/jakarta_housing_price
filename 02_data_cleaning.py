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
from cryptography.fernet import Fernet

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException

df = pd.read_csv("scraped_data.csv")

target_table = "real_estate.jakarta"
target_table_2 = "real_estate.most_recent"
project_id = "jakarta-housing-price"
job_location = "asia-southeast2"

# Decrypt the credentials file
def decrypt_file(encrypted_file, key):
    cipher_suite = Fernet(key)
    with open(encrypted_file, "rb") as file:
        encrypted_data = file.read()
    decrypted_data = cipher_suite.decrypt(encrypted_data)
    return json.loads(decrypted_data.decode("utf-8"))

# Get the FERNET_KEY from the environment
fernet_key = os.environ.get("FERNET_KEY_2")
decrypted_credentials = decrypt_file("encryption/encrypted_data.bin", fernet_key)

credential = Credentials.from_service_account_info(decrypted_credentials)

query_most_recent = pd.read_gbq(f"SELECT * FROM `{project_id}.{target_table_2}`", project_id=project_id, credentials=credential)
query_most_recent["date"] = pd.to_datetime(query_most_recent["date"])

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
    if "Kav" in text:
        text = text.replace("Kav", "Kavling")

    cities = ["Jakarta Utara", "Jakarta Timur", "Jakarta Selatan", "Jakarta Barat", "Jakarta Pusat"]

    if "bintaro" in text.lower():
        result = "Pesanggrahan, Jakarta Selatan"
    elif "daan mogot" in text.lower():
        result = "Grogol Petamburan, Jakarta Barat"
    else:
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

df["Date"] = pd.to_datetime(df["Date"])

df["Price IDR"] = df["Price"].str.split("\n").str[0].str.replace("Rp ", "")
df["Price IDR"] = df["Price IDR"].apply(convert_price)

df["Monthly Payment IDR"] = df["Price"].str.split("\n").str[1].str.replace("Cicilan : ", "").str.replace(" per bulan", "")
df["Monthly Payment IDR"] = df["Monthly Payment IDR"].apply(convert_price)

df = df.drop("Price", axis=1)
df = df[["Date", "Title", "Link", "Address", "Bedroom", "Bathroom", "Garage", "Land m2", "Building m2", "Price IDR", "Monthly Payment IDR", "Agent"]]
df.columns = df.columns.str.lower().str.replace(" ", "_")

for col in ["bedroom", "bathroom", "garage", "land_m2", "building_m2", "price_idr", "monthly_payment_idr"]:
    df[col] = df[col].astype(float)

df = df.drop_duplicates(subset=["title", "address", "bedroom", "bathroom", "garage", "land_m2", "building_m2"]).reset_index(drop=True)

condition = (
    (df["title"] == query_most_recent["title"][0]) &
    (df["link"] == query_most_recent["link"][0]) &
    (df["address"] == query_most_recent["address"][0]) &
    (df["agent"] == query_most_recent["agent"][0])
)

df = df[~condition]

jkt_districts = pd.read_excel("jakarta_districts.xlsx")

unique_locations = pd.DataFrame({"address": df["address"].unique()})
unique_locations["district"] = unique_locations["address"].apply(get_district)
unique_locations["district"] = unique_locations["district"].str.replace(r"(?i)\b(kec(?:amatan)?|kec)\b\.?|^\.|\.$", "", regex=True).str.strip()

updated_unique_locations = unique_locations.merge(jkt_districts, left_on="district", right_on="district_city", how="inner")
updated_unique_locations = updated_unique_locations[["address", "district_x", "kemendagri_code", "latitude_longitude"]]
updated_unique_locations = updated_unique_locations.rename(columns={"district_x": "district"})

merged_df = df.merge(updated_unique_locations, on="address", how="inner").reset_index(drop=True)
merged_df = merged_df[["date", "title", "link", "address", "district", "kemendagri_code", "latitude_longitude", "bedroom", "bathroom", "garage", "land_m2", "building_m2", "price_idr", "monthly_payment_idr", "agent"]]

merged_df.to_csv("cleaned_data.csv", index=False)

most_recent = merged_df.head(1)
most_recent.to_csv("most_recent_data.csv", index=False)