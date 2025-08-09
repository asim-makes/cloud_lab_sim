import os
import sys
import subprocess
import logging
import argparse
from pathlib import Path
from datetime import datetime, time
from typing import Optional, List
from ast import literal_eval

from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


# Load environment variables
load_dotenv()

# Constants
WEEKEND_DAYS = literal_eval(os.environ.get("WEEKEND_DAYS", "{4, 5}"))
DATE_FORMAT = os.environ.get("DATE_FORMAT", "%Y-%m-%d")
TIMEOUT = int(os.environ.get("TIMEOUT", 60))

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_SAVED_DIR = Path(PROJECT_ROOT / "todays_price")

NEPSE_URL = os.environ.get("NEPSE_URL", "https://www.nepalstock.com/today-price")
CHROME_PREFS = literal_eval(os.environ.get("CHROME_PREFS", "{}"))
CHROME_PREFS['download.default_directory'] = str(RAW_SAVED_DIR)

# Ensure the directory exists
RAW_SAVED_DIR.mkdir(parents=True, exist_ok=True)


# Arguments
parser = argparse.ArgumentParser(description="Download todays stock price date")

parser.add_argument(
    "--log",
    action="store_true",
    help="Enable logging to file. By default, it logs to console if MTA is set up."
)

args = parser.parse_args()

if args.log:
    logging.basicConfig(
        stream=sys.stdout,
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s -%(message)s"
    )
else:
    logging.basicConfig(level=logging.CRITICAL + 1)

