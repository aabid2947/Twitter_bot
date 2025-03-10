from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
import time
import random
import os

from utils import *

def login(driver, username, password, phone):
    """
    Logs into Twitter with provided credentials.

    Args:
    - driver: Selenium WebDriver instance.
    - username: Twitter username.
    - password: Twitter password.
    - phone: Phone Number added in Twitter.

    Returns:
    - True if login successful, False otherwise.
    """
    # try:
    #     driver.get("https://twitter.com/login")
    #     time.sleep(2)  # Let the page load

    #     # Use new find_element with By class
    #     driver.find_element(By.NAME, "text").send_keys(username)
    #     driver.find_element(By.CSS_SELECTOR, "div[data-testid='LoginForm_Login_Button']").click()

    #     # Wait for password input to be available
    #     WebDriverWait(driver, 10).until(
    #         EC.presence_of_element_located((By.NAME, "password"))
    #     ).send_keys(password)

    #     driver.find_element(By.CSS_SELECTOR, "div[data-testid='LoginForm_Login_Button']").click()
        
    #     # Wait for login to complete
    #     WebDriverWait(driver, 10).until(EC.url_contains("twitter.com/home"))
        
    #     return True
    # except Exception as e:
    #     print(f"Error during login: {str(e)}")
    #     return False

    try:

        # Open the Twitter (X) login page
        driver.get("https://x.com/i/flow/login")
        
        # Wait for the page to load
        time.sleep(10)
        try:
        
            # Locate the username input field and enter username
            username_input = driver.find_element(By.TAG_NAME, 'input')  # The only available input field
            username_input.send_keys(username)
            
            # Press 'Next' to go to the password field
            username_input.send_keys(Keys.ENTER)
        except Exception as e:
            print(f"Error during login: {str(e)}")
            return False
        
        # Wait for the password field to load
        time.sleep(5)
        
        try:
            # Locate the password input field and enter password
            password_input = driver.find_element(By.NAME, 'password')
            password_input.send_keys(password)
            
            # Press 'Enter' to log in
            password_input.send_keys(Keys.ENTER)
            
            # Wait for login to complete
            time.sleep(5)
        except Exception as e:
            print(f"Error during login: {str(e)}")
            try:
                     # Locate the username input field and enter username
                phone_input = driver.find_element(By.TAG_NAME, 'input')  # The only available input field
                phone_input.send_keys(phone)
                
                # Press 'Next' to go to the password field
                phone_input.send_keys(Keys.ENTER)
                
                # Wait for the password field to load
                time.sleep(5)

                # Locate the password input field and enter password
                password_input = driver.find_element(By.NAME, 'password')
                password_input.send_keys(password)
                
                # Press 'Enter' to log in
                password_input.send_keys(Keys.ENTER)
            except Exception as e:
                return False
            
        # except:
       
            
            # Wait for login to complete
            time.sleep(5)

        while driver.current_url == "https://x.com/account/access":
            print('Automation Paused: Waiting to complete verification.')
            time.sleep(90)
        
        try:
            if driver.find_element(By.CSS_SELECTOR, 'a[href="https://help.twitter.com/managing-your-account/additional-information-request-at-login"]'):
                print('Waiting for entering email for verification.')
                time.sleep(90)
        except:
            pass

        time.sleep(3)

        if driver.current_url == "https://x.com/home":
            return True
        else:
            return False

    except Exception as e:
        print(f"Error during login: {str(e)}")
        return False


def logout(driver):
    """
    Logs out from Twitter.

    Args:
    - driver: Selenium WebDriver instance.
    """
    try:
        # Logout
        driver.get('https://x.com/logout')
        time.sleep(2)
        
        # Click confirm logout button
        confirm_button = driver.find_element(By.CSS_SELECTOR, '[data-testid="confirmationSheetConfirm"]')
        confirm_button.click()

        # Wait for logout to complete
        time.sleep(5)

    except Exception as e:
        print(f"Error during logout: {str(e)}")