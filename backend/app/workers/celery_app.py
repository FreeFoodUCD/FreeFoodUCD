from celery import Celery
from celery.schedules import crontab
from app.core.config import settings

# Create Celery app
celery_app = Celery(
    "freefood",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=['app.workers.scraping_tasks', 'app.workers.notification_tasks']
)

# Configure Celery
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Europe/Dublin',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)

# Celery Beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
    # Scrape stories every 5 minutes
    'scrape-stories-every-5-minutes': {
        'task': 'app.workers.scraping_tasks.scrape_all_stories',
        'schedule': 300.0,  # 5 minutes in seconds
        'options': {'queue': 'scraping'}
    },
    
    # Scrape posts every 15 minutes
    'scrape-posts-every-15-minutes': {
        'task': 'app.workers.scraping_tasks.scrape_all_posts',
        'schedule': 900.0,  # 15 minutes in seconds
        'options': {'queue': 'scraping'}
    },
    
    # Cleanup expired stories daily at 2 AM
    'cleanup-expired-stories': {
        'task': 'app.workers.maintenance_tasks.cleanup_expired_stories',
        'schedule': crontab(hour=2, minute=0),
        'options': {'queue': 'maintenance'}
    },
    
    # Archive old events daily at 3 AM
    'archive-old-events': {
        'task': 'app.workers.maintenance_tasks.archive_old_events',
        'schedule': crontab(hour=3, minute=0),
        'options': {'queue': 'maintenance'}
    },
    
    # Health check every minute
    'health-check': {
        'task': 'app.workers.maintenance_tasks.health_check',
        'schedule': 60.0,  # 1 minute
        'options': {'queue': 'maintenance'}
    },
}

# Task routing
celery_app.conf.task_routes = {
    'app.workers.scraping_tasks.*': {'queue': 'scraping'},
    'app.workers.notification_tasks.*': {'queue': 'notifications'},
    'app.workers.maintenance_tasks.*': {'queue': 'maintenance'},
}

# Made with Bob
