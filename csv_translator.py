import csv
import requests
import io
import xml.etree.ElementTree as ET
from xml.dom import minidom

# --- CONFIGURATION ---
SOURCE_CSV_URL = "https://albarautos.co.uk/aia-feed/6181bf0c-0565-483d-8d47-decff1d423cd.csv"
OUTPUT_FILE = "feed.xml"

# CONSTANTS
DEALER_NAME = "Albar Autos"
DEALER_URL = "https://albarautos.co.uk"
GOOGLE_CATEGORY_ID = "916" # Vehicles & Parts > ... > Cars
STORE_CODE = "ALBAR_MAIN" # IMPORTANT: Make sure this matches your Google Business Profile store code!

def clean_image_url(raw_url):
    """
    1. Replaces {resize} with w1920 for high resolution.
    2. Strips whitespace.
    """
    if not raw_url: return ""
    clean = raw_url.strip()
    clean = clean.replace("{resize}", "w1920").replace("%7Bresize%7D", "w1920")
    return clean

def get_google_feed():
    print("Downloading CSV feed...")
    try:
        response = requests.get(SOURCE_CSV_URL)
        response.raise_for_status()
        csv_content = response.content.decode('utf-8')
        
        # Parse CSV
        reader = csv.DictReader(io.StringIO(csv_content))
        vehicles = list(reader)
        print(f"Successfully loaded {len(vehicles)} vehicles from source.")
        return vehicles
    except Exception as e:
        print(f"Error downloading CSV: {e}")
        return []

def generate_xml(vehicles):
    rss = ET.Element("rss", version="2.0")
    rss.set("xmlns:g", "http://base.google.com/ns/1.0")
    
    channel = ET.SubElement(rss, "channel")
    ET.SubElement(channel, "title").text = DEALER_NAME
    ET.SubElement(channel, "link").text = DEALER_URL
    ET.SubElement(channel, "description").text = f"Vehicle Feed for {DEALER_NAME}"

    count = 0
    for row in vehicles:
        # SKIP LOGIC: If price is missing or 0, skip
        price_raw = row.get('suppliedPrice', '0')
        if not price_raw or price_raw == '0':
            continue

        item = ET.SubElement(channel, "item")
        
        # --- MAPPING START ---

        # 1. ID (Using Registration)
        veh_id = row.get('registration') or row
