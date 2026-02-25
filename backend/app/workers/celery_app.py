from celery import Celery
from celery.schedules import crontab
from celery.signals import worker_process_init, worker_process_shutdown
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# Create Celery app
celery_app = Celery(
    "freefood",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=['app.workers.scraping_tasks', 'app.workers.notification_tasks', 'app.workers.maintenance_tasks']
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
    # Use Redis for beat schedule instead of file (fixes permission issues)
    beat_scheduler='celery.beat:PersistentScheduler',
    beat_schedule_filename='/tmp/celerybeat-schedule',
    # IMPORTANT: Worker must consume from all queues
    task_default_queue='celery',
    task_create_missing_queues=True,
    # Fix Celery 6.0 deprecation warning
    broker_connection_retry_on_startup=True,
    # Use solo pool to avoid fork issues with asyncio
    worker_pool='solo',
)


@worker_process_init.connect
def init_worker(**kwargs):
    """Initialize worker process - dispose of any inherited engine connections."""
    logger.info("Initializing worker process")
    try:
        from app.db.base import dispose_engine
        # Dispose of the engine to ensure fresh connections in this process
        dispose_engine()
        logger.info("Disposed of inherited database engine")
    except Exception as e:
        logger.warning(f"Could not dispose engine on worker init: {e}")


@worker_process_shutdown.connect
def shutdown_worker(**kwargs):
    """Clean up worker process resources."""
    logger.info("Shutting down worker process")
    try:
        from app.db.base import dispose_engine
        dispose_engine()
        logger.info("Disposed of database engine on shutdown")
    except Exception as e:
        logger.warning(f"Could not dispose engine on worker shutdown: {e}")

# Celery Beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
    # Scrape posts 4x daily to catch posts close to event time
    'scrape-posts-8am': {
        'task': 'app.workers.scraping_tasks.scrape_all_posts',
        'schedule': crontab(hour=8, minute=0),
        'options': {'queue': 'scraping'}
    },
    'scrape-posts-11am': {
        'task': 'app.workers.scraping_tasks.scrape_all_posts',
        'schedule': crontab(hour=11, minute=0),
        'options': {'queue': 'scraping'}
    },
    'scrape-posts-3pm': {
        'task': 'app.workers.scraping_tasks.scrape_all_posts',
        'schedule': crontab(hour=15, minute=0),
        'options': {'queue': 'scraping'}
    },
    # TEMP TEST — remove after verifying auto-scrape works
    'scrape-posts-345pm': {
        'task': 'app.workers.scraping_tasks.scrape_all_posts',
        'schedule': crontab(hour=15, minute=45),
        'options': {'queue': 'scraping'}
    },
    'scrape-posts-7pm': {
        'task': 'app.workers.scraping_tasks.scrape_all_posts',
        'schedule': crontab(hour=19, minute=0),
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
