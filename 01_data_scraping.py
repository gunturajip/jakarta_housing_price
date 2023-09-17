import numpy as np
import pandas as pd
import requests
import urllib.parse
import json
import os
import re
import time
import random
# import undetected_chromedriver as uc

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
# from selenium_stealth import stealth
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
# fernet_key = os.environ.get("FERNET_KEY")
fernet_key = "h-INEUme8iXdiFhEK2R6LaZ6ryBwVrkQ0JHbYwKOEsg="
decrypted_credentials = decrypt_file("encryption/encrypted_data.bin", fernet_key)

credential = Credentials.from_service_account_info(decrypted_credentials)

query_most_recent = pd.read_gbq(f"SELECT * FROM `{project_id}.{target_table_2}`", project_id=project_id, credentials=credential)
query_most_recent["date"] = pd.to_datetime(query_most_recent["date"])

options = Options()
options.add_argument("--headless")
options.add_argument("window-size=1920x1080")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
# options.add_experimental_option("excludeSwitches", ["enable-automation"])
# options.add_experimental_option("useAutomationExtension", False)

driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)

# stealth(
#     driver,
#     languages=["en-US", "en"],
#     vendor="Google Inc.",
#     platform="Win32",
#     webgl_vendor="Intel Inc.",
#     renderer="Intel Iris OpenGL Engine",
#     fix_hairline=True,
# )

# driver = uc.Chrome(headless=True, use_subprocess=False)

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

def verify_success(sb):
    sb.assert_element('img[alt="logo rumah123"]', timeout=45)
    sb.sleep(45)

for page in range(1, 101):
    print(f"Scraping page {page}")

    url = f"https://www.rumah123.com/jual/dki-jakarta/rumah/?sort=posted-desc&page={page}#qid~a46c0629-67e4-410c-9c35-0c80e98987d9"

    with SB(uc_cdp=True, guest_mode=True) as sb:
        sb.open(url)
        try:
            verify_success(sb)
        except Exception:
            if sb.is_element_visible('input[value*="Verify"]'):
                sb.click('input[value*="Verify"]')
            elif sb.is_element_visible('iframe[title*="challenge"]'):
                sb.switch_to_frame('iframe[title*="challenge"]')
                sb.click("span.mark")
            else:
                raise Exception("Verification Detected!")
            try:
                verify_success(sb)
            except Exception:
                raise Exception("Verification Detected after attempting!")

    driver.get(url)

    # Using WebDriverWait to wait for the page to load completely
    wait = WebDriverWait(driver, 30)
    wait.until(lambda d: d.execute_script("return document.readyState") == "complete")

    # Assuming you're on the page where the iframe might appear
    try:
        # Wait for the iframe and switch to it
        iframe = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'iframe#cf-chl-widget-ii8u9')))
        driver.switch_to.frame(iframe)
        
        # Interact with the checkbox inside the iframe
        checkbox = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'input[type="checkbox"]')))
        checkbox.click()
        
        # Switch back to the default content
        driver.switch_to.default_content()
        print("Security check handled!")
        
    except TimeoutException:
        # Switch back to the default content in case of any error while interacting with iframe
        driver.switch_to.default_content()
        print("No security check found on this page. Continuing with scraping.")

    # Search for the property elements
    property_elements = driver.find_elements(By.XPATH, "//div[contains(@class, 'card-featured__content-wrapper')]")
    print(property_elements)
    driver.get_screenshot_as_file("page_screenshot.png")
    
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
                price = element.find_element(By.CLASS_NAME, "card-featured__middle-section__price").text.split("\n")[0]
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

            # Store the Scraped Data in the Lists
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

    if conditions_met:
        break

driver.quit()

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