class DownloadFile:
    """Basic utilities needed by class"""

    def kill_chromedriver(self):
        """Kill all chromedriver processes"""
        try:
            # Use pkill command which is more reliable, suppress output
            result = subprocess.run(['pkill', '-f', 'chromedriver'], 
                                capture_output=True, text=True, check=False)
            if result.returncode == 0:
                logging.info("[✔️] Cleaned up chromedriver processes")
            # Don't print anything if no processes found (returncode = 1) - that's normal
        except Exception:
            # Silently handle any errors - process cleanup isn't critical
            pass

    def wait_for_download_complete(self, download_dir, initial_files, timeout=60):

        """Wait for new files to appear and complete downloading"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            current_files = set(Path(download_dir).glob("*"))
            new_files = current_files - initial_files
            
            # Check for new CSV files
            new_csv_files = [f for f in new_files if f.suffix.lower() == '.csv']
            
            # Check if there are any .crdownload files (incomplete downloads)
            crdownload_files = list(Path(download_dir).glob("*.crdownload"))
            
            if new_csv_files and not crdownload_files:
                return new_csv_files[0]
            elif crdownload_files:
                logging.info(f"[⏳] Download in progress...")
            
            time.sleep(1)
        
        return None

    def setup_browser(self):
        # === Set up Chrome options ===
        chrome_options = Options()
        
        # FIX: Use these options that work better for downloads
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-plugins")
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--allow-running-insecure-content")
        
        # FIX: For headless mode, add these specific options
        # Uncomment the next 3 lines if you want to try headless mode
        # chrome_options.add_argument("--headless=new")
        # chrome_options.add_argument("--window-size=1920,1080")
        # chrome_options.add_argument("--disable-blink-features=AutomationControlled")

        # Ensure the download directory is absolute path
        # download_dir = os.path.abspath(RAW_SAVED_DIR)
        # # downwload_dir = RAW_SAVED_DIR # Use this

        chrome_options.add_experimental_option("prefs", CHROME_PREFS)

        # FIX: Add this to avoid detection as automated browser
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)

        return webdriver.Chrome(options=chrome_options)

    def download_todays_price(self):

        driver = self.setup_browser()

        # Avoid Detection
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        initial_files = set(RAW_SAVED_DIR.glob("*"))
        download_dir = str(RAW_SAVED_DIR)
        
        try:
            logging.info("Driver started successfully")
            logging.info(f"Download directory: {download_dir}")
            logging.info("Starting the process....")
        
            logging.info("[*] Opening NEPSE 'Today's Price' page...")
            driver.get(NEPSE_URL)
            
            # Wait for page to load completely
            time.sleep(5)
        
            wait = WebDriverWait(driver, 30)
            
            # FIX: More comprehensive selectors
            download_selectors = [
                "//a[contains(@class,'table__file') and contains(text(),'Download as CSV')]",
                "//a[contains(text(),'Download as CSV')]",
                "//a[contains(text(),'CSV')]",
                "//a[@class='table__file']",
                "//button[contains(text(),'Download as CSV')]",
                "//*[contains(text(),'Download') and contains(text(),'CSV')]"
            ]
            
            download_link = None
            for i, selector in enumerate(download_selectors):
                try:
                    logging.info(f"[*] Trying selector {i+1}: {selector}")
                    download_link = wait.until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    logging.info(f"[✅] Found download link with selector {i+1}")
                    break
                except Exception as e:
                    logging.error(f"[❌] Selector {i+1} failed: {str(e)[:100]}...", exc_info=True)
                    if i < len(download_selectors) - 1:
                        continue
            
            # Workaround 1: Uncomment this line if download link is not found.
            # if not download_link:
            #     # FIX: Try to find any download link by inspecting the page
            #     try:
            #         all_links = driver.find_elements(By.TAG_NAME, "a")
            #         for link in all_links:
            #             link_text = link.text.lower()
            #             href = link.get_attribute("href") or ""
            #             if ("download" in link_text and "csv" in link_text) or "csv" in href.lower():
            #                 download_link = link
            #                 print(f"[✅] Found download link by text search: {link.text}")
            #                 break
            #     except:
            #         pass
            # print("[❌] Could not find download link with #1. Uncomment Workaround 2")
            
            # # Workaround 2: Uncomment this line if workaround 1 fails..
            # if not download_link:
            #     links = driver.find_elements(By.TAG_NAME, "a")
            #     for link in links[:10]:  # Show first 10 links
            #         print(f"  - {link.text[:50]} | href: {(link.get_attribute('href') or '')[:50]}")
            #     raise Exception("Could not find download link")
            # print("[❌] Could not find download link with #1. Manually download the file.")
        
            logging.info("[*] Clicking Download as CSV link...")
            
            # Scroll to element
            driver.execute_script("arguments[0].scrollIntoView(true);", download_link)
            time.sleep(2)
            
            # Try multiple click methods
            try:
                download_link.click()
            except Exception as e1:
                logging.warning(f"[⚠️] Regular click failed: {e1}")
                logging.info("Try to uncomment workaround 3.")
                # Workaround 3: Uncomment this line if clicking download link fails.
                # try:
                #     driver.execute_script("arguments[0].click();", download_link)
                # except Exception as e2:
                #     print(f"[⚠️] JavaScript click failed: {e2}")
                #     # Last resort - try ActionChains
                #     from selenium.webdriver.common.action_chains import ActionChains
                #     ActionChains(driver).move_to_element(download_link).click().perform()
        
            logging.info("[*] Waiting for download to finish...")
            
            # FIX: Use the improved download detection
            downloaded_file = self.wait_for_download_complete(download_dir, initial_files, TIMEOUT)
            
            if downloaded_file:
                logging.info(f"[✅] CSV downloaded: {downloaded_file.name}")
                logging.info(f"[📁] File location: {downloaded_file.absolute()}")
            else:
                logging.error("❌ Download failed or timed out.")
                # List all files for debugging
                all_files = list(Path(download_dir).glob("*"))
                logging.info(f"Files in download directory: {[f.name for f in all_files]}")
        
        except Exception as e:
            logging.info(f"[❌] Error occurred: {e}", exc_info=True)
            import traceback
            traceback.print_exc()
            
        finally:
            # FIX: Improved cleanup with suppressed error output
            if driver:
                try:
                    logging.info("[*] Closing browser...")
                    # Suppress the ugly selenium termination errors
                    import sys
                    import contextlib
                    
                    # Redirect stderr to suppress selenium's ugly error messages
                    with open(os.devnull, 'w') as devnull:
                        with contextlib.redirect_stderr(devnull):
                            driver.quit()
                    logging.info("[✅] Browser closed successfully")
                except Exception as e:
                    # Only show our own clean error message
                    logging.warning(f"[⚠️] Browser cleanup completed (some background processes may persist)", exc_info=True)
                    
            # Always kill chromedriver processes as cleanup
            time.sleep(2)
            self.kill_chromedriver()

        return downloaded_file


class PriceFileManager:
    """Handles file operations for price data"""
    
    def __init__(self, raw_dir: Path):
        self.raw_dir = raw_dir

    def is_file_modified_today(file_path: Path) -> bool:
        modified_time = datetime.fromtimestamp(file_path.stat().st_mtime)
        return modified_time.date() == datetime.today().date()

    def is_file_from_today(file_path: Path) -> bool:
        date_str = file_path.stem.split(" - ")[-1]
        file_creation_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        return file_creation_date == datetime.today().date()
    
    def get_file_by_date(self, date_str: str, file_type: str = "raw") -> Optional[Path]:
        """Get file by date string. file_type can be 'raw' or 'cleaned'"""
        suffix = ""
        filename = f"Today's Price - {date_str}{suffix}.csv"
        
        filepath = self.raw_dir / filename
        
        return filepath if filepath.is_file() else None
    
    def get_todays_files(self) -> List[Path]:
        """Get all files modified today from raw directory"""
        temp_save_dir = {f for f in self.raw_dir.glob("*.csv")}
        existing_files = sorted(temp_save_dir)
        return [f for f in existing_files if self.is_file_from_today(f)]
    
    def file_exists_for_date(self, date_str: str, file_type: str = "raw") -> bool:
        """Check if file exists for given date"""
        return self.get_file_by_date(date_str, file_type) is not None


class MarketChecker:
    """Handles market-related checks"""
    
    @staticmethod
    def is_weekend() -> bool:
        """Check if today is weekend (Fri/Sat/Sun for Nepal market)"""
        return datetime.today().weekday() in WEEKEND_DAYS
    
    @staticmethod
    def get_today_date_str() -> str:
        """Get today's date as string in YYYY-MM-DD format"""
        return datetime.today().strftime(DATE_FORMAT)


