import os
from dotenv import load_dotenv

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

load_dotenv()
PAGE_LOAD_DELAY = os.getenv("PAGE_LOAD_DELAY") # seconds

def is_text_present (driver, text):
    return str(text) in driver.page_source

def click_on (driver, element):
    driver.execute_script("arguments[0].click();", element)

def find_element (driver, identifier, by = By.CLASS_NAME):
    WebDriverWait(driver, PAGE_LOAD_DELAY).until(EC.presence_of_element_located((by, identifier)))

def find_clickable_element (driver, identifier, by = By.CLASS_NAME):
    return WebDriverWait(driver, PAGE_LOAD_DELAY).until(EC.element_to_be_clickable((by, identifier)))

def wait_for_redirect (driver, target_url):
    WebDriverWait(driver, PAGE_LOAD_DELAY).until(lambda driver: driver.current_url != target_url)
