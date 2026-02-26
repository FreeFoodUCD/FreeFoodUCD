"""
Instaloader-based Instagram scraper.
Free, self-hosted replacement for Apify. Runs on the Railway worker service.
"""

import asyncio
import instaloader
import itertools
import time
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

# Shared Instaloader instance (stateless — no login required for public profiles)
_L = instaloader.Instaloader(download_pictures=False, quiet=True)


class InstaLoaderScraper:
    """
    Instagram scraper using Instaloader (free, self-hosted).
    Drop-in replacement for ApifyInstagramScraper — same public interface.
    """

    async def scrape_posts(self, username: str, max_posts: int = 3) -> List[Dict]:
        """
        Scrape recent posts from a public Instagram profile.

        Args:
            username: Instagram username (without @)
            max_posts: Maximum number of posts to return

        Returns:
            List of post dicts: {'url', 'caption', 'image_url', 'timestamp'}
        """
        def _fetch():
            posts = []
            try:
                logger.info(f"Instaloader: scraping @{username}")
                profile = instaloader.Profile.from_username(_L.context, username)
                for post in itertools.islice(profile.get_posts(), max_posts):
                    posts.append({
                        'url': f"https://www.instagram.com/p/{post.shortcode}/",
                        'caption': post.caption or '',
                        'image_url': post.url,
                        'timestamp': post.date_utc,
                    })
                logger.info(f"Instaloader: got {len(posts)} posts from @{username}")
            except instaloader.exceptions.ProfileNotExistsException:
                logger.warning(f"Instaloader: profile @{username} does not exist or is private")
            except Exception as e:
                logger.error(f"Instaloader: scraping failed for @{username}: {e}")
            return posts

        return await asyncio.to_thread(_fetch)

    async def scrape_posts_batch(self, usernames: List[str], max_posts_per_user: int = 3) -> Dict[str, List[Dict]]:
        """
        Scrape recent posts for multiple profiles sequentially.

        Args:
            usernames: List of Instagram usernames (without @)
            max_posts_per_user: Max posts per profile

        Returns:
            Dict mapping username (lowercase) -> list of post dicts
        """
        if not usernames:
            return {}

        def _fetch_all():
            results: Dict[str, List[Dict]] = {}
            logger.info(f"Instaloader: batch scraping {len(usernames)} handles")
            for i, username in enumerate(usernames):
                single_posts: List[Dict] = []
                try:
                    logger.info(f"Instaloader: scraping @{username}")
                    profile = instaloader.Profile.from_username(_L.context, username)
                    for post in itertools.islice(profile.get_posts(), max_posts_per_user):
                        single_posts.append({
                            'url': f"https://www.instagram.com/p/{post.shortcode}/",
                            'caption': post.caption or '',
                            'image_url': post.url,
                            'timestamp': post.date_utc,
                        })
                    logger.info(f"Instaloader: got {len(single_posts)} posts from @{username}")
                except instaloader.exceptions.ProfileNotExistsException:
                    logger.warning(f"Instaloader: profile @{username} does not exist or is private")
                except Exception as e:
                    logger.error(f"Instaloader: scraping failed for @{username}: {e}")
                if single_posts:
                    results[username.lower()] = single_posts
                if i < len(usernames) - 1:
                    time.sleep(2)
            logger.info(f"Instaloader: batch complete — results for {len(results)}/{len(usernames)} profiles")
            return results

        return await asyncio.to_thread(_fetch_all)
