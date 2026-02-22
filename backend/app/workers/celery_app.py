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
    # Scrape posts once daily at 9 AM (when societies typically post)
    'scrape-posts-daily': {
        'task': 'app.workers.scraping_tasks.scrape_all_posts',
        'schedule': crontab(hour=9, minute=0),
        'options': {'queue': 'scraping'}
    },
    
    # Check for upcoming events and send notifications every 10 minutes
    'send-upcoming-event-notifications': {
        'task': 'app.workers.notification_tasks.send_upcoming_event_notifications',
        'schedule': 600.0,  # 10 minutes in seconds
        'options': {'queue': 'notifications'}
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
    
    # Health check every 5 minutes
    'health-check': {
        'task': 'app.workers.maintenance_tasks.health_check',
        'schedule': 300.0,  # 5 minutes
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
