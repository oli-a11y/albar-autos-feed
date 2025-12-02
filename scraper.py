import json
import xml.etree.ElementTree as ET
from xml.dom import minidom

# Configuration
INPUT_FILE = "google_vehicle_ads_feed.json"
OUTPUT_FILE = "feed.xml"
DEALER_NAME = "Albar Autos"
DEALER_URL = "https://albarautos.co.uk"
# Official Google Taxonomy for Cars
GOOGLE_CATEGORY = "Vehicles & Parts > Vehicles > Motor Vehicles > Cars, Trucks & Vans"

def generate_xml_feed():
    try:
        with open(INPUT_FILE, 'r') as f:
            vehicles = json.load(f)
        print(f"Loaded {len(vehicles)} vehicles from JSON.")
    except FileNotFoundError:
        print("Error: JSON file not found. Run scraper.py first!")
        return

    rss = ET.Element("rss", version="2.0")
    rss.set("xmlns:g", "http://base.google.com/ns/1.0")
    
    channel = ET.SubElement(rss, "channel")
    ET.SubElement(channel, "title").text = DEALER_NAME
    ET.SubElement(channel, "link").text = DEALER_URL
    ET.SubElement(channel, "description").text = f"Vehicle Feed for {DEALER_NAME}"

    for car in vehicles:
        item = ET.SubElement(channel, "item")
        
        ET.SubElement(item, "g:id").text = car.get("vin")
        ET.SubElement(item, "g:title").text = car.get("title")
        ET.SubElement(item, "g:description").text = car.get("description")
        ET.SubElement(item, "g:link").text = car.get("link")
        
        if car.get("image_link"):
            ET.SubElement(item, "g:image_link").text = car.get("image_link")
            
        add_imgs = car.get("additional_image_link", [])
        if add_imgs:
            ET.SubElement(item, "g:additional_image_link").text = ",".join(add_imgs)

        ET.SubElement(item, "g:price").text = car.get("price")
        ET.SubElement(item, "g:condition").text = "used"
        
        # --- NEW & FIXED FIELDS ---
        
        # 1. Google Product Category (Static Value)
        ET.SubElement(item, "g:google_product_category").text = GOOGLE_CATEGORY
        
        # 2. Vehicle Type (Required)
        ET.SubElement(item, "g:vehicle_type").text = "car"
        
        # 3. Brand & Model (Now separated)
        ET.SubElement(item, "g:brand").text = car.get("brand")
        ET.SubElement(item, "g:model").text = car.get("model")
        
        # 4. Color (Now extracted)
        ET.SubElement(item, "g:color").text = car.get("color")
        
        # --------------------------
        
        mileage = car.get("mileage")
        if "miles" not in mileage.lower():
            mileage = f"{mileage} miles"
        ET.SubElement(item, "g:mileage").text = mileage
        
        ET.SubElement(item, "g:year").text = car.get("year")
        ET.SubElement(item, "g:availability").text = "in_stock"

    xml_str = minidom.parseString(ET.tostring(rss)).toprettyxml(indent="  ")
    
    with open(OUTPUT_FILE, "w") as f:
        f.write(xml_str)
        
    print(f"SUCCESS: Generated {OUTPUT_FILE} with fixes.")

if __name__ == "__main__":
    generate_xml_feed()
