import os
import sys
import unittest
import requests
from dotenv import load_dotenv

# Selenium imports, set up
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException

driver_options = Options()
driver_options.headless = True
driver_options.add_argument("--headless")
driver_options.add_argument("--disable-gpu")
driver_options.add_argument("--enable-javascript")
driver_options.add_argument("--disable-blink-features=AutomationControlled")

# Load environment variables
load_dotenv()
GECKODRIVER_PATH = os.getenv("GECKODRIVER_PATH")
PAGE_LOAD_DELAY = os.getenv("PAGE_LOAD_DELAY") # seconds

from selenium_helper import is_text_present, click_on, find_element,  find_clickable_element, wait_for_redirect

class ServicesAvailabityTest (unittest.TestCase):
    def test_vt_frontend_available (self):
        try:
            response = requests.get("http://localhost:81/")
            self.passing = self.assertEqual(200, response.status_code)
        except requests.exceptions.HTTPError as e:
            raise SystemExit("VT frontend not available!")

    def test_vt_backend_available (self):
        try:
            response = requests.get("http://localhost:81/backend/")
            self.passing = self.assertEqual(200, response.status_code)
        except requests.exceptions.HTTPError as e:
            raise SystemExit("VT backend not available!")

    def test_gateway_voting_service_available (self):
        try:
            response = requests.get("http://localhost:8080//voting-service-api/")
            self.passing = self.assertEqual(200, response.status_code)
        except requests.exceptions.HTTPError as e:
            raise SystemExit("GATEWAY voting service not available!")

    def test_gateway_statevector_available (self):
        try:
            response = requests.get("http://localhost:8080/statevector/config/config.json")
            self.passing = self.assertEqual(200, response.status_code)
        except requests.exceptions.HTTPError as e:
            raise SystemExit("GATEWAY statevector not available!")

    def test_gateway_voting_process_manager_available (self):
        try:
            response = requests.get("http://localhost:8080/voting-process-manager-api/")
            self.passing = self.assertEqual(200, response.status_code)
        except requests.exceptions.HTTPError as e:
            raise SystemExit("GATEWAY voting process manager not available!")

