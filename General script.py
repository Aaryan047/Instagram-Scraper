import time
import random
import csv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.options import Options

# Configuration
MAX_REELS = 50
INSTAGRAM_USERNAME = "your_username_here"  # Replace with your Instagram username
INSTAGRAM_PASSWORD = "your_password_here"  # Replace with your Instagram password

# Global tracking set (only need to track URLs now)
processed_urls = set()

# Browser setup with better options
def setup_driver():
    """Setup Chrome driver with stealth options"""
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    # Optional: Run in headless mode (uncomment if needed)
    # chrome_options.add_argument("--headless")
    
    driver = webdriver.Chrome(options=chrome_options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver

# Initialize driver and wait
driver = setup_driver()
wait = WebDriverWait(driver, 15)

def save_data(reels_data):
    """Save collected data to CSV"""
    try:
        output_file = 'reels_data.csv'
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            if reels_data:
                writer = csv.DictWriter(f, fieldnames=reels_data[0].keys())
                writer.writeheader()
                writer.writerows(reels_data)
        print(f"Data saved: {len(reels_data)} reels to {output_file}")
    except Exception as e:
        print(f"Error saving data: {e}")

def extract_engagement_number(text):
    """Extract numeric value from engagement text"""
    if not text:
        return "0"
    
    # Clean the text and extract numbers
    import re
    # Find patterns like "1.2K", "500", "1,234", "2.3M"
    match = re.search(r'([\d,]+\.?\d*[KMB]?)', text.replace(' ', ''))
    if match:
        return match.group(1)
    return "0"

def extract_hashtags(text):
    """Extract hashtags from text"""
    if not text:
        return ""
    
    import re
    hashtags = re.findall(r'#\w+', text)
    return ",".join(hashtags) if hashtags else ""

def get_current_reel_data():
    """Extract data from currently displayed reel"""
    try:
        print("Extracting reel data...")
        
        # Wait for content to load
        time.sleep(random.uniform(2, 4))
        
        # Get current URL
        current_url = driver.current_url
        
        # Initialize data structure - focusing on link, likes, and hashtags only
        reel_data = {
            "link": current_url,
            "likes": "0",
            "hashtags": ""
        }
        
        # Extract caption to get hashtags from it
        caption_text = ""
        caption_selectors = [
            "div[data-testid='post-content'] span",
            "span[dir='auto']",
            "div[role='button'] span",
            "span:not([class*='icon']):not([aria-label])",
        ]
        
        for selector in caption_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    text = element.text.strip()
                    if text and len(text) > 10 and not text.isdigit():
                        caption_text = text
                        print(f"Caption found for hashtag extraction: {text[:50]}...")
                        break
                if caption_text:
                    break
            except:
                continue
        
        # Extract hashtags from caption
        if caption_text:
            reel_data["hashtags"] = extract_hashtags(caption_text)
            if reel_data["hashtags"]:
                print(f"Hashtags extracted from caption: {reel_data['hashtags']}")
        
        # Try to find additional hashtags in comments or description sections if none found
        if not reel_data["hashtags"]:
            try:
                # Look for hashtags in various parts of the page
                hashtag_selectors = [
                    "div[data-testid='post-content']",
                    "span[dir='auto']",
                    "div[role='button']",
                    "article span"
                ]
                
                for selector in hashtag_selectors:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        text = element.text.strip()
                        hashtags = extract_hashtags(text)
                        if hashtags and not reel_data["hashtags"]:
                            reel_data["hashtags"] = hashtags
                            print(f"Additional hashtags found: {hashtags}")
                            break
                    if reel_data["hashtags"]:
                        break
            except:
                pass
        
        # Extract likes only (focusing on the specific metric we need)
        likes_selectors = [
            "span[aria-label*='like']",
            "button[aria-label*='like'] span",
            "div[role='button'][aria-label*='like']",
            "span:contains('like')"
        ]
        
        for selector in likes_selectors:
            try:
                if ':contains(' in selector:
                    # Use XPath for text content matching
                    xpath_selector = f"//span[contains(text(), 'like')]"
                    elements = driver.find_elements(By.XPATH, xpath_selector)
                else:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                
                for element in elements:
                    text = element.get_attribute('aria-label') or element.text
                    if text and any(char.isdigit() for char in text):
                        number = extract_engagement_number(text)
                        if number != "0":
                            reel_data["likes"] = number
                            print(f"Likes found: {number}")
                            break
                
                if reel_data["likes"] != "0":
                    break
            except:
                continue
        
        # Fallback: Try to find likes if not found above
        if reel_data["likes"] == "0":
            try:
                # Look for any spans with numbers that might be likes
                number_elements = driver.find_elements(By.XPATH, "//span[text()[contains(., ',') or contains(., 'K') or contains(., 'M')] and string-length(text()) < 10]")
                
                found_numbers = []
                for elem in number_elements:
                    text = elem.text.strip()
                    if text and any(char.isdigit() for char in text):
                        found_numbers.append(text)
                
                # Try to identify which number might be likes (usually the first or second number)
                if len(found_numbers) >= 1:
                    # First number is often likes or views - let's assume it's likes for now
                    reel_data["likes"] = found_numbers[0]
                    print(f"Fallback likes found: {found_numbers[0]}")
                    
            except:
                pass
        
        return reel_data
        
    except Exception as e:
        print(f"Error extracting reel data: {e}")
        return None

def open_fresh_reels_tab():
    """Open a new tab and navigate to reels page"""
    try:
        print("Opening fresh reels tab...")
        
        # Open new tab
        driver.execute_script("window.open('');")
        
        # Switch to the new tab (always the last one)
        all_handles = driver.window_handles
        driver.switch_to.window(all_handles[-1])
        
        # Navigate to reels with random variation
        urls = [
            "https://www.instagram.com/reels/",
            "https://www.instagram.com/explore/reels/",
        ]
        
        url = random.choice(urls)
        driver.get(url)
        
        # Wait for page to load with better detection
        time.sleep(random.uniform(4, 7))
        
        # Check if page loaded properly
        try:
            # Wait for either video elements or clickable reels
            WebDriverWait(driver, 10).until(
                lambda d: d.find_elements(By.TAG_NAME, "video") or 
                         d.find_elements(By.CSS_SELECTOR, "article") or
                         d.find_elements(By.CSS_SELECTOR, "a[href*='/reel/']")
            )
            print("Fresh reels page loaded successfully")
            return True
        except TimeoutException:
            print("Page load timeout, but continuing...")
            return True
            
    except Exception as e:
        print(f"Failed to open fresh reels tab: {e}")
        return False

def close_current_tab():
    """Close current tab and switch back to main tab"""
    try:
        all_handles = driver.window_handles
        if len(all_handles) > 1:
            driver.close()
            # Switch to the first tab (main tab)
            driver.switch_to.window(all_handles[0])
            print("Tab closed, switched to main tab")
        else:
            print("Only one tab remaining")
    except Exception as e:
        print(f"Error closing tab: {e}")

def click_random_reel():
    """Click on a random reel on the current page"""
    try:
        print("Looking for reels to click...")
        
        # Wait for page content
        time.sleep(random.uniform(2, 4))
        
        # Try multiple strategies to find reels
        selectors = [
            "a[href*='/reel/']",           # Direct reel links
            "article",                     # Instagram article containers
            "div[role='button']",          # Clickable divs
            "video",                       # Video elements
        ]
        
        clickable_elements = []
        
        for selector in selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                clickable_elements.extend(elements[:5])  # Take first 5 of each type
                if len(clickable_elements) >= 3:  # Stop if we have enough options
                    break
            except:
                continue
        
        if not clickable_elements:
            print("No clickable reel elements found")
            return False
        
        # Filter out elements that are too small or hidden
        valid_elements = []
        for elem in clickable_elements:
            try:
                if elem.is_displayed() and elem.size['height'] > 50 and elem.size['width'] > 50:
                    valid_elements.append(elem)
            except:
                pass
        
        if not valid_elements:
            valid_elements = clickable_elements  # Fallback to all elements
        
        # Click on a random element
        random_element = random.choice(valid_elements)
        
        # Scroll element into view first
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", random_element)
        time.sleep(1)
        
        # Try clicking with JavaScript (more reliable)
        driver.execute_script("arguments[0].click();", random_element)
        
        # Wait for reel to load
        time.sleep(random.uniform(3, 6))
        
        print("Successfully clicked on reel")
        return True
        
    except Exception as e:
        print(f"Error clicking reel: {e}")
        return False

def navigate_to_variety_page():
    """Navigate to different Instagram sections for content variety"""
    try:
        variety_urls = [
            "https://www.instagram.com/reels/",
            "https://www.instagram.com/explore/reels/",
            "https://www.instagram.com/explore/",
        ]
        
        # Add hashtag exploration occasionally
        if random.random() < 0.4:  # 40% chance
            hashtags = ["viral", "trending", "funny", "music", "dance", "food", "travel", "fashion"]
            hashtag = random.choice(hashtags)
            variety_urls.append(f"https://www.instagram.com/explore/tags/{hashtag}/")
        
        url = random.choice(variety_urls)
        print(f"Navigating to: {url}")
        
        driver.get(url)
        time.sleep(random.uniform(4, 8))
        
        return True
        
    except Exception as e:
        print(f"Failed to navigate to variety page: {e}")
        return False

def check_for_rate_limit():
    """Check if we've hit rate limits or blocks"""
    try:
        page_source = driver.page_source.lower()
        
        warning_signs = [
            'try again later',
            'temporarily blocked',
            'suspicious activity',
            'rate limit',
            'please wait',
            'challenge_required'
        ]
        
        for sign in warning_signs:
            if sign in page_source:
                print(f"Possible rate limit detected: {sign}")
                return True
        
        # Check current URL for blocks
        current_url = driver.current_url.lower()
        if 'challenge' in current_url or 'suspicious' in current_url:
            print("Redirected to challenge page")
            return True
            
        return False
        
    except:
        return False

def main():
    """Main scraping function"""
    reels_data = []
    failed_attempts = 0
    max_failures = 15
    
    # Validate credentials
    if INSTAGRAM_USERNAME == "your_username_here" or INSTAGRAM_PASSWORD == "your_password_here":
        print("ERROR: Please set your Instagram credentials!")
        print("Edit the INSTAGRAM_USERNAME and INSTAGRAM_PASSWORD variables at the top of this script")
        return
    
    try:
        print("Logging into Instagram...")
        driver.get("https://www.instagram.com/accounts/login/")
        
        # Better login process
        time.sleep(random.uniform(3, 5))
        
        # Find and fill username
        username_field = wait.until(EC.element_to_be_clickable((By.NAME, "username")))
        username_field.clear()
        
        # Human-like typing with random delays
        for char in INSTAGRAM_USERNAME:
            username_field.send_keys(char)
            time.sleep(random.uniform(0.05, 0.2))
        
        time.sleep(random.uniform(0.5, 1.5))
        
        # Find and fill password
        password_field = driver.find_element(By.NAME, "password")
        for char in INSTAGRAM_PASSWORD:
            password_field.send_keys(char)
            time.sleep(random.uniform(0.05, 0.2))
        
        # Submit login
        password_field.send_keys(Keys.ENTER)
        
        # Wait for login and handle popups
        time.sleep(random.uniform(8, 12))
        
        # Handle common popups
        popup_buttons = [
            "Not Now", "Not now", "Maybe Later", "Skip", 
            "Cancel", "Save Info", "Turn On Notifications"
        ]
        
        for _ in range(3):  # Try up to 3 popup dismissals
            popup_dismissed = False
            for button_text in popup_buttons:
                try:
                    popup = WebDriverWait(driver, 3).until(
                        EC.element_to_be_clickable((By.XPATH, f"//button[contains(text(),'{button_text}')]"))
                    )
                    popup.click()
                    time.sleep(2)
                    popup_dismissed = True
                    print(f"   Dismissed popup: {button_text}")
                    break
                except TimeoutException:
                    continue
            
            if not popup_dismissed:
                break
        
        print("Login completed successfully")
        
        # Start scraping
        print(f"\nStarting to scrape {MAX_REELS} reels...")
        
        for i in range(MAX_REELS):
            print(f"\n{'='*60}")
            print(f"Processing reel {i+1}/{MAX_REELS}")
            print(f"Successfully collected: {len(reels_data)} reels")
            print(f"Failed attempts: {failed_attempts}/{max_failures}")
            
            # Check for rate limiting every 10 iterations
            if i % 10 == 0 and i > 0:
                if check_for_rate_limit():
                    print("Rate limiting detected, taking extended break...")
                    time.sleep(random.uniform(120, 300))  # 2-5 minute break
            
            # Open fresh tab
            if not open_fresh_reels_tab():
                failed_attempts += 1
                continue
            
            # Navigate to variety page occasionally
            if i % 7 == 0 and i > 0:  # Every 7th iteration
                navigate_to_variety_page()
            
            # Random delay
            time.sleep(random.uniform(2, 5))
            
            # Click on a reel
            if not click_random_reel():
                failed_attempts += 1
                close_current_tab()
                continue
            
            # Extract data
            reel_data = get_current_reel_data()
            
            if reel_data and (reel_data.get("hashtags") or reel_data.get("likes") != "0"):
                # Check for duplicates based on URL only
                if reel_data["link"] not in processed_urls:
                    
                    reels_data.append(reel_data)
                    processed_urls.add(reel_data["link"])
                    
                    print("SUCCESS - Reel data collected:")
                    print(f"   URL: {reel_data['link']}")
                    print(f"   Hashtags: {reel_data['hashtags']}")
                    print(f"   Likes: {reel_data['likes']}")
                    
                    failed_attempts = 0
                    
                    # Save progress periodically
                    if len(reels_data) % 5 == 0:
                        save_data(reels_data)
                        print(f"Progress saved ({len(reels_data)} reels)")
                        
                else:
                    print("Duplicate URL detected, skipping...")
            else:
                failed_attempts += 1
                print(f"FAILED to extract meaningful data (no hashtags or likes found)")
                
                if failed_attempts >= max_failures:
                    print("Too many consecutive failures, stopping...")
                    break
            
            # Close current tab
            close_current_tab()
            
            # Human-like delay
            delay = random.uniform(8, 15)
            print(f"Waiting {delay:.1f}s before next reel...")
            time.sleep(delay)
        
        print(f"\nScraping completed!")
        print(f"Total reels collected: {len(reels_data)}")
        
        if reels_data:
            save_data(reels_data)
            print("Final data saved to reels_data.csv")

    except KeyboardInterrupt:
        print("\nScraping interrupted by user")
        if reels_data:
            save_data(reels_data)
            print("Data saved before exit")
    
    except Exception as e:
        print(f"Critical error: {e}")
        import traceback
        traceback.print_exc()
        if reels_data:
            save_data(reels_data)

    finally:
        print("Closing browser...")
        try:
            driver.quit()
        except:
            pass

if __name__ == "__main__":
    main()