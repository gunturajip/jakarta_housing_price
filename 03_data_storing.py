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
fernet_key = os.environ.get("FERNET_KEY").encode()
decrypted_credentials = decrypt_file("encryption/encrypted_data.bin", fernet_key)

credential = Credentials.from_service_account_info(decrypted_credentials)

df = pd.read_csv("cleaned_data.csv")
df["date"] = pd.to_datetime(df["date"])

most_recent = pd.read_csv("most_recent_data.csv")
most_recent["date"] = pd.to_datetime(most_recent["date"])

schema = [
    {"name": "date", "type": "DATETIME"},
    {"name": "title", "type": "STRING"},
    {"name": "link", "type": "STRING"},
    {"name": "address", "type": "STRING"},
    {"name": "district", "type": "STRING"},
    {"name": "kemendagri_code", "type": "STRING"},
    {"name": "latitude_longitude", "type": "STRING"},
    {"name": "bedroom", "type": "FLOAT64"},
    {"name": "bathroom", "type": "FLOAT64"},
    {"name": "garage", "type": "FLOAT64"},
    {"name": "land_m2", "type": "FLOAT64"},
    {"name": "building_m2", "type": "FLOAT64"},
    {"name": "price_idr", "type": "FLOAT64"},
    {"name": "monthly_payment_idr", "type": "FLOAT64"},
    {"name": "agent", "type": "STRING"}
]

df.to_gbq(
    destination_table=target_table,
    project_id=project_id,
    if_exists="append",
    location=job_location,
    chunksize=10_000,
    progress_bar=True,
    credentials=credential,
    table_schema=schema
)

most_recent.to_gbq(
    destination_table=target_table_2,
    project_id=project_id,
    if_exists="replace",
    location=job_location,
    progress_bar=True,
    credentials=credential,
    table_schema=schema
)

df_original = pd.read_gbq(f"SELECT * FROM `{project_id}.{target_table}`", project_id=project_id, credentials=credential)
df_original["date"] = pd.to_datetime(df_original["date"])

print(f"Number of rows before removing duplicates\t: {len(df_original)}")

df_original = df_original.drop_duplicates(subset=df_original.columns[1:-1]).reset_index(drop=True)

df_original.to_gbq(
    destination_table=target_table,
    project_id=project_id,
    if_exists="replace",
    location=job_location,
    chunksize=10_000,
    progress_bar=True,
    credentials=credential,
    table_schema=schema
)

print(f"Number of rows after removing duplicates\t: {len(df_original)}")
print(f"Number of duplicate rows\t\t\t: {len(df_original[df_original.duplicated()])}")