class VotingTest (unittest.TestCase):
    def setUp(self):
        self.driver = webdriver.Firefox(options = driver_options, executable_path = GECKODRIVER_PATH)


    def test_select_none (self):
        driver = self.driver

        # Redirect to token scan
        driver.get("http://localhost:81/parliament/party")

        wait_for_redirect(driver, "http://localhost:81/parliament/scan")
        find_element(driver, "//img[@src='/img/insert-token.png']", by = By.XPATH)
        self.assertTrue(is_text_present(driver, "Vložte prosím autorizačný token do čítačky"))

        # Send validated token
        response = requests.get("http://localhost:81/backend/test_token_valid")
        self.passing = self.assertEqual(200, response.status_code)

        # Get candidating parties
        driver.get("http://localhost:81/parliament/party")

        find_element(driver, "content")
        self.assertTrue(is_text_present(driver, "Kandidujúce strany:"))

        # Decide for no party
        element = find_clickable_element(driver, "//button[text()='Potvrdiť']", by = By.XPATH)
        click_on(driver, element)

        # Confirm sending vote with no selection
        self.assertTrue(is_text_present(driver, "Odoslať prázdny hlas"))
        element = find_clickable_element(driver, "//button[text()='Odoslať prázdny hlas']", by = By.XPATH)
        click_on(driver, element)

        # Warning of no selection
        self.assertTrue(is_text_present(driver, "Nezvolili ste žiadnu politickú stranu"))
        self.assertTrue(is_text_present(driver, "Nezvolili ste žiadneho kandidáta"))

        # Send vote
        element = find_clickable_element(driver, "//button[text()='Odoslať hlas']", by = By.XPATH)
        click_on(driver, element)

        self.assertTrue(is_text_present(driver, "VÁŠ HLAS BOL ZAPOČÍTANÝ"))


    def test_selecting_party_only (self):
        driver = self.driver

        # Redirect to token scan
        driver.get("http://localhost:81/parliament/party")

        wait_for_redirect(driver, "http://localhost:81/parliament/scan")
        find_element(driver, "//img[@src='/img/insert-token.png']", by = By.XPATH)
        self.assertTrue(is_text_present(driver, "Vložte prosím autorizačný token do čítačky"))

        # Send validated token
        response = requests.get("http://localhost:81/backend/test_token_valid")
        self.passing = self.assertEqual(200, response.status_code)

        # Get candidating parties
        driver.get("http://localhost:81/parliament/party")

        find_element(driver, "content")
        self.assertTrue(is_text_present(driver, "Kandidujúce strany:"))

        # Decide for Sme Rodina party
        element = find_clickable_element(driver, "(//input[@type='checkbox'])[4]", by = By.XPATH)
        click_on(driver, element)

        element = find_clickable_element(driver, "//button[text()='Potvrdiť']", by = By.XPATH)
        click_on(driver, element)

        find_element(driver, "modal-content")
        self.assertTrue(is_text_present(driver, "Zvolili ste"))
        self.assertTrue(is_text_present(driver, "SME RODINA"))
        element = find_clickable_element(driver, "(//button[text()='Potvrdiť'])[2]", by = By.XPATH)
        click_on(driver, element)

        # List of candidates present
        self.assertTrue(is_text_present(driver, "1. Boris Kollár"))

        # Decide for no candidate
        element = find_clickable_element(driver, "//button[text()='Potvrdiť ']", by = By.XPATH)
        click_on(driver, element)

        # Confirm sending vote with no selection
        self.assertTrue(is_text_present(driver, "potvrdiť odoslanie prázdneho hlasu?"))
        element = find_clickable_element(driver, "//button[text()='Pokračovať']", by = By.XPATH)
        click_on(driver, element)

        # Warning of no selection
        self.assertTrue(is_text_present(driver, "Zvolená strana"))
        self.assertTrue(is_text_present(driver, "SME RODINA"))
        self.assertTrue(is_text_present(driver, "Nezvolili ste žiadneho kandidáta"))

        # Send vote
        element = find_clickable_element(driver, "//button[text()='Odoslať hlas']", by = By.XPATH)
        click_on(driver, element)

        self.assertTrue(is_text_present(driver, "VÁŠ HLAS BOL ZAPOČÍTANÝ"))


    def test_selecting_party_and_candidates (self):
        driver = self.driver

        # Redirect to token scan
        driver.get("http://localhost:81/parliament/party")

        wait_for_redirect(driver, "http://localhost:81/parliament/scan")
        find_element(driver, "//img[@src='/img/insert-token.png']", by = By.XPATH)
        self.assertTrue(is_text_present(driver, "Vložte prosím autorizačný token do čítačky"))

        # Send validated token
        response = requests.get("http://localhost:81/backend/test_token_valid")
        self.passing = self.assertEqual(200, response.status_code)

        # Get candidating parties
        driver.get("http://localhost:81/parliament/party")

        find_element(driver, "content")
        self.assertTrue(is_text_present(driver, "Kandidujúce strany:"))

        # Decide for Sme Rodina party
        element = find_clickable_element(driver, "(//input[@type='checkbox'])[4]", by = By.XPATH)
        click_on(driver, element)

        element = find_clickable_element(driver, "//button[text()='Potvrdiť']", by = By.XPATH)
        click_on(driver, element)

        find_element(driver, "modal-content")
        self.assertTrue(is_text_present(driver, "Zvolili ste"))
        self.assertTrue(is_text_present(driver, "SME RODINA"))
        element = find_clickable_element(driver, "(//button[text()='Potvrdiť'])[2]", by = By.XPATH)
        click_on(driver, element)

        # Select candidates
        self.assertTrue(is_text_present(driver, "1. Boris Kollár"))
        element = find_clickable_element(driver, "(//input[@type='checkbox'])[1]", by = By.XPATH)
        click_on(driver, element)

        self.assertTrue(is_text_present(driver, "Ešte môžete zvoliť 4 kandidátov"))

        element = find_clickable_element(driver, "next")
        click_on(driver, element)

        self.assertTrue(is_text_present(driver, "11. Ľuboš Krajčír"))

        element = find_clickable_element(driver, "next")
        click_on(driver, element)

        self.assertTrue(is_text_present(driver, "21. Jozef Mozol"))
        element = find_clickable_element(driver, "(//input[@type='checkbox'])[1]", by = By.XPATH)
        click_on(driver, element)

        self.assertTrue(is_text_present(driver, "Ešte môžete zvoliť 3 kandidátov"))

        element = find_clickable_element(driver, "//button[text()='Potvrdiť ']", by = By.XPATH)
        click_on(driver, element)

        # Confirm selected candidates
        self.assertTrue(is_text_present(driver, "Zvolili ste"))
        self.assertTrue(is_text_present(driver, "1. Boris Kollár"))
        self.assertTrue(is_text_present(driver, "21. Jozef Mozol"))
        self.assertTrue(is_text_present(driver, "Ešte môžete zvoliť ďalších 3 kandidátov"))
        element = find_clickable_element(driver, "//button[text()='Pokračovať']", by = By.XPATH)
        click_on(driver, element)

        # Warning of no selection
        self.assertTrue(is_text_present(driver, "Zvolená strana"))
        self.assertTrue(is_text_present(driver, "SME RODINA"))
        self.assertTrue(is_text_present(driver, "Zvolení kandidáti na poslancov"))
        self.assertTrue(is_text_present(driver, "1. Boris Kollár"))
        self.assertTrue(is_text_present(driver, "21. Jozef Mozol"))

        # Send vote
        element = find_clickable_element(driver, "//button[text()='Odoslať hlas']", by = By.XPATH)
        click_on(driver, element)

        self.assertTrue(is_text_present(driver, "VÁŠ HLAS BOL ZAPOČÍTANÝ"))


    def tearDown (self):
        self.driver.close()

if __name__ == "__main__":
    # Exit if any fail
    unittest.main(failfast = True)

    # Do not sort tests to check services availability first
    unittest.TestLoader.sortTestMethodsUsing = None
