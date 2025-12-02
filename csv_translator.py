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
GOOGLE_CATEGORY_ID = "916" 

# *** YOUR STORE CODE ***
STORE_CODE = "Albar"

def clean_image_url(raw_url):
    """Replaces {resize} with w1920 and strips whitespace."""
    if not raw_url: return ""
    clean = raw_url.strip()
    clean = clean.replace("{resize}", "w1920").replace("%7Bresize%7D", "w1920")
    return clean

def is_valid_image(url):
    """Checks if the URL looks like a real image file."""
    if not url: return False
    url_lower = url.lower()
    # Must start with http and end with a valid extension
    if not url_lower.startswith("http"): return False
    if any(ext in url_lower for ext in ['.jpg', '.jpeg', '.png', '.webp']):
        return True
    return False

def get_row_value(row, possible_keys):
    """Helper to find a value even if keys vary."""
    normalized_row = {k.strip().lower(): v for k, v in row.items() if k}
    for key in possible_keys:
        clean_key = key.lower()
        if clean_key in normalized_row:
            return normalized_row[clean_key]
    return ""

def get_google_feed():
    print("Downloading CSV feed...")
    try:
        response = requests.get(SOURCE_CSV_URL)
        response.raise_for_status()
        response.encoding = 'utf-8-sig'
        csv_content = response.text
        reader = csv.DictReader(io.StringIO(csv_content))
        vehicles = list(reader)
        print(f"Successfully loaded {len(vehicles)} vehicles.")
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
        price_raw = get_row_value(row, ['suppliedPrice', 'price', 'retail_price'])
        if not price_raw or price_raw == '0': continue

        item = ET.SubElement(channel, "item")
        
        # 1. ID
        veh_id = get_row_value(row, ['registration', 'vin', 'id'])
        ET.SubElement(item, "g:id").text = veh_id

        # 2. Basic Info
        make = get_row_value(row, ['make'])
        model = get_row_value(row, ['model'])
        derivative = get_row_value(row, ['derivative'])
        color = get_row_value(row, ['colour'])
        year = get_row_value(row, ['yearOfManufacture'])
        mileage = get_row_value(row, ['odometer
