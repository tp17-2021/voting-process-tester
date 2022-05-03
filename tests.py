import os
import sys
import time
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

from webdriver_manager.firefox import GeckoDriverManager

from selenium_helper import is_text_present, click_on, find_element,  find_clickable_element, wait_for_redirect

driver_options = Options()
driver_options.headless = True
driver_options.add_argument("--headless")
driver_options.add_argument("--disable-gpu")
driver_options.add_argument("--enable-javascript")
driver_options.add_argument("--disable-blink-features=AutomationControlled")

# Load environment variables
load_dotenv()
PAGE_LOAD_DELAY = os.getenv("PAGE_LOAD_DELAY") # seconds
VT_FRONTEND_URL = os.getenv("VT_URL") + "frontend/"
VT_BACKEND_URL = os.getenv("VT_URL") + "backend/"
GATEWAY_URL = os.getenv("GATEWAY_URL")
GATEWAY_ADMIN_URL = os.getenv("GATEWAY_URL") + "admin-frontend/"
SERVER_URL = os.getenv("SERVER_URL")

SYNCHRONIZATION_MESSAGE = "votes were successfully synchronized"

elections_on = False
vt_registration_on = False

all_votes_count = 0
synchronized_votes_count = 0
unsynchronized_votes_count = 0



def set_up_server ():
    # Do import
    response = requests.post(SERVER_URL + "database/import-data")

    # Seed data
    response = requests.post(SERVER_URL + "database/seed-data?number_of_votes=1")

    # Set up elastic
    response = requests.post(SERVER_URL + "elastic/setup-elastic-vote-index")



class ServicesAvailabityTest (unittest.TestCase):
    def test_vt_frontend_available (self):
        try:
            response = requests.get(VT_FRONTEND_URL)
            self.passing = self.assertEqual(200, response.status_code)
        except requests.exceptions.HTTPError as e:
            raise SystemExit("VT frontend not available!")

    def test_gateway_voting_service_available (self):
        try:
            response = requests.get(GATEWAY_URL + "voting-service-api/")
            self.passing = self.assertEqual(200, response.status_code)
        except requests.exceptions.HTTPError as e:
            raise SystemExit("GATEWAY voting service not available!")

    def test_gateway_statevector_available (self):
        try:
            response = requests.get(GATEWAY_URL + "statevector/config/config.json")
            self.passing = self.assertEqual(200, response.status_code)
        except requests.exceptions.HTTPError as e:
            raise SystemExit("GATEWAY statevector not available!")

    def test_gateway_voting_process_manager_available (self):
        try:
            response = requests.get(GATEWAY_URL + "voting-process-manager-api/")
            self.passing = self.assertEqual(200, response.status_code)
        except requests.exceptions.HTTPError as e:
            raise SystemExit("GATEWAY voting process manager not available!")

    def test_server_available (self):
        try:
            response = requests.get(SERVER_URL)
            self.passing = self.assertEqual(200, response.status_code)
        except requests.exceptions.HTTPError as e:
            raise SystemExit("SERVER not available!")

        # Set up server if everything OK
        set_up_server()



