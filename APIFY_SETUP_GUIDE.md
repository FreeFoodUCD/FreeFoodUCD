# Apify Instagram Scraper Setup Guide

This guide explains how to set up Apify for reliable Instagram scraping in the FreeFood UCD platform.

## Why Apify?

Instagram actively blocks automated scraping tools like Playwright and Selenium. Apify provides:
- ✅ Reliable Instagram scraping without detection
- ✅ Handles authentication and anti-bot measures
- ✅ Maintained and updated regularly
- ✅ Pay-per-use pricing (~$0.25 per 1000 posts)
- ✅ No need to manage browser sessions or cookies

## Setup Steps

### 1. Create Apify Account

1. Go to [https://apify.com](https://apify.com)
2. Sign up for a free account
3. Free tier includes $5 credit (enough for ~20,000 posts)

### 2. Get API Token

1. Log into Apify Console
2. Go to **Settings** → **Integrations**
3. Copy your **API Token**
4. Add to `backend/.env`:
   ```bash
   APIFY_API_TOKEN=apify_api_xxxxxxxxxxxxxxxxxxxxxxxx
   ```

### 3. Install Dependencies

```bash
cd backend
source venv/bin/activate
pip install -r requirements.txt
```

This installs `apify-client==1.7.1`

### 4. Test the Integration

Create a test script:

```python
from app.services.scraper.apify_scraper import ApifyInstagramScraper
import asyncio

async def test():
    scraper = ApifyInstagramScraper(api_token="your_token_here")
    posts = await scraper.scrape_posts("ucdlawsoc", max_posts=3)
    print(f"Scraped {len(posts)} posts")
    for post in posts:
        print(f"- {post['url']}: {post['caption'][:50]}...")

asyncio.run(test())
```

## Apify Actor Used

**Actor:** `apify/instagram-profile-scraper`
- **Documentation:** https://apify.com/apify/instagram-profile-scraper
- **Features:**
  - Scrape posts from public profiles
  - Extract captions, images, timestamps
  - Optional story scraping (requires login)
  - Rate limiting handled automatically

## Pricing

### Free Tier
- $5 credit per month
- ~20,000 posts/month
- Perfect for testing

### Paid Plans
- **Starter:** $49/month
  - $49 platform usage
  - Additional usage: $0.25 per 1000 posts
  - Recommended for production

### Cost Estimation for FreeFood UCD

**Assumptions:**
- 8 societies monitored
- Each posts 2-3 times/week = ~20 posts/week
- Scrape last 3 posts daily at 9 AM UTC

**Monthly Usage:**
- Posts scraped per run: 8 societies × 3 posts = 24 posts
- Runs per day: 1 (daily at 9 AM)
- Posts per day: 24 posts
- Posts per month: ~720 posts

**Monthly Cost:**
- Platform: $49
- Usage: 720 posts × $0.25/1000 = $0.18
- **Total: ~$49/month** (mostly platform fee)

**Note:** Daily scraping is much more cost-effective than every 30 minutes while still catching all new posts.

## Configuration

### Scraping Frequency

Edit `backend/app/workers/celery_app.py`:

```python
# Scrape posts daily at 9 AM UTC
beat_schedule = {
    'daily-scrape': {
        'task': 'app.workers.scraping_tasks.scrape_all_societies',
        'schedule': crontab(hour=9, minute=0),
    },
}
```

**Why daily?**
- Societies typically post 2-3 times per week
- Daily scraping catches all new posts
- Much more cost-effective (~$49/month vs ~$58/month)
- Reduces API load and rate limiting issues

### Max Posts Per Society

Edit `backend/app/workers/scraping_tasks.py`:

```python
# Scrape last 3 posts (default)
posts_data = await scraper.scrape_posts(society.instagram_handle, max_posts=3)

# Or scrape more for initial backfill
posts_data = await scraper.scrape_posts(society.instagram_handle, max_posts=10)
```

## Story Scraping

**Note:** Story scraping requires Instagram login and may have limitations.

Apify's Instagram scraper can scrape stories, but:
- Requires authenticated session
- May not work for all accounts
- Stories expire in 24 hours

To enable story scraping:

```python
stories = await scraper.scrape_stories("ucdlawsoc")
```

## Monitoring

### Check Apify Dashboard

1. Go to [https://console.apify.com](https://console.apify.com)
2. View **Runs** to see scraping activity
3. Monitor **Usage** to track costs
4. Check **Logs** for errors

### Check Application Logs

```bash
# View Celery worker logs
cd backend
tail -f celery.log

# View scraping logs
grep "Apify" celery.log
```

## Troubleshooting

### Error: "Invalid API token"
- Check token in `.env` file
- Verify token in Apify Console → Settings → Integrations

### Error: "Insufficient credits"
- Check balance in Apify Console
- Add payment method or upgrade plan

### No posts returned
- Verify Instagram username is correct
- Check if profile is public
- View run logs in Apify Console

### Rate limiting
- Apify handles rate limiting automatically
- If issues persist, reduce scraping frequency

## Alternative: Apify Proxy

For even more reliability, use Apify's residential proxies:

```python
run_input = {
    "usernames": [username],
    "resultsLimit": max_posts,
    "proxy": {
        "useApifyProxy": True,
        "apifyProxyGroups": ["RESIDENTIAL"]
    }
}
```

**Cost:** +$12.50 per GB of proxy traffic

## Production Checklist

- [ ] Apify account created
- [ ] API token added to `.env`
- [ ] Dependencies installed
- [ ] Test scraping works
- [ ] Payment method added (for production)
- [ ] Monitoring set up
- [ ] Scraping frequency configured
- [ ] Error alerts configured

## Support

- **Apify Documentation:** https://docs.apify.com
- **Instagram Scraper Docs:** https://apify.com/apify/instagram-profile-scraper
- **Apify Support:** support@apify.com

---

Made with Bob