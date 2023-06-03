import numpy as np
import pandas as pd
import requests
import urllib.parse
import json
import os

from datetime import datetime
from google.oauth2.service_account import Credentials

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException

target_table = "real_estate.jakarta"
target_table_2 = "real_estate.most_recent"
project_id = "jakarta-housing-price"
credential_file = os.environ["BIGQUERY_CREDENTIALS"]
credential = Credentials.from_service_account_file(credential_file)
job_location = "asia-southeast2"

df = pd.read_csv("cleaned_data.csv")
most_recent = pd.read_csv("most_recent_data.csv")

schema = [
    {"name": "date", "type": "DATE"},
    {"name": "title", "type": "STRING"},
    {"name": "link", "type": "STRING"},
    {"name": "location", "type": "STRING"},
    {"name": "latitude", "type": "FLOAT64"},
    {"name": "longitude", "type": "FLOAT64"},
    {"name": "bedroom", "type": "FLOAT64"},
    {"name": "bathroom", "type": "FLOAT64"},
    {"name": "garage", "type": "FLOAT64"},
    {"name": "land_m2", "type": "FLOAT64"},
    {"name": "building_m2", "type": "FLOAT64"},
    {"name": "price_idr", "type": "FLOAT64"},
    {"name": "monthly_payment_idr", "type": "FLOAT64"},
    {"name": "agent", "type": "STRING"}
]

df_without_timestamp = df.copy()
df_without_timestamp = df_without_timestamp.drop("scraped_timestamp", axis=1)

df_without_timestamp.to_gbq(
    destination_table=target_table,
    project_id=project_id,
    if_exists="append",
    location=job_location,
    chunksize=10_000,
    progress_bar=True,
    credentials=credential,
    table_schema=schema
)

most_recent_without_timestamp = most_recent.copy()
most_recent_without_timestamp = most_recent_without_timestamp.drop("scraped_timestamp", axis=1)

most_recent_without_timestamp.to_gbq(
    destination_table=target_table_2,
    project_id=project_id,
    if_exists="replace",
    location=job_location,
    progress_bar=True,
    credentials=credential,
    table_schema=schema
)