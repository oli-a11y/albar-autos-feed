import json
import xml.etree.ElementTree as ET
from xml.dom import minidom

# Configuration
INPUT_FILE = "google_vehicle_ads_feed.json"
OUTPUT_FILE = "feed.xml"
DEALER_NAME = "Albar Autos"
DEALER_URL = "https://albarautos.co.uk"

def generate_xml_feed():
    # 1. Load the JSON data
    try:
        with open(INPUT_FILE, 'r') as f:
            vehicles = json.load(f)
        print(f"Loaded {len(vehicles)} vehicles from JSON.")
    except FileNotFoundError:
        print("Error: JSON file not found. Run scraper.py first!")
        return

    # 2. Create the XML Root (RSS 2.0 Standard)
    rss = ET.Element("rss", version="2.0")
    rss.set("xmlns:g", "http://base.google.com/ns/1.0") # The Magic Google Namespace
    
    channel = ET.SubElement(rss, "channel")
    ET.SubElement(channel, "title").text = DEALER_NAME
    ET.SubElement(channel, "link").text = DEALER_URL
    ET.SubElement(channel, "description").text = f"Vehicle Feed for {DEALER_NAME}"

    # 3. Loop through vehicles and add to XML
    for car in vehicles:
        item = ET.SubElement(channel, "item")
        
        # --- MAPPING JSON TO GOOGLE XML TAGS ---
        
        # ID (VIN is best, fallback to Offer ID)
        ET.SubElement(item, "g:id").text = car.get("vin")
        
        # Basic Info
        ET.SubElement(item, "g:title").text = car.get("title")
        ET.SubElement(item, "g:description").text = car.get("description")
        ET.SubElement(item, "g:link").text = car.get("link")
        
        # Main Image
        if car.get("image_link"):
            ET.SubElement(item, "g:image_link").text = car.get("image_link")
            
        # Additional Images (Comma separated string)
        add_imgs = car.get("additional_image_link", [])
        if add_imgs:
            # Google prefers a comma-separated list for this field
            ET.SubElement(item, "g:additional_image_link").text = ",".join(add_imgs)

        # Price & Condition
        ET.SubElement(item, "g:price").text = car.get("price") # Already has " GBP"
        ET.SubElement(item, "g:condition").text = "used"
        
        # Vehicle Specifics
        ET.SubElement(item, "g:brand").text = car.get("brand")
        ET.SubElement(item, "g:vehicle_type").text = "car"
        
        # Mileage & Year
        # Ensure mileage has unit (e.g., "12000 miles")
        mileage = car.get("mileage")
        if "miles" not in mileage.lower():
            mileage = f"{mileage} miles"
        ET.SubElement(item, "g:mileage").text = mileage
        
        ET.SubElement(item, "g:year").text = car.get("year")
        
        # Availability (Stock is live on site, so it's in stock)
        ET.SubElement(item, "g:availability").text = "in_stock"

    # 4. Formatting & Saving
    # We use minidom to make the XML "pretty" (readable by humans)
    xml_str = minidom.parseString(ET.tostring(rss)).toprettyxml(indent="  ")
    
    with open(OUTPUT_FILE, "w") as f:
        f.write(xml_str)
        
    print(f"SUCCESS: Generated {OUTPUT_FILE} with {len(vehicles)} items.")
    print("You can now upload this file to Google Merchant Center.")

if __name__ == "__main__":
    generate_xml_feed()
