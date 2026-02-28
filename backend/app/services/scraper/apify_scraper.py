"""
Apify-based Instagram scraper.
Uses Apify's Instagram Profile Scraper for reliable data extraction.
"""

from apify_client import ApifyClient
from typing import List, Dict, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ApifyInstagramScraper:
    """
    Instagram scraper using Apify's Instagram Profile Scraper.
    
    Apify Actor: apify/instagram-profile-scraper
    Pricing: ~$0.25 per 1000 posts scraped
    """
    
    def __init__(self, api_token: str):
        """
        Initialize Apify scraper.
        
        Args:
            api_token: Apify API token
        """
        self.client = ApifyClient(api_token)
        self.actor_id = "apify/instagram-profile-scraper"
    
    async def scrape_posts(self, username: str, max_posts: int = 3) -> List[Dict]:
        """
        Scrape recent posts from an Instagram profile.
        
        Args:
            username: Instagram username (without @)
            max_posts: Maximum number of posts to scrape
            
        Returns:
            List of post dictionaries with structure:
            {
                'url': str,
                'caption': str,
                'image_url': str,
                'timestamp': datetime
            }
        """
        try:
            logger.info(f"Starting Apify scrape for @{username}")
            
            # Configure the Actor run
            run_input = {
                "usernames": [username],
                "resultsLimit": max_posts,
                "resultsType": "posts",
                "searchType": "user",
                "addParentData": False
            }
            
            # Run the Actor and wait for it to finish
            logger.info(f"Running Apify actor with input: {run_input}")
            run = self.client.actor(self.actor_id).call(run_input=run_input)
            
            # Log run details
            logger.info(f"Apify run completed. Run ID: {run.get('id')}, Status: {run.get('status')}")
            logger.info(f"Dataset ID: {run.get('defaultDatasetId')}")
            
            # Fetch results from the Actor's dataset
            posts = []
            dataset_items = list(self.client.dataset(run["defaultDatasetId"]).iterate_items())
            logger.info(f"Apify dataset returned {len(dataset_items)} items for @{username}")
            
            for item in dataset_items:
                try:
                    # Debug: Log the raw item structure
                    logger.debug(f"Raw Apify item keys: {item.keys()}")
                    logger.debug(f"Raw Apify item: {item}")
                    
                    # Check if this is a profile object with nested posts
                    if 'latestPosts' in item and isinstance(item['latestPosts'], list):
                        logger.info(f"Found {len(item['latestPosts'])} posts in latestPosts array")
                        for post_item in item['latestPosts'][:max_posts]:
                            post = self._parse_apify_post(post_item)
                            if post:
                                posts.append(post)
                    else:
                        # Try parsing as individual post
                        post = self._parse_apify_post(item)
                        if post:
                            posts.append(post)
                except Exception as e:
                    logger.error(f"Error parsing post: {e}", exc_info=True)
                    continue
            
            logger.info(f"Successfully scraped {len(posts)} posts from @{username}")
            return posts
            
        except Exception as e:
            logger.error(f"Apify scraping failed for @{username}: {e}")
            return []
    
    def _parse_apify_post(self, item: Dict) -> Optional[Dict]:
        """
        Parse Apify post data into our standard format.
        
        Args:
            item: Raw post data from Apify
            
        Returns:
            Parsed post dictionary or None if parsing fails
        """
        try:
            # Extract caption
            caption = item.get('caption', '')

            # Collect all carousel images (cap at 5 to avoid large photo posts)
            image_urls = []
            if item.get('displayUrl'):
                image_urls.append(item['displayUrl'])
            if item.get('images'):
                for img in item['images'][:5]:
                    if img not in image_urls:
                        image_urls.append(img)

            # Extract timestamp
            timestamp = None
            if item.get('timestamp'):
                timestamp = datetime.fromisoformat(item['timestamp'].replace('Z', '+00:00'))

            # Extract post URL
            post_url = item.get('url', '')
            if not post_url and item.get('shortCode'):
                post_url = f"https://www.instagram.com/p/{item['shortCode']}/"

            return {
                'url': post_url,
                'caption': caption,
                'image_url': image_urls[0] if image_urls else None,   # backwards-compat single field
                'image_urls': image_urls,                              # new: full carousel list
                'timestamp': timestamp or datetime.now()
            }
            
        except Exception as e:
            logger.error(f"Error parsing Apify post: {e}")
            return None
    
    async def scrape_posts_batch(self, usernames: List[str], max_posts_per_user: int = 3) -> Dict[str, List[Dict]]:
        """
        Scrape recent posts for multiple profiles in a single Apify actor run.

        Much more efficient than calling scrape_posts() N times — one run startup
        cost instead of N.

        Args:
            usernames: List of Instagram usernames (without @)
            max_posts_per_user: Max posts to collect per profile

        Returns:
            Dict mapping username (lowercase) -> list of post dicts
        """
        if not usernames:
            return {}

        try:
            logger.info(f"Starting batch Apify scrape for {len(usernames)} handles")

            run_input = {
                "usernames": usernames,
                "resultsLimit": max_posts_per_user,
                "resultsType": "posts",
                "searchType": "user",
                "addParentData": False,
            }

            run = self.client.actor(self.actor_id).call(run_input=run_input)
            logger.info(f"Batch run completed. ID: {run.get('id')}, status: {run.get('status')}")

            results: Dict[str, List[Dict]] = {}

            for item in self.client.dataset(run["defaultDatasetId"]).iterate_items():
                try:
                    if "latestPosts" in item and isinstance(item["latestPosts"], list):
                        # Profile-level item — username is on the item itself
                        uname = (item.get("username") or "").lower()
                        if not uname:
                            continue
                        posts = []
                        for post_item in item["latestPosts"][:max_posts_per_user]:
                            parsed = self._parse_apify_post(post_item)
                            if parsed:
                                posts.append(parsed)
                        results.setdefault(uname, [])
                        results[uname].extend(posts)
                    else:
                        # Individual post item — derive username from owner fields
                        uname = (
                            item.get("ownerUsername")
                            or item.get("username")
                            or (item.get("owner") or {}).get("username")
                            or ""
                        ).lower()
                        if not uname:
                            continue
                        results.setdefault(uname, [])
                        if len(results[uname]) < max_posts_per_user:
                            parsed = self._parse_apify_post(item)
                            if parsed:
                                results[uname].append(parsed)
                except Exception as e:
                    logger.error(f"Error parsing batch item: {e}", exc_info=True)
                    continue

            logger.info(f"Batch scrape returned results for {len(results)}/{len(usernames)} profiles")
            return results

        except Exception as e:
            logger.error(f"Apify batch scraping failed: {e}")
            return {}

    async def scrape_stories(self, username: str) -> List[Dict]:
        """
        Scrape active stories from an Instagram profile.
        
        Note: Apify's Instagram scraper may have limited story support.
        Stories require the account to be logged in and following the user.
        
        Args:
            username: Instagram username
            
        Returns:
            List of story dictionaries
        """
        try:
            logger.info(f"Starting Apify story scrape for @{username}")
            
            # Configure for stories
            run_input = {
                "usernames": [username],
                "resultsType": "stories",
                "searchType": "user"
            }
            
            run = self.client.actor(self.actor_id).call(run_input=run_input)
            
            stories = []
            for item in self.client.dataset(run["defaultDatasetId"]).iterate_items():
                try:
                    story = self._parse_apify_story(item)
                    if story:
                        stories.append(story)
                except Exception as e:
                    logger.error(f"Error parsing story: {e}")
                    continue
            
            logger.info(f"Successfully scraped {len(stories)} stories from @{username}")
            return stories
            
        except Exception as e:
            logger.error(f"Apify story scraping failed for @{username}: {e}")
            return []
    
    def _parse_apify_story(self, item: Dict) -> Optional[Dict]:
        """
        Parse Apify story data into our standard format.
        
        Args:
            item: Raw story data from Apify
            
        Returns:
            Parsed story dictionary or None if parsing fails
        """
        try:
            return {
                'url': item.get('url', ''),
                'text': item.get('caption', ''),
                'image_url': item.get('displayUrl'),
                'timestamp': datetime.fromisoformat(item['timestamp'].replace('Z', '+00:00')) if item.get('timestamp') else datetime.now(),
                'expires_at': None  # Stories expire in 24h
            }
        except Exception as e:
            logger.error(f"Error parsing Apify story: {e}")
            return None


# Made with Bob