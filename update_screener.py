import os
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

def download_screener_csv(output_path="nasdaq_screener.csv"):
    """
    Downloads the latest NASDAQ stock screener CSV using Playwright.
    """
    print(f"\n[NASDAQ SCREENER UPDATER]")
    print(f"  Launching headless browser to download latest screener data...")
    
    output_file = Path(output_path).resolve()
    
    with sync_playwright() as p:
        # Launch browser
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            accept_downloads=True
        )
        page = context.new_page()
        
        try:
            print(f"  Navigating to NASDAQ screener page...")
            page.goto("https://www.nasdaq.com/market-activity/stocks/screener", wait_until="networkidle", timeout=60000)
            
            # Sometimes there might be a cookie consent or overlay, but usually the download button is accessible
            # Wait for the download button to be visible
            print(f"  Waiting for Download CSV button...")
            
            # The button usually has class or text "Download CSV"
            download_button = page.get_by_text("Download CSV", exact=False).first
            download_button.wait_for(state="visible", timeout=30000)
            
            print(f"  Clicking download and waiting for file...")
            # Start waiting for download before clicking
            with page.expect_download(timeout=60000) as download_info:
                download_button.click()
            
            download = download_info.value
            
            print(f"  Saving to {output_file}...")
            download.save_as(output_file)
            print(f"  Successfully updated {output_path}!")
            return True
            
        except Exception as e:
            print(f"  ERROR: Failed to download NASDAQ screener CSV: {e}")
            return False
            
        finally:
            context.close()
            browser.close()

if __name__ == "__main__":
    download_screener_csv()
