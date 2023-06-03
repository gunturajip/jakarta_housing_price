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
credential_file = "jakarta-housing-price-595a9cff2797.json"
credential = Credentials.from_service_account_file(credential_file)
job_location = "asia-southeast2"

query_most_recent = pd.read_gbq(f"SELECT * FROM `{project_id}.{target_table_2}`", project_id=project_id, credentials=credential)
query_most_recent["date"] = query_most_recent["date"].dt.tz_localize(None)

# Browser Settings
website = "https://www.rumah123.com/jual/dki-jakarta/rumah/?sort=posted-desc&page=1#qid~a46c0629-67e4-410c-9c35-0c80e98987d9"
path = "chromedriver.exe"

service = Service(path)

options = Options()
options.add_argument("--headless")
options.add_argument("window-size=1920x1080")

driver = webdriver.Chrome(service=service, options=options)

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
scraped_timestamps = []

# Iterate through Each Page
conditions_met = False

for page in range(1, 101):
    print(f"Scraping page {page}")

    url = f"https://www.rumah123.com/jual/dki-jakarta/rumah/?sort=posted-desc&page={page}#qid~a46c0629-67e4-410c-9c35-0c80e98987d9"
    driver.get(url)

    # Property Elements
    property_elements = driver.find_elements("xpath", "//div[contains(@class, 'card-container')]")
    
    # Iterate through Each Property Element
    index = 0
    for element in property_elements:
        try:
            # Scraped Timestamp
            current_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Title
            try:
                title_element = element.find_element("xpath", ".//a[@title and h2]")
                title = title_element.text
            except NoSuchElementException:
                title = float("nan")

            # Link
            try:
                link_element = element.find_element("xpath", ".//a[@title and h2]")
                link = link_element.get_attribute("href")
            except NoSuchElementException:
                link = float("nan")

            # Location
            try:
                location_element = element.find_element("xpath", ".//a[@title and h2]/following-sibling::span")
                location = location_element.text
            except NoSuchElementException:
                location = float("nan")

            # Price
            try:
                price_element = element.find_element("class name", "card-featured__middle-section__price")
                price = price_element.text
            except NoSuchElementException:
                price = float("nan")

            # Features
            features_element = element.find_element("class name", "card-featured__middle-section__attribute")

            # Bedroom
            try:
                bedroom_element = features_element.find_element("css selector", "div.ui-molecules-list__item:nth-child(1) span.attribute-text")
                bedroom = int(bedroom_element.text) if bedroom_element.text.isdigit() else float("nan")
            except NoSuchElementException:
                bedroom = float("nan")

            # Bathroom
            try:
                bathroom_element = features_element.find_element("css selector", "div.ui-molecules-list__item:nth-child(2) span.attribute-text")
                bathroom = int(bathroom_element.text) if bathroom_element.text.isdigit() else float("nan")
            except NoSuchElementException:
                bathroom = float("nan")

            # Garage
            try:
                garage_element = features_element.find_element("css selector", "div.ui-molecules-list__item:nth-child(3) span.attribute-text")
                garage = int(garage_element.text) if garage_element.text.isdigit() else float("nan")
            except NoSuchElementException:
                garage = float("nan")

            # Land Area
            try:
                land_area_element = element.find_element("xpath", ".//div[contains(text(), 'LT : ')]/span")
                land_area_text = land_area_element.text.strip()
                land_area = int(land_area_text.split()[0]) if land_area_text.split()[0].isdigit() else float("nan")
            except NoSuchElementException:
                land_area = float("nan")

            # Building Area
            try:
                building_area_element = element.find_element("xpath", ".//div[contains(text(), 'LB : ')]/span")
                building_area_text = building_area_element.text.strip()
                building_area = int(building_area_text.split()[0]) if building_area_text.split()[0].isdigit() else float("nan")
            except NoSuchElementException:
                building_area = float("nan")

            # Agent & Date
            try:
                agent_date_element = element.find_element("class name", "ui-organisms-card-r123-basic__bottom-section__agent")
                agent = agent_date_element.find_element("tag name", "p").text.strip()
                date = agent_date_element.find_elements("tag name", "p")[1].text.strip() if len(agent_date_element.find_elements("tag name", "p")) > 1 else float("nan")
            except NoSuchElementException:
                agent = float("nan")
                date = float("nan")

            # Store the Scraped Data in the Lists
            print(f"House {index + 1} (Page {page}):")

            scraped_timestamps.append(current_timestamp)
            print(f"Scraped Timestamp: {current_timestamp}")

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

            agents.append(agent)
            print(f"Agent: {agent}")

            dates.append(date)
            print(f"Date: {date}")

            print("--------------------")

            # Check If Conditions Are Met
            if title == query_most_recent["title"][0] and link == query_most_recent["link"][0] and \
                    location == query_most_recent["location"][0] and agent == query_most_recent["agent"][0]:
                print("CONDITIONS ARE MET")
                conditions_met = True
                break

            index += 1

        except NoSuchElementException:
            continue

    if conditions_met:
        break

driver.quit()

df = pd.DataFrame({
    "Title": titles,
    "Link": links,
    "Location": locations,
    "Bedroom": bedrooms,
    "Bathroom": bathrooms,
    "Garage": garages,
    "Land m2": land_areas,
    "Building m2": building_areas,
    "Price": prices,
    "Agent": agents,
    "Date": dates,
    "Scraped Timestamp": scraped_timestamps
})

df.to_csv("scraped_data.csv", index=False)