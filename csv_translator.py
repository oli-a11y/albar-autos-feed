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

def is_valid_image(url):
    """Checks if the URL looks like a real image file."""
    if not url: return False
    url_lower = url.lower()
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

def clean_drivetrain(dt_text):
    """Maps verbose drivetrains to Google's preferred abbreviations."""
    if not dt_text: return ""
    dt_lower = dt_text.lower()
    if "front" in dt_lower: return "FWD"
    if "rear" in dt_lower: return "RWD"
    if "4x4" in dt_lower or "four" in dt_lower or "all" in dt_lower: return "4WD"
    return dt_text

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
        
        # --- CORE IDENTIFIERS ---
        veh_id = get_row_value(row, ['registration', 'vin', 'id'])
        ET.SubElement(item, "g:id").text = veh_id

        make = get_row_value(row, ['make'])
        model = get_row_value(row, ['model'])
        derivative = get_row_value(row, ['derivative'])
        color = get_row_value(row, ['colour'])
        year = get_row_value(row, ['yearOfManufacture'])
        mileage = get_row_value(row, ['odometerReadingMiles'])
        
        # --- NEW ATTRIBUTES (BATCH 2) ---
        body_style = get_row_value(row, ['bodyType'])
        if body_style:
            ET.SubElement(item, "g:body_style").text = body_style

        transmission = get_row_value(row, ['transmissionType'])
        if transmission:
            ET.SubElement(item, "g:transmission").text = transmission

        fuel_type = get_row_value(row, ['fuelType'])
        if fuel_type:
            ET.SubElement(item, "g:fuel_type").text = fuel_type

        drivetrain = clean_drivetrain(get_row_value(row, ['drivetrain']))
        if drivetrain:
            ET.SubElement(item, "g:drivetrain").text = drivetrain

        doors = get_row_value(row, ['doors'])
        if doors:
            ET.SubElement(item, "g:doors").text = doors

        # --- PREVIOUS ATTRIBUTES (BATCH 1) ---
        trim = get_row_value(row, ['trim'])
        if trim and trim.lower() != 'unlisted':
            ET.SubElement(item, "g:trim").text = trim

        engine_size = get_row_value(row, ['badgeEngineSizeLitres'])
        if engine_size:
            ET.SubElement(item, "g:engine").text = f"{engine_size}L"

        elec_range = get_row_value(row, ['batteryRangeMiles'])
        if elec_range and elec_range != '0':
            ET.SubElement(item, "g:electric_range").text = f"{elec_range} miles"

        emissions = get_row_value(row, ['emissionClass'])
        if emissions:
            ET.SubElement(item, "g:emissions_standard").text = emissions

        mpg = get_row_value(row, ['fuelEconomyWLTPCombinedMPG', 'fuelEconomyNEDCCombinedMPG'])
        if mpg and mpg != '0':
            ET.SubElement(item, "g:fuel_efficiency").text = f"{mpg} MPG"

        # --- TITLES & DESCRIPTION ---
        full_title = f"{year} {make} {model} {derivative}"
        ET.SubElement(item, "g:title").text = full_title
        
        desc_parts = [
            f"{full_title}.",
            f"Color: {color}.",
            f"Mileage: {mileage} miles.",
            f"Body: {body_style}." if body_style else "",
            f"Transmission: {transmission}." if transmission else "",
            f"Fuel: {fuel_type}." if fuel_type else "",
            f"Doors: {doors}." if doors else "",
            f"Available at {DEALER_NAME}."
        ]
        clean_desc = " ".join([p for p in desc_parts if p])
        ET.SubElement(item, "g:description").text = clean_desc

        # --- LINKS & IMAGES ---
        link = get_row_value(row, ['url', 'advert_url'])
        ET.SubElement(item, "g:link").text = link
        ET.SubElement(item, "g:link_template").text = f"{link}?store={{store_code}}"

        # Added 'photosurl' to the list of keys to check
        photos_raw = get_row_value(row, ['photos', 'image_urls', 'photosurl'])
        if photos_raw:
            delimiter = '|' if '|' in photos_raw else ','
            all_imgs = [clean_image_url(x) for x in photos_raw.split(delimiter) if x.strip()]
            valid_imgs = [img for img in all_imgs if is_valid_image(img)]
            
            if len(valid_imgs) > 0:
                ET.SubElement(item, "g:image_link").text = valid_imgs[0]
            if len(valid_imgs) > 1:
                ET.SubElement(item, "g:additional_image_link").text = ",".join(valid_imgs[1:11])

        # --- STANDARD GOOGLE FIELDS ---
        ET.SubElement(item, "g:price").text = f"{price_raw} GBP"
        ET.SubElement(item, "g:brand").text = make
        ET.SubElement(item, "g:model").text = model
        ET.SubElement(item, "g:color").text = color
        ET.SubElement(item, "g:year").text = year
        ET.SubElement(item, "g:mileage").text = f"{mileage} miles"
        
        ET.SubElement(item, "g:condition").text = "used"
        ET.SubElement(item, "g:vehicle_type").text = "car"
        ET.SubElement(item, "g:google_product_category").text = GOOGLE_CATEGORY_ID
        
        # Nested Fulfillment
        fulfillment = ET.SubElement(item, "g:vehicle_fulfillment")
        ET.SubElement(fulfillment, "g:option").text = "in_store"
        ET.SubElement(fulfillment, "g:store_code").text = STORE_CODE

        ET.SubElement(item, "g:store_code").text = STORE_CODE

        count += 1

    xml_str = minidom.parseString(ET.tostring(rss)).toprettyxml(indent="  ")
    with open(OUTPUT_FILE, "w") as f:
        f.write(xml_str)
    print(f"SUCCESS: Generated {OUTPUT_FILE} with {count} vehicles.")

if __name__ == "__main__":
    data = get_google_feed()
    if data:
        generate_xml(data)
