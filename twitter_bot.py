"""
twitter_bot.py

This module contains the TwitterBot class which automates the process of logging in to Twitter,
navigating to user profiles (provided in a text file), retweeting the 3 latest unique tweets with a
user-supplied hashtag, and then (if monitoring is enabled) periodically checking for new tweets.
Each tweet is uniquely identified by its URL (or extracted tweet id) to prevent duplicate retweets.
"""

import json
import time
import logging
import os
import datetime
import tkinter.messagebox as messagebox
from actions import login, logout

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("twitter_bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def get_driver():
    """
    Initializes and returns a Selenium WebDriver using Selenium Manager.
    
    Returns:
        webdriver.Chrome: An instance of the Chrome WebDriver.
    """
    service = Service()  # Uses Selenium Manager
    options = webdriver.ChromeOptions()
    driver = webdriver.Chrome(service=service, options=options)
    return driver

class TwitterBot:
    def __init__(self, username, password,phone_number):
        """
        Initializes a TwitterBot instance.
        
        Args:
            username (str): Twitter username.
            password (str): Twitter password.
        
        Attributes:
            driver (webdriver.Chrome): Selenium WebDriver instance.
            results (list): List to store operation results.
            monitoring (bool): Flag for monitoring mode.
            processed_tweets_map (dict): In-memory mapping of user IDs to processed tweet IDs.
        """
        self.username = username
        self.password = password
        self.phone_number = phone_number
        self.driver = None
        self.results = []
        self.monitoring = True
        self.processed_tweets_map = {}  # e.g., { "ElonMusk": {"12345", "67890"}, ... }
        self.setup_driver()

    def setup_driver(self):
        try:
            self.driver = get_driver()
        except Exception as e:
            logger.error("Error setting up driver: " + str(e))
            messagebox.showerror("Driver Error", str(e))

    def perform_login(self,phone):
        try:
            logger.info('here')
            logger.info(self.phone_number)
            login(self.driver, self.username, self.password, self.phone_number)
            
            # if login_succes:

            logger.info("Login successful")
            return True
            # else:
            #     self.perform_login()
        except Exception as e:
            logger.error("Login failed: " + str(e))
            messagebox.showerror("Login Error", f"Login failed: {str(e)}")
            return False

    def navigate_to_user_profile(self, user_id):
        try:
            logger.info(f"Navigating to user profile: {user_id}")
            self.driver.get(f"https://twitter.com/{user_id}")
            wait = WebDriverWait(self.driver, 20)
            try:
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="primaryColumn"]')))
            except TimeoutException:
                logger.warning("Primary column not found, trying alternative selectors")
                try:
                    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="UserName"]')))
                except TimeoutException:
                    logger.warning("User name not found for " + user_id)
            page_source = self.driver.page_source.lower()
            error_messages = [
                "this account doesn't exist",
                "user not found",
                "hmm...this page doesn't exist",
                "account suspended"
            ]
            for error in error_messages:
                if error in page_source:
                    logger.warning(f"User {user_id} does not exist or is suspended")
                    self.results.append({"status": "warning", "user": user_id, "message": "User does not exist or is suspended"})
                    return False
            time.sleep(5)
            logger.info(f"Successfully navigated to {user_id}'s profile")
            return True
        except Exception as e:
            logger.error(f"Error navigating to user profile {user_id}: {str(e)}")
            self.results.append({"status": "error", "user": user_id, "message": f"Navigation error: {str(e)}"})
            return False

    def get_latest_tweets(self, user_id, count=3):
        """
        Retrieves the top 'count' tweets from a user's Twitter profile using the accessible list.
        
        Args:
            user_id (str): Twitter handle of the user.
            count (int, optional): Number of tweets to retrieve. Defaults to 3.
        
        Returns:
            list: A list of dictionaries with keys:
                  - "tweet": The tweet WebElement.
                  - "unique_id": A unique identifier (extracted from aria-labelledby if available).
                  Returns an empty list on error.
        """
        try:
            if not self.navigate_to_user_profile(user_id):
                return []
            time.sleep(3)
            container = self.driver.find_element(By.CSS_SELECTOR, '[aria-labelledby^="accessible-list-"]')
            tweets = container.find_elements(By.CSS_SELECTOR, 'article[data-testid="tweet"]')
            logger.info(f"Found {len(tweets)} tweets in accessible list for user {user_id}")
            latest_tweets = []
            for tweet in tweets[:count]:
                raw_id = tweet.get_attribute("aria-labelledby")
                if raw_id:
                    unique_id = raw_id.split()[0]
                else:
                    unique_id = self.get_tweet_id(tweet)
                logger.info(f"Tweet unique id: {unique_id}")
                latest_tweets.append({"tweet": tweet, "unique_id": unique_id})
            return latest_tweets
        except Exception as e:
            logger.error(f"Error finding tweets in accessible list for {user_id}: {str(e)}")
            return []

    def get_tweet_id(self, tweet_element):
        try:
            tweet_id = tweet_element.get_attribute("aria-labelledby")
            if tweet_id:
                logger.info(f"Extracted tweet ID from aria-labelledby: {tweet_id}")
                return tweet_id
            logger.warning("aria-labelledby attribute not found, falling back to URL extraction.")
            links = tweet_element.find_elements(By.TAG_NAME, 'a')
            for link in links:
                try:
                    href = link.get_attribute('href')
                    if href and '/status/' in href:
                        status_parts = href.split('/status/')
                        if len(status_parts) > 1:
                            status_id = status_parts[1].split('?')[0].split('/')[0]
                            logger.info(f"Extracted tweet ID: {status_id} from URL: {href}")
                            return status_id
                        return href
                except Exception as e:
                    logger.warning(f"Error extracting tweet URL: {str(e)}")
            fallback_text = tweet_element.text[:100]
            fallback_id = f"text_{hash(fallback_text)}"
            logger.warning(f"Using text hash as fallback ID: {fallback_id}")
            return fallback_id
        except Exception as e:
            logger.error(f"Error extracting tweet ID: {str(e)}")
            timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")
            return f"unknown_{timestamp}"

    def get_logged_tweet_ids(self, user_id):
        """
        Reads the posted_tweet_ids.txt file and returns a set of tweet IDs for the given user.
        (In our updated design, we store only one tweet id per user.)
        """
        logged_ids = set()
        try:
            if os.path.exists("posted_tweet_ids.txt"):
                with open("posted_tweet_ids.txt", "r", encoding="utf-8") as f:
                    for line in f:
                        parts = line.strip().split(":", 1)
                        if len(parts) == 2:
                            uid = parts[0].strip()
                            tweet_id = parts[1].strip()
                            if uid == user_id:
                                logged_ids.add(tweet_id)
        except Exception as e:
            logger.error(f"Error reading logged tweet ids for {user_id}: {str(e)}")
        return logged_ids

    def update_logged_tweet_id(self, user_id, tweet_url):
        """
        Updates the posted_tweet_ids.txt file so that for the given user, only the tweet id extracted from tweet_url is saved.
        """
        try:
            tweet_id = tweet_url.split('/status/')[-1].split('?')[0]
            existing = {}
            if os.path.exists("posted_tweet_ids.txt"):
                with open("posted_tweet_ids.txt", "r", encoding="utf-8") as f:
                    for line in f:
                        parts = line.strip().split(":", 1)
                        if len(parts) == 2:
                            existing[parts[0].strip()] = parts[1].strip()
            existing[user_id] = tweet_id
            with open("posted_tweet_ids.txt", "w", encoding="utf-8") as f:
                for uid, tid in existing.items():
                    f.write(f"{uid}: {tid}\n")
            logger.info(f"Updated logged tweet id for {user_id}: {tweet_id}")
        except Exception as e:
            logger.error(f"Error updating logged tweet id for {user_id}: {str(e)}")
    
    def find_tweet(self,driver, tweet_url):
        """
        Finds a tweet specified by URL.

        Args:
        - driver: Selenium WebDriver instance.
        - tweet_url: URL of the tweet to like.

        Returns:
        - Required tweet from the page if no error encountered else None.
        """
        try:
            driver.get(tweet_url)
            time.sleep(5)  # Let the page load
            # Find all the tweets (article elements) on the page
            tweets = driver.find_elements(By.CSS_SELECTOR, "article[data-testid='tweet']")
            for tweet in tweets:
                a_tags = tweet.find_elements(By.TAG_NAME, "a")
                for a_tag in a_tags:
                    tweet_link = a_tag.get_attribute("href")
                    if tweet_link == tweet_url:
                        return tweet
        except Exception as e:
            print(f"Error while finding tweet: {str(e)}")
            return None

    def quote_tweet(self, driver, tweet_url, quote_text, folder_path=None, image_index=None):
        """
        Quotes a tweet specified by URL.

        Args:
        - driver: Selenium WebDriver instance.
        - tweet_url: URL of the tweet to quote.
        - quote_text: text to tweet.

        Returns:
        - True if quote successful, False otherwise.
        """
        try:        
            tweet = self.find_tweet(driver, tweet_url)

            repost_button = tweet.find_element(By.CSS_SELECTOR, '[data-testid="retweet"]')
            repost_button.click()
            time.sleep(1)

            confirm_repost = driver.find_element(By.CSS_SELECTOR, 'a[href="/compose/post"]')
            confirm_repost.click()
            time.sleep(2)

            # Click on the Tweet button to open the tweet modal
            tweet_box = driver.find_element(By.CSS_SELECTOR, 'div[aria-label="Post text"]')
            tweet_box.click()
            time.sleep(1)

            # Type the tweet message
            tweet_box.send_keys(quote_text+' ') #adding space to avoid hashtag window


            # Check if folder_path is provided, and add a random image if it is
            # if folder_path and os.path.exists(folder_path):
            #     images = [f for f in os.listdir(folder_path) if f.lower().endswith(('png', 'jpg', 'jpeg', 'gif'))]
            #     if images:
            #         # random_image = os.path.join(folder_path, random.choice(images))
            #         image = get_image(folder_path=folder_path, image_index=image_index)
            #         # Find the file input element for image upload and send the file path
            #         file_input = driver.find_element(By.XPATH, '//input[@type="file"]')
            #         file_input.send_keys(image)
                    
            #         # Allow some time for the image to be processed by Twitter
            #         time.sleep(3)

            # Post the tweet
            tweet_button = driver.find_element(By.XPATH, '//button[@data-testid="tweetButton"]')
            tweet_button.click()

            # Allow time for the tweet to post
            time.sleep(5)


            return True

        except Exception as e:
            print(f"Error while quoting tweet: {str(e)}")
            return False

    def repost_with_hashtag(self, tweet_element, hashtags):
        """
        Reposts (quote tweets) a given tweet with the provided hashtag(s) as the entire comment.
        This function uses the Quote Tweet option to repost the tweet and then immediately sets the
        tweet input field to the hashtag text via JavaScript before clicking the tweet button.
        
        Args:
            tweet_element (WebElement): Selenium element representing the tweet.
            hashtags (list): List of hashtag strings to be used in the repost.
        
        Returns:
            bool: True if reposting was successful; False otherwise.
        """
        try:
            logger.info("Starting repost process with hashtag")
            clickable_elements = tweet_element.find_elements(By.TAG_NAME, 'a')
            for element in clickable_elements:
                try:
                    href = element.get_attribute('href')
                    if href and '/status/' in href:
                        logger.info(f"Found tweet link: {href}")
                        self.driver.get(href)
                        logger.info("Navigated to tweet detail page")
                        time.sleep(3)
                        break
                except Exception as e:
                    logger.warning(f"Error checking link: {str(e)}")
                    continue

            retweet_button = None
            retweet_selectors = [
                '[data-testid="retweet"]',
                '[aria-label="Retweet"]',
                '[aria-label*="retweet"]',
                '//div[@aria-label="Retweet"]',
                '//div[contains(@aria-label, "Retweet")]'
            ]
            for selector in retweet_selectors:
                try:
                    if selector.startswith("//"):
                        buttons = self.driver.find_elements(By.XPATH, selector)
                    else:
                        buttons = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if buttons:
                        for button in buttons:
                            if button.is_displayed():
                                retweet_button = button
                                logger.info(f"Found retweet button with selector: {selector}")
                                break
                    if retweet_button:
                        break
                except Exception as e:
                    logger.warning(f"Error finding retweet button with selector {selector}: {str(e)}")
            if not retweet_button:
                logger.error("Could not find retweet button")
                return False
            try:
                retweet_button.click()
                logger.info("Clicked retweet button")
            except Exception as e:
                error_str = str(e)
                if "element click intercepted" in error_str:
                    logger.error("Tweet button click intercepted; moving on to next tweet.")
                    return False
                else:
                    logger.error(f"Error clicking retweet button: {error_str}")
                    try:
                        self.driver.execute_script("arguments[0].click();", retweet_button)
                        logger.info("Clicked retweet button using JavaScript")
                    except Exception as js_e:
                        logger.error(f"JavaScript click for tweet button failed: {str(js_e)}")
                        return False

            time.sleep(2)
            quote_option = None
            quote_selectors = [
                "//span[text()='Quote']",
                "//span[contains(text(), 'Quote')]",
                "//div[contains(text(), 'Quote')]",
                '[data-testid="retweetConfirm"]',
                "//div[contains(@role, 'menuitem')]//span[contains(text(), 'Quote')]",
                "//div[@role='menuitem'][contains(., 'Quote')]"
            ]
            for selector in quote_selectors:
                try:
                    if selector.startswith("//"):
                        elements = self.driver.find_elements(By.XPATH, selector)
                    else:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        for element in elements:
                            if element.is_displayed():
                                quote_option = element
                                logger.info(f"Found quote option with selector: {selector}")
                                break
                    if quote_option:
                        break
                except Exception as e:
                    logger.warning(f"Error finding quote option with selector {selector}: {str(e)}")
            if not quote_option:
                logger.error("Could not find Quote Tweet option")
                return False
            try:
                quote_option.click()
                logger.info("Clicked Quote Tweet option")
            except Exception as e:
                logger.error(f"Error clicking Quote option: {str(e)}")
                try:
                    self.driver.execute_script("arguments[0].click();", quote_option)
                    logger.info("Clicked Quote option using JavaScript")
                except Exception as js_e:
                    logger.error(f"JavaScript click for Quote option failed: {str(js_e)}")
                    return False

            time.sleep(2)
            hashtag_text = " ".join(hashtags)
            tweet_input = None
            tweet_input_selectors = [
                '[data-testid="tweetTextarea_0"]',
                '[data-testid="tweetTextInput"]',
                '[contenteditable="true"]',
                '//div[@contenteditable="true"]',
                '//div[@role="textbox"]'
            ]
            for selector in tweet_input_selectors:
                try:
                    if selector.startswith("//"):
                        elements = self.driver.find_elements(By.XPATH, selector)
                    else:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        for element in elements:
                            if element.is_displayed():
                                tweet_input = element
                                logger.info(f"Found tweet input with selector: {selector}")
                                break
                    if tweet_input:
                        break
                except Exception as e:
                    logger.warning(f"Error finding tweet input with selector {selector}: {str(e)}")
            if not tweet_input:
                logger.error("Could not find tweet input field")
                return False

            try:
                script = "arguments[0].innerHTML = arguments[1];"
                self.driver.execute_script(script, tweet_input, hashtag_text)
                logger.info(f"Set tweet input to hashtag(s): {hashtag_text}")
            except Exception as e:
                logger.error(f"Error setting tweet input via JavaScript: {str(e)}")
                return False

            time.sleep(1)
            tweet_button = None
            tweet_button_selectors = [
                '[data-testid="tweetButton"]',
                '[data-testid="tweetButtonInline"]',
                '//span[text()="Tweet"]',
                '//div[@data-testid="tweetButtonInline"]',
                '//div[contains(@role, "button")][.//span[contains(text(), "Tweet")]]'
            ]
            for selector in tweet_button_selectors:
                try:
                    if selector.startswith("//"):
                        elements = self.driver.find_elements(By.XPATH, selector)
                    else:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        for element in elements:
                            if element.is_displayed() and element.is_enabled():
                                tweet_button = element
                                logger.info(f"Found tweet button with selector: {selector}")
                                break
                    if tweet_button:
                        break
                except Exception as e:
                    logger.warning(f"Error finding tweet button with selector {selector}: {str(e)}")
            if not tweet_button:
                logger.error("Could not find tweet button")
                return False
            try:
                tweet_button.click()
                logger.info("Clicked tweet button")
            except Exception as e:
                logger.error(f"Error clicking tweet button: {str(e)}")
                try:
                    self.driver.execute_script("arguments[0].click();", tweet_button)
                    logger.info("Clicked tweet button using JavaScript")
                except Exception as js_e:
                    logger.error(f"JavaScript click for tweet button failed: {str(js_e)}")
                    return False

            time.sleep(5)
            logger.info("Successfully reposted tweet with hashtag")
            return True
        except Exception as e:
            logger.error(f"Error reposting tweet: {str(e)}")
            return False

    def check_for_new_tweet(self, user_id, hashtag):
        """
        Checks the user's tweets in descending order (most recent first). For each tweet, if the tweet ID is not
        equal to the saved tweet ID for that user (loaded from file), it retweets the tweet and logs it.
        The process stops once a tweet is encountered that is already processed.
        Finally, it updates the saved tweet id to only the top (most recent) tweet id.
        
        Returns:
            tuple(bool, str): True and a message if at least one new tweet was retweeted; otherwise False.
        """
        try:
            new_top_tweet_id= None
             # Navigate to the user's profile
            if not self.navigate_to_user_profile(user_id):
                return False, f"Could not navigate to {user_id}'s profile."
            time.sleep(3)

            # Wait until tweet elements are loaded using a robust CSS selector
            wait = WebDriverWait(self.driver, 20)
            tweet_elements = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "article[data-testid='tweet']")))
            
            if not tweet_elements:
                logger.info(f"No tweets found for {user_id} in check_for_new_tweet")
                return False, "No tweets found"
            
            # Get the top tweet's URL and id (most recent tweet)
            try:
                top_link = tweet_elements[0].find_element(By.XPATH, './/a[contains(@href, "/status/")]')
                top_tweet_url = top_link.get_attribute("href")
            except Exception as e:
                logger.error(f"Error extracting top tweet URL for {user_id}: {str(e)}")
                return False, "Error extracting tweet URL"
            
            # Extract tweet URLs from these tweet elements
            tweet_urls = []
            for tweet in tweet_elements:
                try:
                    # Look for an anchor element whose href contains "/status/"
                    link_element = tweet.find_element(By.XPATH, './/a[contains(@href, "/status/")]')
                    tweet_url = link_element.get_attribute("href")
                    tweet_urls.append(tweet_url)
                except Exception as e:
                    logger.error(f"Error extracting tweet URL for {user_id}: {str(e)}")
            if not tweet_urls:
                return False, f"No tweet URLs found for {user_id}"
            
            
            new_tweets_retweeted = 0
            # Iterate through tweet elements in order

            for tweet in tweet_urls:
                try:
                    # Check if the top tweet id is already processed
                    # If tweet id is present and the post is not pinned
                    top_tweet_id = tweet.split("/status/")[-1].split('?')[0]
                    saved_ids = self.get_logged_tweet_ids(user_id)
                    saved_tweet_id = next(iter(saved_ids), None)

                    if saved_tweet_id == top_tweet_id:
                        logger.info(f"No new tweet for {user_id}: top tweet id {top_tweet_id} already processed")
                        break
                    
                    # Navigate to the tweet's detail page
                    self.driver.get(tweet)

                    # # Wait for the tweet detail element to be present
                    # tweet_detail = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "article[data-testid='tweet']")))

                    # # Retweet the tweet with comment using the provided hashtag
                    # retweeted = self.repost_with_hashtag(tweet_detail, [hashtag])

                    retweeted = self.quote_tweet(driver=self.driver,tweet_url=tweet,quote_text=" ".join(hashtag))

                    logger.info(f"new retweet count  {new_tweets_retweeted}")


                    # update the posted tweet ids
                    if retweeted and new_tweets_retweeted==0:
                
                        logger.info(f"Successfully retweeted new tweet for {user_id}: {top_tweet_id} as top ID")
                        

                        if user_id not in self.processed_tweets_map:
                            self.processed_tweets_map[user_id] = set()
                        else:
                            self.processed_tweets_map[user_id].clear()

                        self.processed_tweets_map[user_id].add(top_tweet_id)
                        # self.log_retweeted_tweet(user_id, tweet)
                        new_top_tweet_id=tweet
                        new_tweets_retweeted += 1

                           
                  

                    elif retweeted:
                        new_tweets_retweeted += 1

                        logger.info(f"Successfully retweeted new tweet for {user_id}: {top_tweet_id}")
                    
                    
                    # link_element = tweet.find_element(By.XPATH, './/a[contains(@href, "/status/")]')
                    # tweet_url = link_element.get_attribute("href")
                except Exception as e:
                    logger.error(f"Error extracting tweet URL for {user_id}: {str(e)}")
                    continue

        

            if new_tweets_retweeted > 0:
                logger.info(f"tweet  id updated {user_id}")
                # After processing, update the log with only the top tweet's id.
                self.update_logged_tweet_id(user_id, new_top_tweet_id)

                new_tweets_retweeted=0
                return True, f"Retweeted {new_tweets_retweeted} new tweet(s) for {user_id}."
            else:
                return False, f"No new tweets to retweet for {user_id}."
        except Exception as e:
            logger.error(f"Error in check_for_new_tweet for {user_id}: {str(e)}")
            return False, f"Error: {str(e)}"

    def process_user(self, user_id, hashtag):
        """
        Processes a single Twitter user by navigating to the user's profile, extracting the top 3 tweet elements,
        and retweeting only those tweets that have not been processed before. It does so by checking the saved
        tweet IDs from file (via get_logged_tweet_ids). When a new tweet is retweeted, its tweet ID is logged.
        Only the top tweet id (the most recent tweet) is kept in the file.
        
        Returns:
            tuple(bool, str): A success flag and a message.
        """
        try:
            if not self.navigate_to_user_profile(user_id):
                return False, f"Could not navigate to {user_id}'s profile."
            time.sleep(3)

            wait = WebDriverWait(self.driver, 20)
            tweets = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "article[data-testid='tweet']")))

            tweet_elements = tweets[:2]
            if not tweet_elements:
                logger.warning(f"No tweets found for {user_id}")
                return False, f"No tweets found for {user_id}"
            
            logged_ids = self.get_logged_tweet_ids(user_id)
            successful_retweets = 0

            tweet_urls = []
            for tweet in tweet_elements:
                try:
                    link_element = tweet.find_element(By.XPATH, './/a[contains(@href, "/status/")]')
                    tweet_url = link_element.get_attribute("href")
                    tweet_urls.append(tweet_url)
                except Exception as e:
                    logger.error(f"Error extracting tweet URL for {user_id}: {str(e)}")
        
            if not tweet_urls:
                return False, f"No tweet URLs found for {user_id}"
            
            for i, tweet_url in enumerate(tweet_urls):
                try:
                    tweet_id = tweet_url.split("/status/")[-1].split('?')[0]
                    if tweet_id in logged_ids:
                        logger.info(f"Tweet {tweet_id} for {user_id} already processed, skipping.")
                        continue

                    logger.info(f"Processing tweet {i+1} for {user_id}: {tweet_url}")
                    self.driver.get(tweet_url)
                    time.sleep(3)

                    # tweet_detail = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "article[data-testid='tweet']")))
                    # retweeted = self.repost_with_hashtag(tweet_detail, [hashtag])
                    retweeted = self.quote_tweet(driver=self.driver,tweet_url=tweet_url,quote_text=" ".join(hashtag))

                    if retweeted:
                        logger.info(f"Successfully retweeted tweet for {user_id}: {tweet_id}")
                        successful_retweets += 1
                    else:
                        logger.warning(f"Failed to retweet tweet for {user_id}: {tweet_id}")
                    self.driver.get(f"https://twitter.com/{user_id}")

                    time.sleep(5)
                except Exception as e:
                    logger.error(f"Error processing a tweet for {user_id}: {str(e)}")
            if successful_retweets > 0:
                # Update the logged tweet id to only the top (most recent) tweet id
                self.update_logged_tweet_id(user_id, tweet_urls[0])
                return True, f"Successfully retweeted {successful_retweets} tweets for {user_id}."
            else:
                return False, f"No new tweets retweeted for {user_id}"
        except Exception as e:
            logger.error(f"Error processing user {user_id}: {str(e)}")
            return False, f"Error processing user {user_id}: {str(e)}"

    def repost_tweets(self, user_ids, hashtags, start_monitoring=False, monitor_interval=300, phone=None):
        """
        Processes a list of user IDs by logging in, navigating to each user's profile, and retweeting up to
        3 tweets initially (only those which have not been processed before). Then, if monitoring is enabled,
        the bot periodically logs in, checks for new tweets using check_for_new_tweet (retweeting all new tweets
        until a known tweet is encountered), logs out, and repeats after the fixed interval.
        
        Returns:
            list: A list of dictionaries with the result for each user.
        """
        results = []
        hashtag = hashtags[0] if hashtags else ""
        
        # Initial retweeting phase
        if not self.perform_login(phone):
            messagebox.showerror("Login Error", "Unable to log in, aborting operation.")
            return []
        for user_id in user_ids:
            try:
                success, message = self.process_user(user_id, hashtag)
                results.append({"user": user_id, "status": "success" if success else "failed", "message": message})
            except Exception as e:
                logger.error(f"Error processing user {user_id}: {str(e)}")
                results.append({"user": user_id, "status": "error", "message": str(e)})
        
        
        # Monitoring phase
        if start_monitoring:
            self.monitoring = True
            logger.info("Starting monitoring mode...")
            while self.monitoring:
                time.sleep(1)
                
                for user_id in user_ids:
                    retweeted, msg = self.check_for_new_tweet(user_id, hashtag)
                    logger.info(f"Monitoring: {user_id} - {msg}")
                
            logger.info("Monitoring mode stopped.")
        else:
            self.monitoring = False
        
        if all(r["status"] == "success" for r in results):
            messagebox.showinfo("Retweet Bot", "Successfully retweeted latest tweets for all users!")
        else:
            messagebox.showerror("Retweet Bot", "Some tweets could not be retweeted. Check log for details.")
        return results

    def stop_monitoring(self):
        self.monitoring = False