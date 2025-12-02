import csv
import requests
import io
import xml.etree.ElementTree as ET
from xml.dom import minidom

# CONFIGURATION
# Your new Backoffice Feed URL
SOURCE_CSV_URL = "https://albarautos.co.uk/aia-feed/6181bf0c-0565-483d-8d47-decff1d423cd.csv"
OUTPUT_FILE = "feed.xml"

# CONSTANTS
DEALER_NAME = "Albar Autos"
DEALER_URL = "https://albarautos.co.uk"
GOOGLE_CATEGORY_ID = "916" # Vehicles & Parts > ... > Cars
STORE_CODE = "ALBAR_MAIN" # You might need to match this to your Google Business Profile store code

def get_google_feed():
    print("Downloading CSV feed...")
    try:
        response = requests.get(SOURCE_CSV_URL)
        response.raise_for_status()
        # Decode the CSV content
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
        # SKIP LOGIC: Filter out sold cars if the CSV has a status column
        # if row.get('Status', '').lower() == 'sold': continue

        item = ET.SubElement(channel, "item")
        
        # --- MAPPING: BACKOFFICE CSV -> GOOGLE XML ---
        # Note: We use .get() with a default to avoid crashing on missing columns
        
        # 1. ID (Registration or VIN)
        # Try 'registration', 'reg', 'vin', or 'id'
        veh_id = row.get('registration') or row.get('vin') or row.get('id') or row.get('stock_id')
        ET.SubElement(item, "g:id").text = veh_id

        # 2. Titles & Descriptions
        # We build a strong title: Year Make Model Color
        make = row.get('make', '')
        model = row.get('model', '')
        variant = row.get('derivative') or row.get('variant') or ""
        color = row.get('colour') or row.get('color') or "Unknown"
        year = row.get('year') or row.get('year_of_manufacture')
        
        full_title = f"{year} {make} {model} {variant} {color}"
        ET.SubElement(item, "g:title").text = full_title
        
        # Description
        desc = row.get('description') or row.get('advert_text') or f"{full_title} available at {DEALER_NAME}"
        ET.SubElement(item, "g:description").text = desc

        # 3. Links
        # Does the CSV have a 'url' column?
        link = row.get('url') or row.get('advert_url') or row.get('vehicle_url')
        if not link:
            # Fallback: Construct URL manually if missing
            # e.g. https://albarautos.co.uk/car-details/{id}
            link = f"https://albarautos.co.uk/used-cars/{make}-{model}-{veh_id}"
        ET.SubElement(item, "g:link").text = link

        # 4. Images
        # Usually a comma-separated list or a single URL
        img_str = row.get('image_urls') or row.get('images') or row.get('picture_refs') or ""
        all_imgs = img_str.split(',') if ',' in img_str else [img_str]
        
        # Main Image
        if len(all_imgs) > 0 and all_imgs[0]:
            ET.SubElement(item, "g:image_link").text = all_imgs[0].strip()
        
        # Additional Images (Limit to 10)
        if len(all_imgs) > 1:
            clean_adds = [img.strip() for img in all_imgs[1:11] if img.strip()]
            ET.SubElement(item, "g:additional_image_link").text = ",".join(clean_adds)

        # 5. Price
        price = row.get('price') or row.get('retail_price') or "0"
        ET.SubElement(item, "g:price").text = f"{price} GBP"

        # 6. Specifics
        ET.SubElement(item, "g:brand").text = make
        ET.SubElement(item, "g:model").text = model
        ET.SubElement(item, "g:color").text = color
        ET.SubElement(item, "g:year").text = year
        
        mileage = row.get('mileage') or "0"
        ET.SubElement(item, "g:mileage").text = f"{mileage} miles"
        
        # 7. Google Magic Fields (Hardcoded)
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
