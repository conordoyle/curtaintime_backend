"""
Celery tasks for scheduling theatre scrapes.
Handles the periodic dispatching of scheduled scraping operations.
"""
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any

from ..celery_app import celery_app
from ..models.database import SessionLocal, ScheduledScrape
from .scraping import scrape_single_theatre

# Configure logging
logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="app.tasks.scheduling.dispatch_scheduled_scrapes")
def dispatch_scheduled_scrapes(self) -> Dict[str, Any]:
    """
    Celery task to dispatch scheduled theatre scrapes.
    This task runs periodically and triggers scrapes for theatres that are due.
    """
    now = datetime.utcnow()
    logger.info(f"Starting dispatch_scheduled_scrapes task at {now}")

    db = SessionLocal()
    try:
        # Get current time for comparison

        # Find all enabled scheduled scrapes that are due to run
        due_schedules = db.query(ScheduledScrape).filter(
            ScheduledScrape.enabled == True,
            ScheduledScrape.next_run <= now
        ).all()

        if not due_schedules:
            logger.info(f"No scheduled scrapes due at {now}. Next check in 30 minutes.")
            return {
                "status": "completed",
                "message": "No scheduled scrapes due",
                "dispatched_count": 0,
                "checked_at": now.isoformat()
            }

        logger.info(f"Found {len(due_schedules)} scheduled scrapes due to run: {[f'{s.theatre_id}@{s.next_run}' for s in due_schedules]}")

        # Dispatch scrapes for each due schedule
        dispatched_tasks = []
        for schedule in due_schedules:
            try:
                logger.info(f"Dispatching scrape for theatre: {schedule.theatre.name} ({schedule.theatre.id})")

                # Trigger the scrape (without force_scrape=True for efficiency)
                task = scrape_single_theatre.delay(schedule.theatre.id)
                dispatched_tasks.append({
                    "theatre_id": schedule.theatre.id,
                    "theatre_name": schedule.theatre.name,
                    "task_id": task.id,
                    "schedule_type": schedule.schedule_type
                })

                # Update the next_run time based on schedule type
                schedule.next_run = _calculate_next_run(schedule, now)
                schedule.last_run = now

                logger.info(f"Updated next_run for {schedule.theatre.name} to {schedule.next_run}")

            except Exception as e:
                logger.error(f"Failed to dispatch scrape for theatre {schedule.theatre.id}: {str(e)}")
                # Continue with other schedules even if one fails

        # Commit all the updates
        db.commit()

        logger.info(f"Successfully dispatched {len(dispatched_tasks)} scheduled scrapes")

        return {
            "status": "completed",
            "message": f"Dispatched {len(dispatched_tasks)} scheduled scrapes",
            "dispatched_count": len(dispatched_tasks),
            "dispatched_tasks": dispatched_tasks,
            "checked_at": now.isoformat()
        }

    except Exception as e:
        logger.error(f"Error in dispatch_scheduled_scrapes: {str(e)}")
        db.rollback()
        return {
            "status": "error",
            "error": str(e),
            "dispatched_count": 0
        }

    finally:
        db.close()


def _calculate_next_run(schedule: ScheduledScrape, from_time: datetime) -> datetime:
    """
    Calculate the next run time for a scheduled scrape based on its configuration.

    Args:
        schedule: The ScheduledScrape model instance
        from_time: The time to calculate from (usually current time)

    Returns:
        datetime: The next time this schedule should run
    """
    if schedule.schedule_type == "daily":
        # Run every day at the configured hour/minute
        config = schedule.schedule_config or {}
        hour = config.get('hour', 2)  # Default 2 AM
        minute = config.get('minute', 0)  # Default top of hour

        next_run = from_time.replace(hour=hour, minute=minute, second=0, microsecond=0)

        # If we've already passed that time today, schedule for tomorrow
        if next_run <= from_time:
            next_run = next_run + timedelta(days=1)

        return next_run

    elif schedule.schedule_type == "weekly":
        # Run once per week on specified day at specified time
        config = schedule.schedule_config or {}
        day_of_week = config.get('day_of_week', 1)  # Default Monday (0=Monday, 6=Sunday)
        hour = config.get('hour', 2)
        minute = config.get('minute', 0)

        # Find the next occurrence of the specified day
        days_ahead = (day_of_week - from_time.weekday()) % 7
        if days_ahead == 0 and from_time.hour >= hour and from_time.minute >= minute:
            # Today is the target day but we've already passed the time
            days_ahead = 7

        next_run = from_time.replace(hour=hour, minute=minute, second=0, microsecond=0)
        next_run = next_run + timedelta(days=days_ahead)

        return next_run

    elif schedule.schedule_type == "hourly":
        # Run every hour at the specified minute
        config = schedule.schedule_config or {}
        minute = config.get('minute', 0)  # Default top of hour

        next_run = from_time.replace(minute=minute, second=0, microsecond=0)

        # If we've already passed that minute in this hour, schedule for next hour
        if next_run <= from_time:
            next_run = next_run + timedelta(hours=1)

        return next_run

    else:
        # Unknown schedule type - default to daily at 2 AM
        logger.warning(f"Unknown schedule type '{schedule.schedule_type}' for theatre {schedule.theatre_id}, defaulting to daily")
        next_run = from_time.replace(hour=2, minute=0, second=0, microsecond=0)
        if next_run <= from_time:
            next_run = next_run + timedelta(days=1)
        return next_run
