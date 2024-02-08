import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime, timezone
import time
import mysql.connector
import logging
import random
import firebase_admin
from firebase_admin import credentials, messaging

# Configure logging
logging.basicConfig(level=logging.INFO)

# Inisialisasi Firebase Admin SDK
cred = credentials.Certificate("services.json")
firebase_admin.initialize_app(cred)

# Map channel URLs to names
channel_mapping = {
    'https://t.me/s/RACUN_SHOPEE_DISKON_PROMO_RECEH': 'Shopee',
    'https://t.me/s/RACUN_LAZADA_DISKON_PROMO_MURAH': 'Lazada',
    'https://t.me/s/racun_tokopedia_tokped': 'Tokopedia',
}

# Function to save data to MySQL database
def save_to_database(image_url, caption, channel_url):
    if not image_url:
        logging.warning("Image URL is empty. Data not saved to the database.")
        return

    # Extract platform_link from caption using regular expression
    platform_link_match = re.search(r'(https?://[^\s]+)', caption)
    platform_link = platform_link_match.group(1) if platform_link_match else None

    # Remove platform_link from caption if found
    caption = re.sub(r'(https?://[^\s]+)', '', caption).strip()

    # Use a random default caption if it is empty
    if not caption:
        default_captions = [
            "🌟 Jangan Sampai Ketinggalan!! 🌟",
            "🎉 Segera Dapatkan Diskon Spesial! 🎉",
            "⏰ Jangan Lewatkan Kesempatan Ini! ⏰",
            "✨ Gas Order!! ✨",
        ]
        caption = random.choice(default_captions)

    # Get the channel name from the mapping
    channel_name = channel_mapping.get(channel_url)

    if not channel_name:
        logging.warning("Channel URL not found in the mapping. Data not saved to the database.")
        return

    # Replace with your MySQL database connection details
    db_config = {
        'host': '188.166.231.207',
        'user': 'diskon',
        'password': 'aaaaaaac',
        'database': 'diskon',
        'charset': 'utf8mb4',
        'collation': 'utf8mb4_unicode_ci',
    }

    try:
        # Create a connection to the database
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()

        # Check for duplicate entries based on the image URL and channel
        query_check_duplicate = "SELECT * FROM posts WHERE image_link = %s AND channel = %s"
        cursor.execute(query_check_duplicate, (image_url, channel_name))
        
        if not cursor.fetchall():
            # If no duplicates, save data to the database
            query_insert = "INSERT INTO posts (image_link, caption, platform_link, channel) VALUES (%s, %s, %s, %s)"
            data_insert = (image_url, caption, platform_link, channel_name)
            cursor.execute(query_insert, data_insert)
            connection.commit()
            logging.info("Data successfully saved to the database!")

            # Ambil semua FCM token dari tabel users di database
            query_select_tokens = "SELECT fcm_token FROM users"
            cursor.execute(query_select_tokens)
            fcm_tokens = [result[0] for result in cursor.fetchall()]

            # Kirim notifikasi push ke setiap FCM token
            for fcm_token in fcm_tokens:
                send_push_notification(fcm_token, "Ada Promo Baru!", caption)
        else:
            logging.info("Data already exists in the database. Not saved.")

    except mysql.connector.Error as err:
        logging.error(f"Error: {err}")

    finally:
        # Close the database connection
        if connection.is_connected():
            cursor.close()
            connection.close()

# Function untuk mengirim notifikasi push ke FCM token
def send_push_notification(fcm_token, title, body):
    message = messaging.Message(
        notification=messaging.Notification(
            title=title,
            body=body,
        ),
        token=fcm_token,
    )

    try:
        response = messaging.send(message)
        logging.info("Successfully sent push notification to FCM token:", fcm_token)
    except Exception as e:
        logging.error("Error sending push notification:", e)


# List of Telegram channel URLs
channel_urls = ['https://t.me/s/RACUN_SHOPEE_DISKON_PROMO_RECEH', 'https://t.me/s/RACUN_LAZADA_DISKON_PROMO_MURAH', "https://t.me/s/racun_tokopedia_tokped"]



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
