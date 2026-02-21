from playwright.async_api import Page
import hashlib
from typing import List, Dict, Optional
from datetime import datetime
import logging
import base64

logger = logging.getLogger(__name__)


class StoryScraper:
    """Scrape Instagram stories from society accounts."""
    
    def __init__(self, browser):
        self.browser = browser
    
    async def scrape_stories(self, username: str) -> List[Dict]:
        """
        Scrape all stories from a user's profile.
        
        Args:
            username: Instagram username to scrape
            
        Returns:
            List of story dictionaries with text, location, timestamp, etc.
        """
        stories = []
        page = self.browser.page
        
        try:
            logger.info(f"Scraping stories for @{username}")
            
            # Navigate to profile
            await page.goto(f"https://www.instagram.com/{username}/", wait_until="networkidle")
            await self.browser.random_delay(2000, 3000)
            
            # Check for story ring (indicates active stories)
            story_ring = await page.query_selector('canvas[aria-label*="story"]')
            if not story_ring:
                logger.info(f"No active stories for @{username}")
                return stories
            
            # Click on story ring to open stories
            await story_ring.click()
            await page.wait_for_selector('[role="dialog"]', timeout=5000)
            await self.browser.random_delay(1000, 2000)
            
            # Extract all stories in sequence
            story_count = 0
            max_stories = 50  # Safety limit
            
            while story_count < max_stories:
                story_data = await self._extract_story_content(page)
                
                if story_data:
                    stories.append(story_data)
                    story_count += 1
                    logger.info(f"Extracted story {story_count} from @{username}")
                
                # Check if there's a next story
                next_button = await page.query_selector('button[aria-label="Next"]')
                if not next_button:
                    logger.info(f"No more stories for @{username}")
                    break
                
                # Click next
                await next_button.click()
                await self.browser.random_delay(1000, 2000)
            
            logger.info(f"Scraped {len(stories)} stories from @{username}")
            
        except Exception as e:
            logger.error(f"Error scraping stories for @{username}: {e}")
        
        return stories
    
    async def _extract_story_content(self, page: Page) -> Optional[Dict]:
        """Extract content from current story."""
        try:
            # Extract all text elements
            text_elements = await page.query_selector_all('[dir="auto"]')
            texts = []
            
            for element in text_elements:
                try:
                    text = await element.inner_text()
                    if text and text.strip():
                        texts.append(text.strip())
                except:
                    continue
            
            # Extract location sticker if present
            location = None
            try:
                location_element = await page.query_selector('[aria-label*="location"]')
                if location_element:
                    location = await location_element.inner_text()
            except:
                pass
            
            # Extract time posted (if available)
            story_timestamp = None
            try:
                time_element = await page.query_selector('time')
                if time_element:
                    datetime_attr = await time_element.get_attribute('datetime')
                    if datetime_attr:
                        story_timestamp = datetime.fromisoformat(datetime_attr.replace('Z', '+00:00'))
            except:
                pass
            
            # Take screenshot
            screenshot_bytes = None
            try:
                screenshot_bytes = await page.screenshot(full_page=False)
            except Exception as e:
                logger.warning(f"Failed to capture screenshot: {e}")
            
            # Combine all text
            combined_text = " ".join(texts)
            
            # Create content hash for deduplication
            content_hash = hashlib.sha256(combined_text.encode()).hexdigest()
            
            # Only return if there's actual content
            if not combined_text and not location:
                return None
            
            return {
                'text': combined_text,
                'location': location,
                'timestamp': story_timestamp or datetime.now(),
                'content_hash': content_hash,
                'screenshot': base64.b64encode(screenshot_bytes).decode() if screenshot_bytes else None,
                'detected_at': datetime.now()
            }
            
        except Exception as e:
            logger.error(f"Error extracting story content: {e}")
            return None
    
    async def check_has_stories(self, username: str) -> bool:
        """
        Quick check if user has active stories without opening them.
        
        Args:
            username: Instagram username
            
        Returns:
            True if user has active stories
        """
        try:
            page = self.browser.page
            await page.goto(f"https://www.instagram.com/{username}/", wait_until="networkidle")
            await self.browser.random_delay(1000, 2000)
            
            story_ring = await page.query_selector('canvas[aria-label*="story"]')
            return story_ring is not None
            
        except Exception as e:
            logger.error(f"Error checking stories for @{username}: {e}")
            return False

# Made with Bob
