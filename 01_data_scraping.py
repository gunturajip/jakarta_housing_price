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

query_most_recent = pd.read_gbq(f"SELECT * FROM `{project_id}.{target_table_2}`", project_id=project_id, credentials=credential)
query_most_recent["date"] = query_most_recent["date"].dt.tz_localize(None)

website = "https://www.rumah123.com/jual/dki-jakarta/rumah/?sort=posted-desc&page=1#qid~a46c0629-67e4-410c-9c35-0c80e98987d9"
path = "chromedriver.exe"

service = Service(path)

options = Options()
options.add_argument("--headless")
options.add_argument("window-size=1920x1080")

driver = webdriver.Chrome(service=service, options=options)

title = []
link = []
location = []
price = []
bedrooms = []
bathrooms = []
garages = []
land_areas = []
building_areas = []
agent = []
date = []
scraped_timestamp = []

for page in range(1, 101):
    print(f"Scraping page {page}")

    url = f"https://www.rumah123.com/jual/dki-jakarta/rumah/?sort=posted-desc&page={page}#qid~a46c0629-67e4-410c-9c35-0c80e98987d9"
    driver.get(url)

    pagination = driver.find_element("class name", "ui-molecule-paginate")

    title_elements = driver.find_elements("xpath", "//a[@title and h2]")
    titles = [element.text if element.text else float("nan") for element in title_elements]

    link_elements = driver.find_elements("xpath", "//a[@title and h2]")
    links = [element.get_attribute("href") if element.get_attribute("href") else float("nan") for element in link_elements]

    location_elements = driver.find_elements("xpath", "//a[@title and h2]/following-sibling::span")
    locations = [element.text if element.text else float("nan") for element in location_elements]

    price_elements = driver.find_elements("class name", "card-featured__middle-section__price")
    prices = [element.text if element.text else float("nan") for element in price_elements]

    features_elements = driver.find_elements("class name", "card-featured__middle-section__attribute")

    for index, element in enumerate(features_elements):
        current_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        scraped_timestamp.append(current_timestamp)
        title.append(titles[index] if index < len(titles) else 'N/A')
        link.append(links[index] if index < len(links) else 'N/A')
        location.append(locations[index] if index < len(locations) else 'N/A')
        price.append(prices[index] if index < len(prices) else 'N/A')
        
        try:
            bedroom_element = element.find_element("css selector", "div.ui-molecules-list__item:nth-child(1) span.attribute-text")
            bedroom = int(bedroom_element.text) if bedroom_element.text.isdigit() else 'N/A'
        except NoSuchElementException:
            bedroom = 'N/A'
        bedrooms.append(bedroom)

        try:
            bathroom_element = element.find_element("css selector", "div.ui-molecules-list__item:nth-child(2) span.attribute-text")
            bathroom = int(bathroom_element.text) if bathroom_element.text.isdigit() else 'N/A'
        except NoSuchElementException:
            bathroom = 'N/A'
        bathrooms.append(bathroom)

        try:
            garage_element = element.find_element("css selector", "div.ui-molecules-list__item:nth-child(3) span.attribute-text")
            garage = int(garage_element.text) if garage_element.text.isdigit() else 'N/A'
        except NoSuchElementException:
            garage = 'N/A'
        garages.append(garage)

        try:
            land_area_element = element.find_element("xpath", ".//div[contains(text(), 'LT : ')]/span")
            land_area_text = land_area_element.text.strip()
            land_area = int(land_area_text.split()[0]) if land_area_text.split()[0].isdigit() else 'N/A'
        except NoSuchElementException:
            land_area = 'N/A'
        land_areas.append(land_area)

        try:
            building_area_element = element.find_element("xpath", ".//div[contains(text(), 'LB : ')]/span")
            building_area_text = building_area_element.text.strip()
            building_area = int(building_area_text.split()[0]) if building_area_text.split()[0].isdigit() else 'N/A'
        except NoSuchElementException:
            building_area = 'N/A'
        building_areas.append(building_area)

        agent_date_elements = driver.find_elements("class name", "ui-organisms-card-r123-basic__bottom-section__agent")
        agents = [element.find_element("tag name", "p").text.strip() if element.find_element("tag name", "p").text.strip() else 'N/A' for element in agent_date_elements]
        dates = [element.find_elements("tag name", "p")[1].text.strip() if len(element.find_elements("tag name", "p")) > 1 and element.find_elements("tag name", "p")[1].text.strip() else 'N/A' for element in agent_date_elements]

        agent.append(agents[index] if index < len(agents) else 'N/A')
        date.append(dates[index] if index < len(dates) else 'N/A')

        print("--------------------")

        if titles[index] == query_most_recent["title"][0] and links[index] == query_most_recent["link"][0] and \
                locations[index] == query_most_recent["location"][0] and agents[index] == query_most_recent["agent"][0]:
            break

    else:
        continue
    break

driver.quit()

df = pd.DataFrame({
    "Title": title,
    "Link": link,
    "Location": location,
    "Bedroom": bedrooms,
    "Bathroom": bathrooms,
    "Garage": garages,
    "Land m2": land_areas,
    "Building m2": building_areas,
    "Price": price,
    "Agent": agent,
    "Date": date,
    "Scraped Timestamp": scraped_timestamp
})

df.to_csv("scraped_data.csv", index=False)