class VotingTest (unittest.TestCase):
    INSERT_TOKEN_IMAGE_PATH= "/frontend/img/icons/insert.png"

    def setUp (self):
        global vt_registration_on
        global elections_on

        self.driver = webdriver.Firefox(executable_path = GeckoDriverManager().install(), options = driver_options)

        if not vt_registration_on:
            self.turn_on_vt_registration()
            vt_registration_on = True

        if not elections_on:
            self.turn_on_elections_if_not_on()
            elections_on = True


    def enter_gateway_pin (self):
        driver = self.driver

        # Enter 0000
        element = find_clickable_element(driver, "//button[text()='0']", by = By.XPATH)
        for i in range(4):
            click_on(driver, element)

    def turn_on_vt_registration (self):
        driver = self.driver

        driver.get(GATEWAY_ADMIN_URL + "home/terminals")
        find_element(driver, "//main", by = By.XPATH)

        # Enter PIN
        self.enter_gateway_pin()

        wait_for_redirect(driver, GATEWAY_ADMIN_URL + "home")

        # Click on VT menu
        element = find_clickable_element(driver, "//button[text()='Volebné terminaly']", by = By.XPATH)
        click_on(driver, element)

        find_element(driver, "//main", by = By.XPATH)

        # Turn registration on
        find_element(driver, "registration-state", by = By.ID)

        # Wait for status update
        time.sleep(2)

        if not is_text_present(driver, "Registrácia spustená."):
            element = find_clickable_element(driver, "//button[text()='Spustiť registráciu']", by = By.XPATH)
            click_on(driver, element)

        find_element(driver, "//div[text()='Registrácia spustená.']", by = By.XPATH)

    def turn_on_elections_if_not_on (self):
        driver = self.driver

        driver.get(GATEWAY_ADMIN_URL + "home/elections")
        find_element(driver, "//main", by = By.XPATH)

        # Enter PIN
        self.enter_gateway_pin()

        wait_for_redirect(driver, GATEWAY_ADMIN_URL + "home")

        # Click on Elections menu
        element = find_clickable_element(driver, "//button[text()='Voľby']", by = By.XPATH)
        click_on(driver, element)

        find_element(driver, "//main", by = By.XPATH)

        # Turn elections on
        find_element(driver, "election-state", by = By.ID)

        # Wait for status update
        time.sleep(2)

        if not is_text_present(driver, "Voľby spustené."):
            element = find_clickable_element(driver, "//button[text()='Spustiť voľby']", by = By.XPATH)
            click_on(driver, element)

        find_element(driver, "//div[text()='Voľby spustené.']", by = By.XPATH)


    def test_select_none (self):
        global all_votes_count
        global synchronized_votes_count
        global unsynchronized_votes_count

        driver = self.driver

        # Get token
        response = requests.post(GATEWAY_URL + "token-manager-api/tokens/create")
        self.passing = self.assertEqual(200, response.status_code)
        token = response.json()["token"]

        # Activate token
        response = requests.post(GATEWAY_URL + 'token-manager-api/tokens/writer/update', json = {"token": token})
        self.passing = self.assertEqual(200, response.status_code)

        # Wait for FE to be ready
        time.sleep(20)
        driver.get(VT_FRONTEND_URL)
        find_element(driver, "//div[text()='Načítajte NFC tag']", by = By.XPATH)

        # Use token
        response = requests.post(VT_BACKEND_URL + "token", json = token)
        self.passing = self.assertEqual(200, response.status_code)

        # Get candidating parties
        driver.get(VT_FRONTEND_URL + "parliament/party")

        find_element(driver, "//h2[text()='Kandidujúce strany:']", by = By.XPATH)

        # Decide for no party
        element = find_clickable_element(driver, "//button[text()='Potvrdiť']", by = By.XPATH)
        click_on(driver, element)

        # Confirm sending vote with no selection
        self.assertTrue(is_text_present(driver, "Naozaj chcete odoslať prázdny hlas?"))
        element = find_clickable_element(driver, "//button[text()='Odoslať prázdny hlas']", by = By.XPATH)
        click_on(driver, element)

        # Warning of no selection
        find_element(driver, "//div[text()='Nezvolili ste žiadnu politickú stranu']", by = By.XPATH)
        find_element(driver, "//div[text()='Nezvolili ste žiadneho kandidáta']", by = By.XPATH)

        # Send vote
        element = find_clickable_element(driver, "//button[text()='Odoslať hlas']", by = By.XPATH)
        click_on(driver, element)

        find_element(driver, "//div[text()='Váš hlas bol započítaný']", by = By.XPATH, delay = 6)

        all_votes_count += 1
        unsynchronized_votes_count += 1

        # Check if vote is saved in gateway
        response = requests.post(GATEWAY_URL + "synchronization-service-api/statistics")
        self.assertEqual(200, response.status_code)
        statistics_result = response.json()

        self.assertTrue(statistics_result["statistics"]["all_count"] == all_votes_count)
        self.assertTrue(statistics_result["statistics"]["syncronized_count"] == synchronized_votes_count)
        self.assertTrue(statistics_result["statistics"]["unsyncronized_count"] == unsynchronized_votes_count)

        # Synchronize votes in gateway with server
        response = requests.post(GATEWAY_URL + "synchronization-service-api/synchronize")
        self.assertEqual(200, response.status_code)

        unsynchronized_votes_count -= 1
        synchronized_votes_count += 1

        # Check if vote is marked as synchronized
        response = requests.post(GATEWAY_URL + "synchronization-service-api/statistics")
        self.assertEqual(200, response.status_code)
        statistics_result = response.json()

        self.assertTrue(statistics_result["statistics"]["all_count"] == all_votes_count)
        self.assertTrue(statistics_result["statistics"]["syncronized_count"] == synchronized_votes_count)
        self.assertTrue(statistics_result["statistics"]["unsyncronized_count"] == unsynchronized_votes_count)

        # Check server statistics
        response = requests.get(SERVER_URL + "elastic/synchronization-status")
        election_status = response.json()

        # There is +1 vote in server because of initial seed
        self.assertTrue(election_status["data"]["total_votes"] == all_votes_count + 1)

        # Do elastic search synchronize
        response = requests.post(SERVER_URL + "elastic/synchronize-votes-es", json = {"number": 100})
        synchronize_response = response.json()

        self.assertTrue(SYNCHRONIZATION_MESSAGE in synchronize_response["message"])


    def test_select_party_only (self):
        global all_votes_count
        global synchronized_votes_count
        global unsynchronized_votes_count

        driver = self.driver

        # Get token
        response = requests.post(GATEWAY_URL + "token-manager-api/tokens/create")
        self.passing = self.assertEqual(200, response.status_code)
        token = response.json()["token"]

        # Activate token
        response = requests.post(GATEWAY_URL + 'token-manager-api/tokens/writer/update', json = {"token": token})
        self.passing = self.assertEqual(200, response.status_code)

        response = requests.post(VT_BACKEND_URL + "token", json = token)
        self.passing = self.assertEqual(200, response.status_code)

        # Get candidating parties
        driver.get(VT_FRONTEND_URL + "parliament/party")

        find_element(driver, "//h2[text()='Kandidujúce strany:']", by = By.XPATH)

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
        find_element(driver, "//h2[text()='Kandidáti']", by = By.XPATH)
        find_element(driver, "//span[text()='Meno']", by = By.XPATH)
        self.assertTrue(is_text_present(driver, "Boris Kollár"))

        # Decide for no candidate
        element = find_clickable_element(driver, "//button[text()='Potvrdiť']", by = By.XPATH)
        click_on(driver, element)

        # Confirm sending vote with no selection
        self.assertTrue(is_text_present(driver, "potvrdiť odoslanie prázdneho hlasu?"))
        element = find_clickable_element(driver, "//button[text()='Pokračovať']", by = By.XPATH)
        click_on(driver, element)

        # Warning of no candidate selected
        find_element(driver, "//h2[text()='Zvolená strana']", by = By.XPATH)
        self.assertTrue(is_text_present(driver, "SME RODINA"))
        self.assertTrue(is_text_present(driver, "Nezvolili ste žiadneho kandidáta"))

        # Send vote
        element = find_clickable_element(driver, "//button[text()='Odoslať hlas']", by = By.XPATH)
        click_on(driver, element)

        find_element(driver, "//div[text()='Váš hlas bol započítaný']", by = By.XPATH, delay = 6)

        all_votes_count += 1
        unsynchronized_votes_count += 1

        # Check if vote is saved in gateway
        response = requests.post(GATEWAY_URL + "synchronization-service-api/statistics")
        self.assertEqual(200, response.status_code)
        statistics_result = response.json()

        self.assertTrue(statistics_result["statistics"]["all_count"] == all_votes_count)
        self.assertTrue(statistics_result["statistics"]["syncronized_count"] == synchronized_votes_count)
        self.assertTrue(statistics_result["statistics"]["unsyncronized_count"] == unsynchronized_votes_count)

        # Synchronize votes in gateway with server
        response = requests.post(GATEWAY_URL + "synchronization-service-api/synchronize")
        self.assertEqual(200, response.status_code)

        unsynchronized_votes_count -= 1
        synchronized_votes_count += 1

        # Check if vote is marked as synchronized
        response = requests.post(GATEWAY_URL + "synchronization-service-api/statistics")
        self.assertEqual(200, response.status_code)
        statistics_result = response.json()

        self.assertTrue(statistics_result["statistics"]["all_count"] == all_votes_count)
        self.assertTrue(statistics_result["statistics"]["syncronized_count"] == synchronized_votes_count)
        self.assertTrue(statistics_result["statistics"]["unsyncronized_count"] == unsynchronized_votes_count)

        # Check server statistics
        response = requests.get(SERVER_URL + "elastic/synchronization-status")
        election_status = response.json()

        # There is +1 vote in server because of initial seed
        self.assertTrue(election_status["data"]["total_votes"] == all_votes_count + 1)

        # Do elastic search synchronize
        response = requests.post(SERVER_URL + "elastic/synchronize-votes-es", json = {"number": 100})
        synchronize_response = response.json()

        self.assertTrue(SYNCHRONIZATION_MESSAGE in synchronize_response["message"])


    def test_select_party_and_candidates (self):
        global all_votes_count
        global synchronized_votes_count
        global unsynchronized_votes_count

        driver = self.driver

        # Get token
        response = requests.post(GATEWAY_URL + "token-manager-api/tokens/create")
        self.passing = self.assertEqual(200, response.status_code)
        token = response.json()["token"]

        # Activate token
        response = requests.post(GATEWAY_URL + 'token-manager-api/tokens/writer/update', json = {"token": token})
        self.passing = self.assertEqual(200, response.status_code)

        response = requests.post(VT_BACKEND_URL + "token", json = token)
        self.passing = self.assertEqual(200, response.status_code)

        # Get candidating parties
        driver.get(VT_FRONTEND_URL + "parliament/party")

        find_element(driver, "//h2[text()='Kandidujúce strany:']", by = By.XPATH)

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
        find_element(driver, "//h2[text()='Kandidáti']", by = By.XPATH)
        find_element(driver, "//span[text()='Meno']", by = By.XPATH)
        self.assertTrue(is_text_present(driver, "Boris Kollár"))

        # Select candidates
        element = find_clickable_element(driver, "(//input[@type='checkbox'])[1]", by = By.XPATH)
        click_on(driver, element)

        self.assertTrue(is_text_present(driver, "Ešte môžete zvoliť 4 kandidátov"))

        element = find_clickable_element(driver, "next")
        click_on(driver, element)

        self.assertTrue(is_text_present(driver, "Ľuboš Krajčír"))

        element = find_clickable_element(driver, "next")
        click_on(driver, element)

        self.assertTrue(is_text_present(driver, "Jozef Mozol"))
        element = find_clickable_element(driver, "(//input[@type='checkbox'])[1]", by = By.XPATH)
        click_on(driver, element)

        self.assertTrue(is_text_present(driver, "Ešte môžete zvoliť 3 kandidátov"))

        element = find_clickable_element(driver, "//button[text()='Potvrdiť']", by = By.XPATH)
        click_on(driver, element)

        # Confirm selected candidates
        self.assertTrue(is_text_present(driver, "Zvolili ste"))
        self.assertTrue(is_text_present(driver, "Boris Kollár"))
        self.assertTrue(is_text_present(driver, "Jozef Mozol"))
        self.assertTrue(is_text_present(driver, "Ešte môžete zvoliť ďalších 3 kandidátov"))
        element = find_clickable_element(driver, "//button[text()='Pokračovať']", by = By.XPATH)
        click_on(driver, element)

        find_element(driver, "//h2[text()='Zvolená strana']", by = By.XPATH)
        self.assertTrue(is_text_present(driver, "SME RODINA"))
        self.assertTrue(is_text_present(driver, "Zvolení kandidáti na poslancov"))
        self.assertTrue(is_text_present(driver, "Boris Kollár"))
        self.assertTrue(is_text_present(driver, "Jozef Mozol"))

        # Send vote
        element = find_clickable_element(driver, "//button[text()='Odoslať hlas']", by = By.XPATH)
        click_on(driver, element)

        find_element(driver, "//div[text()='Váš hlas bol započítaný']", by = By.XPATH, delay = 6)

        all_votes_count += 1
        unsynchronized_votes_count += 1

        # Check if vote is saved in gateway
        response = requests.post(GATEWAY_URL + "synchronization-service-api/statistics")
        self.assertEqual(200, response.status_code)
        statistics_result = response.json()

        self.assertTrue(statistics_result["statistics"]["all_count"] == all_votes_count)
        self.assertTrue(statistics_result["statistics"]["syncronized_count"] == synchronized_votes_count)
        self.assertTrue(statistics_result["statistics"]["unsyncronized_count"] == unsynchronized_votes_count)

        # Synchronize votes in gateway with server
        response = requests.post(GATEWAY_URL + "synchronization-service-api/synchronize")
        self.assertEqual(200, response.status_code)

        unsynchronized_votes_count -= 1
        synchronized_votes_count += 1

        # Check if vote is marked as synchronized
        response = requests.post(GATEWAY_URL + "synchronization-service-api/statistics")
        self.assertEqual(200, response.status_code)
        statistics_result = response.json()

        self.assertTrue(statistics_result["statistics"]["all_count"] == all_votes_count)
        self.assertTrue(statistics_result["statistics"]["syncronized_count"] == synchronized_votes_count)
        self.assertTrue(statistics_result["statistics"]["unsyncronized_count"] == unsynchronized_votes_count)

        # Check server statistics
        response = requests.get(SERVER_URL + "elastic/synchronization-status")
        self.assertEqual(200, response.status_code)
        election_status = response.json()

        # There is +1 vote in server because of initial seed
        self.assertTrue(election_status["data"]["total_votes"] == all_votes_count + 1)

        # Do elastic search synchronize
        response = requests.post(SERVER_URL + "elastic/synchronize-votes-es", json = {"number": 100})
        self.assertEqual(200, response.status_code)
        synchronize_response = response.json()

        self.assertTrue(SYNCHRONIZATION_MESSAGE in synchronize_response["message"])


    def tearDown (self):
        self.driver.close()



if __name__ == "__main__":
    # Exit if any fail
    unittest.main(failfast = True)

    # Do not sort tests to check services availability first
    unittest.TestLoader.sortTestMethodsUsing = None
