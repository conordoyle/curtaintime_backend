"""
Celery application configuration for CurtainTime backend.
Handles background task processing for theatre scraping operations.
"""
import os
from celery import Celery
from celery.schedules import crontab
from dotenv import load_dotenv


# Load environment variables
load_dotenv()

# Redis configuration
REDIS_URL = os.getenv("REDIS_URL")
if not REDIS_URL:
    raise ValueError("REDIS_URL environment variable is required")

# Create Celery app
celery_app = Celery(
    "curtaintime",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["app.tasks.scraping", "app.tasks.parsing", "app.tasks.images", "app.tasks.scheduling"]
)

# Celery configuration
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,

    # Worker settings
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_max_tasks_per_child=50,

    # Result backend settings
    result_expires=3600,  # 1 hour
    result_backend_transport_options={
        "retry_policy": {"timeout": 5.0}
    },

    # Beat schedule configuration
    beat_schedule={
        "dispatch-scheduled-scrapes": {
            "task": "app.tasks.scheduling.dispatch_scheduled_scrapes",
            "schedule": crontab(minute="*/30"),  # Every 30 minutes
        },
        "scrape-all-theatres-daily": {
            "task": "app.tasks.scraping.scrape_all_theatres",
            "schedule": crontab(hour=2, minute=0),  # Daily at 2 AM UTC (legacy)
        },
    },
)



# Optional: Configure logging
if __name__ == "__main__":
    celery_app.start()
