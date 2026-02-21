from playwright.async_api import Page
from typing import List, Dict, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class PostScraper:
    """Scrape Instagram feed posts from society accounts."""
    
    def __init__(self, browser):
        self.browser = browser
    
    async def scrape_recent_posts(self, username: str, max_posts: int = 12) -> List[Dict]:
        """
        Scrape recent posts from a user's profile.
        
        Args:
            username: Instagram username to scrape
            max_posts: Maximum number of posts to scrape
            
        Returns:
            List of post dictionaries with caption, media URLs, etc.
        """
        posts = []
        page = self.browser.page
        
        try:
            logger.info(f"Scraping posts for @{username}")
            
            # Navigate to profile
            await page.goto(f"https://www.instagram.com/{username}/", wait_until="networkidle")
            await self.browser.random_delay(2000, 3000)
            
            # Get all post links from grid
            post_links = await page.query_selector_all('article a[href*="/p/"]')
            
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
                    
                    # Make absolute URL
                    if not post_url.startswith('http'):
                        post_url = f"https://www.instagram.com{post_url}"
                    
                    # Extract post ID from URL
                    post_id = post_url.split('/p/')[-1].split('/')[0]
                    
                    # Navigate to post
                    await page.goto(post_url, wait_until="networkidle")
                    await self.browser.random_delay(1000, 2000)
                    
                    # Extract post data
                    post_data = await self._extract_post_content(page, post_id, post_url)
                    
                    if post_data:
                        posts.append(post_data)
                        logger.info(f"Extracted post {i+1}/{len(post_links)} from @{username}")
                    
                    # Go back to profile
                    await page.go_back(wait_until="networkidle")
                    await self.browser.random_delay(1000, 2000)
                    
                except Exception as e:
                    logger.error(f"Error extracting post {i+1}: {e}")
                    continue
            
            logger.info(f"Scraped {len(posts)} posts from @{username}")
            
        except Exception as e:
            logger.error(f"Error scraping posts for @{username}: {e}")
        
        return posts
    
    async def _extract_post_content(self, page: Page, post_id: str, post_url: str) -> Optional[Dict]:
        """Extract content from a single post."""
        try:
            # Extract caption
            caption = ""
            try:
                # Try multiple selectors for caption
                caption_selectors = [
                    'h1',
                    'span[dir="auto"]',
                    'div[data-testid="post-comment-root"]'
                ]
                
                for selector in caption_selectors:
                    caption_element = await page.query_selector(selector)
                    if caption_element:
                        caption = await caption_element.inner_text()
                        if caption:
                            break
            except:
                pass
            
            # Extract media URLs
            media_urls = []
            try:
                # Images
                images = await page.query_selector_all('article img[src*="instagram"]')
                for img in images:
                    src = await img.get_attribute('src')
                    if src and 'instagram' in src:
                        media_urls.append(src)
                
                # Videos
                videos = await page.query_selector_all('article video[src]')
                for video in videos:
                    src = await video.get_attribute('src')
                    if src:
                        media_urls.append(src)
            except:
                pass
            
            # Extract timestamp
            post_timestamp = None
            try:
                time_element = await page.query_selector('time')
                if time_element:
                    datetime_attr = await time_element.get_attribute('datetime')
                    if datetime_attr:
                        post_timestamp = datetime.fromisoformat(datetime_attr.replace('Z', '+00:00'))
            except:
                pass
            
            # Only return if there's a caption or media
            if not caption and not media_urls:
                return None
            
            return {
                'instagram_post_id': post_id,
                'caption': caption,
                'source_url': post_url,
                'media_urls': media_urls,
                'post_timestamp': post_timestamp or datetime.now(),
                'detected_at': datetime.now()
            }
            
        except Exception as e:
            logger.error(f"Error extracting post content: {e}")
            return None
    
    async def get_latest_post_id(self, username: str) -> Optional[str]:
        """
        Get the ID of the most recent post without full scraping.
        Useful for checking if there are new posts.
        
        Args:
            username: Instagram username
            
        Returns:
            Post ID of most recent post, or None
        """
        try:
            page = self.browser.page
            await page.goto(f"https://www.instagram.com/{username}/", wait_until="networkidle")
            await self.browser.random_delay(1000, 2000)
            
            # Get first post link
            first_post = await page.query_selector('article a[href*="/p/"]')
            if not first_post:
                return None
            
            post_url = await first_post.get_attribute('href')
            if not post_url:
                return None
            
            # Extract post ID
            post_id = post_url.split('/p/')[-1].split('/')[0]
            return post_id
            
        except Exception as e:
            logger.error(f"Error getting latest post ID for @{username}: {e}")
            return None

# Made with Bob
