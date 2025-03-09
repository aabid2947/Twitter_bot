# Twitter Repost Bot

An automated application that reposts tweets with specific hashtags from targeted Twitter users.

## Features

- Web interface built with Flask and Tailwind CSS
- Upload a text file containing target Twitter user IDs
- Login to Twitter using your credentials
- Repost tweets with custom hashtags
- Selenium-based web scraping for Twitter interaction

## Setup

1. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Make sure you have Chrome browser installed and the appropriate ChromeDriver version.

3. Run the application:
   ```
   python app.py
   ```

4. Access the web interface at `http://localhost:5000`

## Usage

1. Prepare a text file with Twitter user IDs (one per line)
2. Upload the file through the web interface
3. Enter your Twitter credentials
4. Specify hashtags to add to reposts
5. Start the repost process

## Note

This application is for educational purposes. Please ensure you comply with Twitter's Terms of Service when using this tool. 