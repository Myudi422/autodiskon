import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime, timezone
import time
import mysql.connector
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

# Function to save data to MySQL database
def save_to_database(image_url, caption, channel):
    if not image_url or not caption:
        logging.warning("Image URL or Caption is empty. Data not saved to the database.")
        return

    # Replace with your MySQL database connection details
    db_config = {
        'host': '188.166.231.207',
        'user': 'diskon',
        'password': 'aaaaaaac',
        'database': 'diskon',
        'charset': 'utf8mb4',  # Tambahkan pengaturan karakter set utf8mb4
        'collation': 'utf8mb4_unicode_ci',
    }

    try:
        # Create a connection to the database
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()

        # Check for duplicate entries based on the image URL and channel
        query_check_duplicate = "SELECT * FROM posts WHERE image_link = %s AND channel = %s"
        cursor.execute(query_check_duplicate, (image_url, channel))
        if not cursor.fetchall():
            # If no duplicates, save data to the database
            query_insert = "INSERT INTO posts (image_link, caption, channel) VALUES (%s, %s, %s)"
            data_insert = (image_url, caption, channel)
            cursor.execute(query_insert, data_insert)
            connection.commit()
            logging.info("Data successfully saved to the database!")
        else:
            logging.info("Data already exists in the database. Not saved.")

    except mysql.connector.Error as err:
        logging.error(f"Error: {err}")

    finally:
        # Close the database connection
        if connection.is_connected():
            cursor.close()
            connection.close()

# List of Telegram channel URLs
channel_urls = ['https://t.me/s/racuntest', 'https://t.me/s/downloadanimebatch']

while True:
    for url in channel_urls:
        try:
            # Fetch HTML content from the channel
            response = requests.get(url)
            response.raise_for_status()
            html_content = response.text

            # Parse HTML with BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')

            # Extract all posts
            posts = soup.find_all('div', class_='tgme_widget_message')

            # Initialize variables for the latest post details
            latest_time = datetime.min.replace(tzinfo=timezone.utc)
            latest_post = None
            latest_image_url = None

            # Loop to find the latest post
            for post in posts:
                post_time_str = post.find('a', class_='tgme_widget_message_date').time['datetime']
                post_time = datetime.strptime(post_time_str, "%Y-%m-%dT%H:%M:%S%z")

                if post_time > latest_time:
                    latest_time = post_time
                    latest_post = post

            # Extract image URL using XPath
            image_url_xpath_result = None
            latest_post_anchor = latest_post.find('a', class_='tgme_widget_message_photo_wrap')

            if latest_post_anchor:
                image_url_xpath_result = re.search(r"url\('(.+?)'\)", latest_post_anchor['style'])

                if image_url_xpath_result:
                    image_url_xpath_result = image_url_xpath_result.group(1)

            # Extract caption
            caption = latest_post.select_one('div.tgme_widget_message_text').get_text(strip=True)

            logging.info("Channel: %s", url)
            logging.info("Image URL (using XPath): %s", image_url_xpath_result)
            logging.info("Caption: %s", caption)

            save_to_database(image_url_xpath_result, caption, url)

        except requests.RequestException as req_err:
            logging.error(f"Request error: {req_err}")
        except Exception as e:
            logging.error(f"An unexpected error occurred: {e}")

        time.sleep(2)  # Pause for 2 seconds before the next iteration
