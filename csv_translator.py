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
STORE_CODE = "Albar" 

def clean_image_url(raw_url):
    """Replaces {resize} with w1920 and strips whitespace."""
    if not raw_url: return ""
    clean = raw_url.strip()
    clean = clean.replace("{resize}", "w1920").replace("%7Bresize%7D", "w1920")
    return clean

def get_row_value(row, possible_keys):
    """
    Helper to find a value even if the case/spacing is slightly off.
    e.g. finds 'suppliedPrice' even if row has 'suppliedPrice '
    """
    # 1. Normalize the row keys (strip spaces, lower case)
    normalized_row = {k.strip().lower(): v for k, v in row.items() if k}
    
    # 2. Check for our target keys
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
        # Force UTF-8-SIG to handle potential BOM (hidden characters)
        response.encoding = 'utf-8-sig'
        csv_content = response.text
        
        # Parse CSV
        reader = csv.DictReader(io.StringIO(csv_content))
        
        # DEBUG: Print the actual headers found to help debug if needed
        if reader.fieldnames:
            print(f"DEBUG: Headers found: {reader.fieldnames}")
            
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
        # 1. Price (CRITICAL FIELD)
        # We look for suppliedPrice, price, or retail_price
        price_raw = get_row_value(row, ['suppliedPrice', 'price', 'retail_price', 'asking_price'])
        
        # Skip if no price
        if not price_raw or price_raw == '0':
            continue

        item = ET.SubElement(channel, "item")
        
        # 2. ID (Registration or VIN)
        veh_id = get_row_value(row, ['registration', 'vin', 'id'])
        ET.SubElement(item, "g:id").text = veh_id

        # 3. Basic Details
        make = get_row_value(row, ['make', 'manufacturer'])
        model = get_row_value(row, ['model'])
        derivative = get_row_value(row, ['derivative', 'variant'])
        color = get_row_value(row, ['colour', 'color'])
        year = get_row_value(row, ['yearOfManufacture', 'year'])
        mileage = get_row_value(row, ['odometerReadingMiles', 'mileage'])
        
        # 4. Rich Description Data
        fuel = get_row_value(row, ['fuelType', 'fuel'])
        trans = get_row_value(row, ['transmissionType', 'transmission'])
        body = get_row_value(row, ['bodyType', 'body'])
        doors = get_row_value(row, ['doors'])
        
        # Construct Title: 2018 Fiat 500 1.2 Lounge ...
        full_title = f"{year} {make} {model} {derivative}"
        ET.SubElement(item, "g:title").text = full_title
        
        # Rich Description
        desc_parts = [
            full_title,
            f"{color} Paint.",
            f"{mileage} miles.",
            f"{trans} Transmission.",
            f"{fuel} Engine.",
            f"{body} Body with {doors} doors.",
            f"Available at {DEALER_NAME}."
        ]
        ET.SubElement(item, "g:description").text = " ".join(desc_parts)

        # 5. Link
        link = get_row_value(row, ['url', 'advert_url', 'website_url'])
        ET.SubElement(item, "g:link").text = link

        # 6. Images (Pipe Separated)
        # Look for 'photos', 'image_urls', 'images'
        photos_raw = get_row_value(row, ['photos', 'image_urls', 'images', 'picture_refs'])
        
        if photos_raw:
            # Split by pipe '|' or comma ',' just in case
            delimiter = '|' if '|' in photos_raw else ','
            all_imgs = [clean_image_url(x) for x in photos_raw.split(delimiter) if x.strip()]
            
            if len(all_imgs) > 0:
                ET.SubElement(item, "g:image_link").text = all_imgs[0]
            
            if len(all_imgs) > 1:
                ET.SubElement(item, "g:additional_image_link").text = ",".join(all_imgs[1:11])

        # 7. Price
        ET.SubElement(item, "g:price").text = f"{price_raw} GBP"

        # 8. Google Taxonomy & Specifics
        ET.SubElement(item, "g:brand").text = make
        ET.SubElement(item, "g:model").text = model
        ET.SubElement(item, "g:color").text = color
        ET.SubElement(item, "g:year").text = year
        ET.SubElement(item, "g:mileage").text = f"{mileage} miles"
        
        ET.SubElement(item, "g:condition").text = "used"
        ET.SubElement(item, "g:vehicle_type").text = "car"
        ET.SubElement(item, "g:google_product_category").text = GOOGLE_CATEGORY_ID
        ET.SubElement(item, "g:store_code").text = STORE_CODE
        ET.SubElement(item, "g:vehicle_fulfillment").text = "in_store"
        ET.SubElement(item, "g:availability").text = "in_stock"

        count += 1

    # Save
    xml_str = minidom.parseString(ET.tostring(rss)).toprettyxml(indent="  ")
    with open(OUTPUT_FILE, "w") as f:
        f.write(xml_str)
    
    print(f"SUCCESS: Generated {OUTPUT_FILE} with {count} vehicles.")

if __name__ == "__main__":
    data = get_google_feed()
    if data:
        generate_xml(data)
