"""
Instagram scraper for FreeFoodUCD
Combines browser management, authentication, and content scraping
"""
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
import random
import asyncio
from typing import List, Dict, Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class InstagramScraper:
    """Unified Instagram scraper with browser management and authentication."""
    
    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.is_logged_in = False
        
        # Rotating user agents
        self.user_agents = [
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        ]
    
    async def initialize(self):
        """Initialize browser with anti-detection measures."""
        logger.info("Initializing Instagram scraper...")
        
        self.playwright = await async_playwright().start()
        
        # Launch browser
        self.browser = await self.playwright.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
            ]
        )
        
        # Create context
        self.context = await self.browser.new_context(
            user_agent=random.choice(self.user_agents),
            viewport={'width': 1920, 'height': 1080},
            locale='en-GB',
            timezone_id='Europe/Dublin',
        )
        
        # Anti-detection
        await self.context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)
        
        self.page = await self.context.new_page()
        logger.info("Browser initialized")
    
    async def login(self) -> bool:
        """Login to Instagram."""
        try:
            logger.info(f"Logging in as {self.username}")
            
            # Go to Instagram homepage first
            await self.page.goto("https://www.instagram.com/", wait_until="domcontentloaded")
            await self.random_delay(2000, 3000)
            
            # Try multiple selectors for username field
            username_selectors = [
                'input[name="username"]',
                'input[aria-label="Phone number, username, or email"]',
                'input[type="text"]'
            ]
            
            username_filled = False
            for selector in username_selectors:
                try:
                    await self.page.wait_for_selector(selector, timeout=5000)
                    await self.page.fill(selector, self.username)
                    username_filled = True
                    logger.info(f"Username filled with selector: {selector}")
                    break
                except Exception as e:
                    logger.debug(f"Selector {selector} failed: {e}")
                    continue
            
            if not username_filled:
                logger.error("Could not find username input field")
                return False
            
            await self.random_delay(500, 1000)
            
            # Try multiple selectors for password field
            password_selectors = [
                'input[name="password"]',
                'input[aria-label="Password"]',
                'input[type="password"]'
            ]
            
            password_filled = False
            for selector in password_selectors:
                try:
                    await self.page.fill(selector, self.password)
                    password_filled = True
                    logger.info(f"Password filled with selector: {selector}")
                    break
                except Exception as e:
                    logger.debug(f"Selector {selector} failed: {e}")
                    continue
            
            if not password_filled:
                logger.error("Could not find password input field")
                return False
            
            await self.random_delay(500, 1000)
            
            # Click login button
            login_selectors = [
                'button[type="submit"]',
                'button:has-text("Log in")',
                'button:has-text("Log In")'
            ]
            
            login_clicked = False
            for selector in login_selectors:
                try:
                    await self.page.click(selector)
                    login_clicked = True
                    logger.info(f"Login button clicked with selector: {selector}")
                    break
                except Exception as e:
                    logger.debug(f"Selector {selector} failed: {e}")
                    continue
            
            if not login_clicked:
                logger.error("Could not find login button")
                return False
            
            # Wait for navigation
            await self.page.wait_for_timeout(5000)
            
            # Check if login was successful by looking for profile icon or feed
            try:
                await self.page.wait_for_selector('svg[aria-label="Home"]', timeout=10000)
                logger.info("Login successful - found home icon")
            except:
                logger.warning("Could not verify login success, but continuing...")
            
            # Handle "Save Your Login Info" popup
            try:
                await self.page.click('button:has-text("Not Now")', timeout=3000)
                await self.random_delay(1000, 2000)
            except:
                pass
            
            # Handle "Turn on Notifications" popup
            try:
                await self.page.click('button:has-text("Not Now")', timeout=3000)
                await self.random_delay(1000, 2000)
            except:
                pass
            
            self.is_logged_in = True
            logger.info("Login process completed")
            return True
            
        except Exception as e:
            logger.error(f"Login failed: {e}")
            return False
    
    async def scrape_posts(self, username: str, max_posts: int = 3) -> List[Dict]:
        """
        Scrape recent posts from a user's profile.
        
        Args:
            username: Instagram username
            max_posts: Maximum number of posts to scrape (default: 3 for low volume)
            
        Returns:
            List of post dictionaries
        """
        posts = []
        
        try:
            logger.info(f"Scraping posts for @{username}")
            
            # Navigate to profile
            await self.page.goto(f"https://www.instagram.com/{username}/", wait_until="networkidle")
            await self.random_delay(2000, 3000)
            
            # Get post links
            post_links = await self.page.query_selector_all('article a[href*="/p/"]')
            
            if not post_links:
                logger.info(f"No posts found for @{username}")
                return posts
            
            # Limit to max_posts
            post_links = post_links[:max_posts]
            logger.info(f"Found {len(post_links)} posts for @{username}")
            
            # Extract each post
            for i, link in enumerate(post_links):
                try:
                    post_url = await link.get_attribute('href')
                    if not post_url:
                        continue
                    
                    if not post_url.startswith('http'):
                        post_url = f"https://www.instagram.com{post_url}"
                    
                    post_id = post_url.split('/p/')[-1].split('/')[0]
                    
                    # Navigate to post
                    await self.page.goto(post_url, wait_until="networkidle")
                    await self.random_delay(1000, 2000)
                    
                    # Extract post data
                    post_data = await self._extract_post_content(post_id, post_url)
                    
                    if post_data:
                        posts.append(post_data)
                        logger.info(f"Extracted post {i+1}/{len(post_links)}")
                    
                    # Go back
                    await self.page.go_back(wait_until="networkidle")
                    await self.random_delay(1000, 2000)
                    
                except Exception as e:
                    logger.error(f"Error extracting post {i+1}: {e}")
                    continue
            
            logger.info(f"Scraped {len(posts)} posts from @{username}")
            
        except Exception as e:
            logger.error(f"Error scraping posts for @{username}: {e}")
        
        return posts
    
    async def _extract_post_content(self, post_id: str, post_url: str) -> Optional[Dict]:
        """Extract content from a single post."""
        try:
            # Extract caption
            caption = ""
            try:
                caption_element = await self.page.query_selector('h1')
                if caption_element:
                    caption = await caption_element.inner_text()
            except:
                pass
            
            # Extract image URL for OCR
            image_url = None
            try:
                img_element = await self.page.query_selector('article img')
                if img_element:
                    image_url = await img_element.get_attribute('src')
            except:
                pass
            
            # Extract timestamp
            timestamp = datetime.now()
            try:
                time_element = await self.page.query_selector('time')
                if time_element:
                    datetime_str = await time_element.get_attribute('datetime')
                    if datetime_str:
                        timestamp = datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
            except:
                pass
            
            return {
                'post_id': post_id,
                'source_url': post_url,
                'caption': caption,
                'image_url': image_url,
                'timestamp': timestamp,
                'scraped_at': datetime.now()
            }
            
        except Exception as e:
            logger.error(f"Error extracting post content: {e}")
            return None
    
    async def random_delay(self, min_ms: int = 1000, max_ms: int = 3000):
        """Add random delay to mimic human behavior."""
        delay = random.uniform(min_ms / 1000, max_ms / 1000)
        await asyncio.sleep(delay)
    
    async def close(self):
        """Close browser and cleanup."""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        logger.info("Browser closed")


# Made with Bob