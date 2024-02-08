import requests
from bs4 import BeautifulSoup
from datetime import datetime
import mysql.connector
from mysql.connector import Error
import time

def insert_promo_data(merchant_id, image_url, title, claim_link, valid_from_date):
    try:
        connection = mysql.connector.connect(
            host='188.166.231.207',
            user='diskon',
            password='aaaaaaac',
            database='diskon'
        )

        if connection.is_connected():
            cursor = connection.cursor()

            cursor.execute("""
    INSERT INTO promo (merchantid, expired, link_gambar, kategori, deskripsi, lokasi, visit_link, judul)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
""", (merchant_id, valid_from_date, image_url, 'games', None, None, claim_link, title))

            connection.commit()
            print("Data berhasil dimasukkan ke database!")

    except Error as e:
        print(f"Error: {e}")

    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()


def check_duplicate_data(cursor, claim_link):
    cursor.execute("SELECT COUNT(*) FROM promo WHERE visit_link = %s", (claim_link,))
    result = cursor.fetchone()
    return result[0] > 0

def scrape_and_insert_data(merchant_id, url):
    response = requests.get(url)

    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')

        image_element = soup.select_one('.flex.bg-white.rounded-lg.shadow-md.p-6.mb-8 img')
        image_url = image_element['src'] if image_element else None

        title_element = soup.select_one('.flex-1 h3')
        title = title_element.text.strip() if title_element else None

        claim_element = soup.select_one('.flex-1 a')
        claim_link = claim_element['href'] if claim_element else None

        valid_from_element = soup.select_one('span.text-sm')
        valid_from_text = valid_from_element.text.strip() if valid_from_element else None

        valid_from_date = datetime.strptime(valid_from_text.split(" ")[-1], "%Y-%m-%d").date()

        # Menampilkan hasil
        print("Merchant ID:", merchant_id)
        print("Gambar URL:", image_url)
        print("Judul:", title)
        print("Tombol Link Claim:", claim_link)
        print("Valid from:", valid_from_date)

        try:
            connection = mysql.connector.connect(
                host='188.166.231.207',
                user='diskon',
                password='aaaaaaac',
                database='diskon'
            )

            if connection.is_connected():
                cursor = connection.cursor()

                if not check_duplicate_data(cursor, claim_link):
                    insert_promo_data(merchant_id, image_url, title, claim_link, valid_from_date)
                else:
                    print("Data sudah ada di database. Tidak dimasukkan lagi.")

        except Error as e:
            print(f"Error: {e}")

        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()

    else:
        print(f"Failed to retrieve the page. Status code: {response.status_code}")

# Daftar URL untuk setiap merchant
merchant_urls = {
    'epicgames': 'https://feed.phenx.de/lootscraper_epic_game.html',
    'googleplay': 'https://feed.phenx.de/lootscraper_google_game.html',
    'steam': 'https://feed.phenx.de/lootscraper_steam_game.html',
    'gog': 'https://feed.phenx.de/lootscraper_gog_game.html',
    'itch.io': 'https://feed.phenx.de/lootscraper_itch_game.html',
}

# Loop utama untuk menjalankan program secara terus menerus
while True:
    # Memanggil fungsi scrape_and_insert_data untuk setiap URL
    for merchant_id, url in merchant_urls.items():
        scrape_and_insert_data(merchant_id, url)
        time.sleep(2)  # Tunggu 2 detik sebelum melanjutkan ke merchant berikutnya
