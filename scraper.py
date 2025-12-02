import re
import json
import time
import urllib.parse
from playwright.sync_api import sync_playwright

# Configuration
SEARCH_URL = "https://albarautos.co.uk/car-search"
OUTPUT_FILE = "google_vehicle_ads_feed.json"

def get_clean_text(element):
    if not element: return ""
    return element.inner_text().strip().replace("\n", " ")

def clean_image_url(raw_url):
    """Decodes the URL and forces high-res."""
    if not raw_url: return None
    
    # 1. Decode Next.js wrapper
    if "url=" in raw_url:
        try:
            parsed = urllib.parse.urlparse(raw_url)
            query_params = urllib.parse.parse_qs(parsed.query)
            if 'url' in query_params:
                raw_url = query_params['url'][0]
        except:
            pass
    
    # 2. Fix Relative Paths
    if raw_url.startswith("/"):
        raw_url = "https://albarautos.co.uk" + raw_url

    # 3. Force High Resolution (1920px)
    raw_url = raw_url.replace("%7Bresize%7D", "w1920").replace("{resize}", "w1920")
    
    return raw_url

def run_scraper():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = context.new_page()

        print(f"--- STEP 1: Collecting Vehicle Links ---")
        page.goto(SEARCH_URL)
        
        for _ in range(5):
            page.mouse.wheel(0, 2000)
            time.sleep(1)

        try:
            page.wait_for_selector("a[href*='/car-details/']", timeout=10000)
            all_links = page.locator("a[href*='/car-details/']").all()
        except:
            all_links = []
        
        car_urls = set()
        for link in all_links:
            href = link.get_attribute("href")
            if href:
                clean_href = href.split('?')[0]
                full_url = "https://albarautos.co.uk" + clean_href if clean_href.startswith("/") else clean_href
                car_urls.add(full_url)
        
        print(f"Found {len(car_urls)} unique vehicles.")

        inventory = []
        
        # --- STEP 2: Process Each Vehicle ---
        for index, url in enumerate(car_urls):
            print(f"Processing [{index+1}/{len(car_urls)}]: {url.split('/')[-1][:25]}...") 
            
            try:
                page.goto(url)
                # Wait for title - confirms page load
                page.wait_for_selector("h1", timeout=5000)
                
                # --- STRATEGY: HARVEST META TAGS ---
                final_images = []
                seen_urls = set()
                
                # Find ALL meta tags with property="og:image"
                # This solves the "Strict Mode Violation" by asking for .all()
                meta_tags = page.locator('meta[property="og:image"]').all()
                
                for meta in meta_tags:
                    raw_link = meta.get_attribute("content")
                    clean_link = clean_image_url(raw_link)
                    
                    if clean_link and clean_link not in seen_urls:
                        final_images.append(clean_link)
                        seen_urls.add(clean_link)

                # Limit to 10 images max
                final_images = final_images[:10]
                
                main_image = final_images[0] if final_images else ""
                additional_images = final_images[1:] if len(final_images) > 1 else []

                # --- EXTRACT DATA ---
                page_content = page.content()
                vin_match = re.search(r'\b[A-HJ-NPR-Z0-9]{17}\b', page_content)
                vin = vin_match.group(0) if vin_match else None
                if not vin:
                    print("   -> SKIP: No VIN found.")
                    continue

                title = get_clean_text(page.locator("h1").first)

                price = "0"
                candidates = page.locator("span.text-main.font-bold").all()
                for span in candidates:
                    text = span.inner_text()
                    if "£" in text and "/month" not in text and "HP" not in text:
                        clean_price = text.replace("£", "").replace(",", "").strip()
                        if clean_price.isdigit() and int(clean_price) > 1000:
                            price = clean_price
                            break

                body_text = page.inner_text("body")
                mileage = "0"
                match = re.search(r'(\d{1,3}(,\d{3})*)\s*(miles|Miles)', body_text)
                if match: mileage = match.group(1).replace(",", "")

                year = "2020"
                match = re.search(r'\b(20\d{2}|19\d{2})\b', title)
                if match: year = match.group(1)

                car_object = {
                    "offer_id": vin,
                    "vin": vin,
                    "title": title,
                    "description": f"{title} - {year} - {mileage} miles.",
                    "link": url,
                    "image_link": main_image,
                    "additional_image_link": additional_images,
                    "price": f"{price} GBP",
                    "brand": title.split(" ")[0],
                    "condition": "used",
                    "mileage": f"{mileage} miles",
                    "year": year
                }
                
                inventory.append(car_object)
                
                # DEBUG: Show count and unique ID
                img_count = len(final_images)
                first_id = final_images[0][-10:] if final_images else "None"
                print(f"   -> OK. Captured {img_count} images (ID: ...{first_id})")

            except Exception as e:
                print(f"   -> Error: {e}")

        with open(OUTPUT_FILE, 'w') as f:
            json.dump(inventory, f, indent=2)
        
        print(f"\nCOMPLETE. Saved {len(inventory)} vehicles.")
        browser.close()

if __name__ == "__main__":
    run_scraper()
