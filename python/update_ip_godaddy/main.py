# A simple script that updates godaddy ip through playwrightr

import urllib.request
import os
import re
import time
import random
import logging
import shutil
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('godaddy_updater.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def get_my_ip():
    try:
        response = urllib.request.urlopen("https://api.ipify.org")
        my_ip = response.read().decode('utf8')
        logger.info(f"Retrieved IP: {my_ip}")
        return my_ip
    except Exception as e:
        logger.error(f"Error getting IP: {e}", exc_info=True)
        raise

# Setup automation profile
def setup_automation_profile():
    try:
        user_data_dir = os.path.expandvars(
            r'C:\Users\%USERNAME%\AppData\Local\BraveSoftware\Brave-Browser\User Data'
        )
        
        source_profile = os.path.join(user_data_dir, 'Default')
        dest_profile = os.path.join(user_data_dir, 'AutomationProfile')  # or your automation profile
        
        print(dest_profile)

        # Files to copy for staying logged in
        files_to_copy = [
            'Cookies',
            'Cookies-journal',
            'Login Data',
            'Login Data-journal',
            'Web Data',
            'Web Data-journal',
            'Network',
            'Preferences'
        ]
        
        logger.info("Copying authentication data to automation profile...")
        
        for file_name in files_to_copy:
            source_file = os.path.join(source_profile, file_name)
            dest_file = os.path.join(dest_profile, file_name)
            
            if os.path.exists(source_file):
                if os.path.isfile(source_file):
                    shutil.copy2(source_file, dest_file)
                    logger.info(f"Copied {file_name}")
                elif os.path.isdir(source_file):
                    if os.path.exists(dest_file):
                        shutil.rmtree(dest_file)
                    shutil.copytree(source_file, dest_file)
                    logger.info(f"Copied {file_name} directory")
        
        logger.info("Profile setup complete")
        
    except Exception as e:
        logger.error(f"Error setting up automation profile: {e}", exc_info=True)


# Init browser using Brave & local cookies
def init_browser():
    try:
        time.sleep(random.uniform(0.3, 0.8))
        user_data_dir = os.path.expandvars(
                r'C:\Users\%USERNAME%\AppData\Local\BraveSoftware\Brave-Browser\User Data'
            )

        browser = p.chromium.launch_persistent_context(
            user_data_dir,
            executable_path=r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
            headless=True,
            args=['--profile-directory=AutomationProfile'] 
        )
        logger.info("Browser initialized successfully")
        return browser
    except Exception as e:
        logger.error(f"Error initializing browser: {e}", exc_info=True)
        raise

def godaddy_login(page):
    try:
        load_dotenv() # Load from .env file

        godaddy_login_url = "https://sso.godaddy.com/?realm=idp&app=cart&path=%2Fcheckoutapi%2Fv1%2Fredirects%2Flogin"
        time.sleep(random.uniform(1.0, 2.0))
        page.goto(godaddy_login_url)

        login_user = os.getenv("GODADDY_USERNAME")
        login_passw = os.getenv("GODADDY_PASSWORD")

        # Fill
        time.sleep(random.uniform(0.5, 1.2))
        page.fill("#username", login_user)
        time.sleep(random.uniform(0.3, 0.7))
        page.fill("#password", login_passw)

        # Click login
        time.sleep(random.uniform(0.4, 0.6))
        page.locator("#submitBtn").click()

        time.sleep(1)
        page.pause()

        page.wait_for_load_state("networkidle")
        
    except Exception as e:
        logger.error(f"Error during login: {e}", exc_info=True)
        raise



def update_dns(page):
    try:
        test_ids = [
            "table-checkbox-select-13fd365d-d3d6-4c42-b189-9d439f71ab53",
            "table-checkbox-select-9b512069-6d2d-4572-ba8e-4b46ae69fccf",
            "table-checkbox-select-cd509f12-9afa-441b-be9a-34407c712ab3",
            "table-checkbox-select-b9f23e0a-248a-436f-b5b6-025c7edd7e22",
            "table-checkbox-select-3b33ad9b-b2f7-474c-bc59-b3a0e0a0764e",
            "table-checkbox-select-701b8e69-ef05-469f-bbcb-24305b971a26",
            "table-checkbox-select-112de572-7519-4ae0-ac4a-92a86803a589"
        ]

        for i in test_ids:
            time.sleep(random.uniform(0.1, 0.4))
            page.get_by_test_id(i).check()

        time.sleep(1)
        page.locator("div").filter(has_text=re.compile(r"^Modifica$")).click()
        time.sleep(random.uniform(0.8, 1.5))

        my_ip = get_my_ip()
        for i in range(1,7):
            page.get_by_test_id("dataDnsFieldInput").nth(i).fill(my_ip)
            time.sleep(random.uniform(0.4, 0.6))
        
        time.sleep(random.uniform(0.5, 1.0))
        page.get_by_role("button", name="Salva tutti i record").click()
        logger.info("DNS update completed successfully")
    except Exception as e:
        logger.error(f"Error updating DNS: {e}", exc_info=True)
        raise

with sync_playwright() as p:

    # Init the browser
    setup_automation_profile()
    browser = init_browser()
    page = browser.new_page()

    # Login

    land_to_page = "https://dashboard.godaddy.com/venture?ventureId=c35e4138-68fd-48f4-b4ef-fd62c487c6a3&itc=vh_ventureredirect&referrer=venture-redirector"
    login_page = "https://sso.godaddy.com/login"

    # Attempt to go to the target page
    page.goto(land_to_page)
    time.sleep(2)

    # if we were redirected to the login page, do the login
    if login_page in page.url:
        godaddy_login(page)
    
    accept_button = page.get_by_role("button", name="Accetta")
    if accept_button.is_hidden() == False:
        print(accept_button)
        accept_button.click()

    # Click on Dominio
    time.sleep(2)
    #page.get_by_role("link", name="Dominio").click()
    page.locator("a").filter(has_text="Gestisci dominio").nth(1).click()

    page.get_by_role("tab",name="DNS").click()

    update_dns(page)

    page.pause()

    browser.close()