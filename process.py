# def process_user(self, user_id, hashtag):
#     """
#     Processes a single Twitter user by navigating to the user's profile, extracting the top 3 tweet elements,
#     and retweeting only those tweets that have not been processed before. It does so by checking the saved
#     tweet IDs from file (via get_logged_tweet_ids). When a new tweet is retweeted, its tweet ID is logged.
#     Only the top tweet id (the most recent tweet) is kept in the file.
    
#     Returns:
#         tuple(bool, str): A success flag and a message.
#     """
#     try:
#         # Check if navigation to the user's profile is successful
#         if not self.navigate_to_user_profile(user_id):
#             return False, f"Could not navigate to {user_id}'s profile."
        
#         time.sleep(3)
#         wait = WebDriverWait(self.driver, 20)
        
#         # Locate tweet elements on the user's profile page
#         tweets = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "article[data-testid='tweet']")))
        
#         # Get only the top 2 tweets for processing
#         tweet_elements = tweets[:2]
        
#         # If no tweets are found, log a warning and return
#         if not tweet_elements:
#             logger.warning(f"No tweets found for {user_id}")
#             return False, f"No tweets found for {user_id}"
        
#         # Retrieve previously processed tweet IDs
#         logged_ids = self.get_logged_tweet_ids(user_id)
#         successful_retweets = 0
#         tweet_urls = []
        
#         # Extract tweet URLs from tweet elements
#         for tweet in tweet_elements:
#             try:
#                 link_element = tweet.find_element(By.XPATH, './/a[contains(@href, "/status/")]')
#                 tweet_url = link_element.get_attribute("href")
#                 tweet_urls.append(tweet_url)
#             except Exception as e:
#                 logger.error(f"Error extracting tweet URL for {user_id}: {str(e)}")
#                 self.logout()
#                 return self.process_user(user_id, hashtag)
        
#         # If no tweet URLs were found, return failure
#         if not tweet_urls:
#             return False, f"No tweet URLs found for {user_id}"
        
#         # Process each tweet URL
#         for i, tweet_url in enumerate(tweet_urls):
#             try:
#                 # Extract tweet ID from URL
#                 tweet_id = tweet_url.split("/status/")[-1].split('?')[0]
                
#                 # Check if the tweet has already been processed
#                 if tweet_id in logged_ids:
#                     logger.info(f"Tweet {tweet_id} for {user_id} already processed, skipping.")
#                     continue
                
#                 logger.info(f"Processing tweet {i+1} for {user_id}: {tweet_url}")
#                 self.driver.get(tweet_url)
#                 time.sleep(3)
                
#                 # Locate the tweet details page
#                 tweet_detail = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "article[data-testid='tweet']")))
                
#                 # Retweet the tweet with the specified hashtag
#                 retweeted = self.repost_with_hashtag(tweet_detail, [hashtag])
                
#                 # Log success or failure of the retweet attempt
#                 if retweeted:
#                     logger.info(f"Successfully retweeted tweet for {user_id}: {tweet_id}")
#                     successful_retweets += 1
#                 else:
#                     logger.warning(f"Failed to retweet tweet for {user_id}: {tweet_id}")
                
#                 # Navigate back to the user's profile page before processing the next tweet
#                 self.driver.get(f"https://twitter.com/{user_id}")
#                 time.sleep(5)
#             except Exception as e:
#                 logger.error(f"Error processing a tweet for {user_id}: {str(e)}")
#                 self.logout()
#                 return self.process_user(user_id, hashtag)
        
#         # If at least one tweet was successfully retweeted, update the logged tweet ID
#         if successful_retweets > 0:
#             self.update_logged_tweet_id(user_id, tweet_urls[0])
#             return True, f"Successfully retweeted {successful_retweets} tweets for {user_id}."
#         else:
#             return False, f"No new tweets retweeted for {user_id}"
    
#     except Exception as e:
#         # Log any error that occurs in the entire process
#         logger.error(f"Error processing user {user_id}: {str(e)}")
#         self.logout()
#         return self.process_user(user_id, hashtag)