class PriceDataApp:
    """Main application class"""
    
    def __init__(self):
        self.file_manager = PriceFileManager(RAW_SAVED_DIR)
        self.market_checker = MarketChecker()
        self.download_file = DownloadFile()
    
    def download_todays_data(self) -> bool:
        """Handle downloading today's data"""
        if self.market_checker.is_weekend():
            logging.info("📅 Weekend detected - market closed, skipping download")
            return True
        
        # Check if file already exists today
        todays_files = self.file_manager.get_todays_files()
        
        if todays_files:
            raw_file = todays_files[0]
            logging.info(f"✅ File already downloaded today: {raw_file.name}")
            return True
        
        # Download new file
        logging.info("📥 No file found for today. Starting download...")
        raw_file = self.download_filedownload_todays_price()
        
        if raw_file and self.file_manager.is_file_modified_today(raw_file):
            logging.info("✅ Successfully downloaded:", raw_file.name)
            return True
        else:
            logging.error("❌ Failed to download today's price file.")
            return False
    
    def run(self) -> None:
        try:
            success = self.download_todays_data()

            if success:
                logging.info("Task completed successfully")
            else:
                logging.error("Something went wrong. Please check log")
                

        except Exception as e:
            logging.error("An unexpected error occured!", exc_info=True)



app = PriceDataApp()
app.run()