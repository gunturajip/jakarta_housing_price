import numpy as np
import pandas as pd
import requests
import urllib.parse
import json
import os
import re
import time
import random
import undetected_chromedriver as uc

from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials
from geopy.geocoders import Nominatim
from cryptography.fernet import Fernet

from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from seleniumbase import SB

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
fernet_key = os.environ.get("FERNET_KEY")
decrypted_credentials = decrypt_file("encryption/encrypted_data.bin", fernet_key)
credential = Credentials.from_service_account_info(decrypted_credentials)

query_most_recent = pd.read_gbq(f"SELECT * FROM `{project_id}.{target_table_2}`", project_id=project_id, credentials=credential)
query_most_recent["date"] = pd.to_datetime(query_most_recent["date"])

# Lists to Store the Scraped Data
titles = []
links = []
locations = []
prices = []
bedrooms = []
bathrooms = []
garages = []
land_areas = []
building_areas = []
agents = []
dates = []

# Iterate through Each Page
conditions_met = False

with SB(uc_cdp=True, guest_mode=True) as sb:
    for page in range(1, 101):
        try:
            sb.open(f"https://www.rumah123.com/jual/dki-jakarta/rumah/?sort=posted-desc&page={page}#qid~a46c0629-67e4-410c-9c35-0c80e98987d9")

            if sb.is_element_visible('input[value*="Verify"]'):
                sb.click('input[value*="Verify"]')
                if page == 1:
                    sb.save_screenshot("page_screenshot_before.png")
            elif sb.is_element_visible('iframe[title*="challenge"]'):
                sb.switch_to_frame('iframe[title*="challenge"]')
                sb.click("span.mark")
                if page == 1:
                    sb.save_screenshot("page_screenshot_before.png")
            else:
                if page == 1:
                    sb.save_screenshot("page_screenshot_before.png")

            property_elements = sb.find_elements(By.XPATH, "//div[contains(@class, 'card-featured__content-wrapper')]")
            print(property_elements)

            # Iterate through Each Property Element
            index = 0
            for element in property_elements:
                try:
                    # Title
                    try:
                        title_element = element.find_element(By.XPATH, ".//a[h2]")
                        title = title_element.get_attribute("title")
                    except NoSuchElementException:
                        title = float("nan")

                    # Link
                    try:
                        link = title_element.get_attribute("href")
                    except NoSuchElementException:
                        link = float("nan")

                    # Location
                    try:
                        location = element.find_element(By.XPATH, ".//span[contains(text(), ',')]").text
                    except NoSuchElementException:
                        location = float("nan")

                    # Price
                    try:
                        price = element.find_element(By.CLASS_NAME, "card-featured__middle-section__price").text
                    except NoSuchElementException:
                        price = float("nan")

                    # Features
                    features_element = element.find_elements(By.XPATH, ".//div[@class='attribute-grid']/span[@class='attribute-text']")

                    # Extracting the attributes (like bedroom, bathroom, garage) from features_element
                    attributes = [float("nan")] * 3

                    for idx, attr_elem in enumerate(features_element[:3]):
                        text_content = attr_elem.text
                        if text_content.isdigit():
                            attributes[idx] = int(text_content)

                    bedroom, bathroom, garage = attributes

                    # Land Area
                    try:
                        land_area_text = element.find_element(By.XPATH, ".//div[contains(text(), 'LT : ')]/span").text.strip()
                        land_area = int(re.search(r"\d+", land_area_text).group()) if re.search(r"\d+", land_area_text) else float("nan")
                    except NoSuchElementException:
                        land_area = float("nan")

                    # Building Area
                    try:
                        building_area_text = element.find_element(By.XPATH, ".//div[contains(text(), 'LB : ')]/span").text.strip()
                        building_area = int(re.search(r"\d+", building_area_text).group()) if re.search(r"\d+", building_area_text) else float("nan")
                    except NoSuchElementException:
                        building_area = float("nan")

                    # Agent & Date
                    try:
                        agent_date_element = element.find_element(By.CLASS_NAME, "ui-organisms-card-r123-basic__bottom-section__agent")
                        
                        time_info = agent_date_element.find_element(By.XPATH, ".//p[1]").text
                        time_pattern = re.compile(r'(\d+\s\w+)')
                        time_match = time_pattern.search(time_info)

                        if time_match:
                            agent = time_match.group(1)
                        else:
                            agent = float("nan")

                        date = agent_date_element.find_element(By.XPATH, ".//p[2]").text.strip()
                    except NoSuchElementException:
                        agent = float("nan")
                        date = float("nan")

                    print(f"House {index + 1} (Page {page}):")

                    titles.append(title)
                    print(f"Title: {title}")

                    links.append(link)
                    print(f"Link: {link}")

                    locations.append(location)
                    print(f"Location: {location}")

                    prices.append(price)
                    print(f"Price: {price}")

                    bedrooms.append(bedroom)
                    print(f"Bedroom: {bedroom}")

                    bathrooms.append(bathroom)
                    print(f"Bathroom: {bathroom}")

                    garages.append(garage)
                    print(f"Garage: {garage}")

                    land_areas.append(land_area)
                    print(f"Land Area: {land_area}")

                    building_areas.append(building_area)
                    print(f"Building Area: {building_area}")

                    agents.append(date)
                    print(f"Agent: {date}")

                    def subtract_time_from_now(time_string):
                        time_parts = time_string.split()

                        number = int(time_parts[0])
                        unit = time_parts[-1]

                        now = datetime.now() + timedelta(hours=7)
                        # now = datetime.now()

                        if unit.lower() == "detik":
                            return now - timedelta(seconds=number)
                        elif unit.lower() == "menit":
                            return now - timedelta(minutes=number)
                        elif unit.lower() == "jam":
                            return now - timedelta(hours=number)
                        elif unit.lower() == "hari":
                            return now - timedelta(days=number)
                        else:
                            raise ValueError("Unknown time unit!")
                        
                    agent = subtract_time_from_now(agent)
                    dates.append(agent)
                    print(f"Date: {agent}")

                    print("--------------------")

                    # Check If Conditions Are Met
                    if title == query_most_recent["title"][0] and link == query_most_recent["link"][0] and \
                            location == query_most_recent["address"][0] and date == query_most_recent["agent"][0]:
                        print("CONDITIONS ARE MET")
                        conditions_met = True
                        break

                    index += 1

                except NoSuchElementException:
                    continue

            if page == 1:
                sb.save_screenshot("page_screenshot_after.png")

            if conditions_met:
                break

        except Exception as e:
            print(f"Error on page {page}: {str(e)}")
            continue

df = pd.DataFrame({
    "Title": titles,
    "Link": links,
    "Address": locations,
    "Bedroom": bedrooms,
    "Bathroom": bathrooms,
    "Garage": garages,
    "Land m2": land_areas,
    "Building m2": building_areas,
    "Price": prices,
    "Agent": agents,
    "Date": dates
})

df.to_csv("scraped_data.csv", index=False)