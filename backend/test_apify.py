"""
Test script for Apify Instagram scraper.
Tests scraping posts from UCD Law Society.
"""

import asyncio
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.scraper.apify_scraper import ApifyInstagramScraper
from app.core.config import settings
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Changed to DEBUG to see raw data
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def test_apify():
    """Test the Apify Instagram scraper with UCD Law Society."""
    
    logger.info("=" * 60)
    logger.info("Testing Apify Instagram Scraper")
    logger.info("=" * 60)
    
    try:
        # Initialize scraper
        logger.info("\n1. Initializing Apify scraper...")
        scraper = ApifyInstagramScraper(api_token=settings.APIFY_API_TOKEN)
        logger.info("✓ Scraper initialized")
        
        # Test with UCD Law Society
        test_handle = "ucdlawsoc"
        logger.info(f"\n2. Scraping posts from @{test_handle}...")
        
        posts = await scraper.scrape_posts(test_handle, max_posts=3)
        
        logger.info(f"\n✓ Scraped {len(posts)} posts")
        
        # Display results
        logger.info("\n" + "=" * 60)
        logger.info("RESULTS")
        logger.info("=" * 60)
        
        if len(posts) == 0:
            logger.warning("No posts found. This could mean:")
            logger.warning("  - The account has no posts")
            logger.warning("  - The account is private")
            logger.warning("  - Apify API token is invalid")
            logger.warning("  - Apify credits exhausted")
        
        for i, post in enumerate(posts, 1):
            logger.info(f"\nPost {i}:")
            logger.info(f"  URL: {post['url']}")
            logger.info(f"  Timestamp: {post['timestamp']}")
            logger.info(f"  Image URL: {post.get('image_url', 'N/A')}")
            logger.info(f"  Caption ({len(post['caption'])} chars):")
            
            # Show first 200 chars of caption
            caption_preview = post['caption'][:200]
            if len(post['caption']) > 200:
                caption_preview += "..."
            logger.info(f"    {caption_preview}")
        
        logger.info("\n" + "=" * 60)
        logger.info("TEST COMPLETED SUCCESSFULLY")
        logger.info("=" * 60)
        
        return True
        
    except Exception as e:
        logger.error(f"\n✗ Test failed: {e}", exc_info=True)
        logger.error("\nTroubleshooting:")
        logger.error("  1. Check APIFY_API_TOKEN in backend/.env")
        logger.error("  2. Verify token at https://console.apify.com")
        logger.error("  3. Check Apify account has credits")
        logger.error("  4. View run logs at https://console.apify.com/actors/runs")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_apify())
    sys.exit(0 if success else 1)

# Made with Bob