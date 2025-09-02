"""
Celery tasks for parsing scraped markdown into structured show data.
Handles AI parsing, data validation, and database replacement operations.
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List
from sqlalchemy.orm import Session

from ..celery_app import celery_app
from ..models.database import SessionLocal, Show, ScrapeLog, Theatre
from ..parsers.gemini_parser import GeminiParser, ShowData

# Configure logging
logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="app.tasks.parsing.parse_theatre_shows")
def parse_theatre_shows(self, scrape_log_id: int, markdown: str, theatre_name: str) -> Dict[str, Any]:
    """
    Celery task to parse theatre shows from markdown content.

    Args:
        scrape_log_id: ID of the scrape log entry
        markdown: Raw markdown content to parse
        theatre_name: Name of the theatre for context

    Returns:
        Dict containing parsing results and status
    """
    logger.info(f"Starting parse task for scrape log {scrape_log_id}: {theatre_name}")

    db = SessionLocal()
    try:
        # Get scrape log and theatre info
        scrape_log = db.query(ScrapeLog).filter(ScrapeLog.id == scrape_log_id).first()
        if not scrape_log:
            raise ValueError(f"Scrape log {scrape_log_id} not found")

        theatre = db.query(Theatre).filter(Theatre.id == scrape_log.theatre_id).first()
        if not theatre:
            raise ValueError(f"Theatre {scrape_log.theatre_id} not found")

        # Skip parsing if page hasn't changed (optimization)
        if scrape_log.change_status == 'same':
            logger.info(f"Skipping LLM parsing for {theatre_name} - page unchanged")

            # Update scrape log status
            scrape_log.shows_found = 0
            scrape_log.shows_added = 0
            scrape_log.shows_updated = 0
            scrape_log.status = "unchanged"
            db.commit()

            return {
                "status": "unchanged",
                "scrape_log_id": scrape_log_id,
                "theatre_id": theatre.id,
                "theatre_name": theatre_name,
                "shows_found": 0,
                "shows_added": 0,
                "shows_updated": 0,
                "raw_shows_count": 0,
                "image_processing_triggered": False,
                "change_status": "same"
            }

        # Initialize parser and parse content
        parser = GeminiParser.from_env()
        raw_shows = parser.parse_theatre_markdown(markdown, theatre_name, scrape_log_id)

        # Validate parsed data
        valid_shows = parser.validate_show_data(raw_shows)

        logger.info(f"Parsed {len(valid_shows)} valid shows from {len(raw_shows)} raw items")

        # Store the Gemini JSON response for debugging/logging
        gemini_response = []
        for show in raw_shows:
            gemini_response.append({
                "title": show.title,
                "start_datetime": show.start_datetime.isoformat() if show.start_datetime else None,
                "description": show.description,
                "image_url": show.image_url,
                "ticket_url": show.ticket_url,
                "raw_data": show.raw_data
            })

        scrape_log.parsed_json = gemini_response

        # Replace all shows for this theatre with newly parsed data
        try:
            replaced_count, deleted_count = _replace_theatre_shows(db, theatre.id, valid_shows)

            # Update scrape log with results
            scrape_log.shows_found = len(valid_shows)
            scrape_log.shows_added = replaced_count
            scrape_log.shows_updated = 0  # No updates in replace mode

            # Update status based on results
            if replaced_count > 0:
                scrape_log.status = "completed"
            else:
                scrape_log.status = "completed_no_changes"

            db.commit()

            logger.info(f"Completed parsing for {theatre_name}: {replaced_count} shows replaced, {deleted_count} shows removed")

            # Trigger image processing for all shows with images (since all are "new")
            if replaced_count > 0:
                _trigger_image_processing(db, theatre.id)

            return {
                "status": "completed",
                "scrape_log_id": scrape_log_id,
                "theatre_id": theatre.id,
                "theatre_name": theatre_name,
                "shows_found": len(valid_shows),
                "shows_added": replaced_count,
                "shows_updated": 0,  # No updates in replace mode
                "shows_deleted": deleted_count,
                "raw_shows_count": len(raw_shows),
                "image_processing_triggered": replaced_count > 0
            }

        except Exception as e:
            logger.error(f"Failed to replace shows for {theatre_name}: {str(e)}")
            db.rollback()
            raise

    except Exception as e:
        logger.error(f"Error in parse_theatre_shows for {scrape_log_id}: {str(e)}")

        # Update scrape log with error
        if 'scrape_log' in locals():
            scrape_log.status = "parsing_error"
            scrape_log.error_message = f"Parsing error: {str(e)}"
            db.commit()

        db.rollback()

        return {
            "status": "error",
            "scrape_log_id": scrape_log_id,
            "theatre_name": theatre_name,
            "error": str(e)
        }

    finally:
        db.close()


def _replace_theatre_shows(db: Session, theatre_id: str, valid_shows: List[ShowData]) -> tuple[int, int]:
    """
    Replace all shows for a theatre with newly parsed data.
    This is done in a single atomic transaction to prevent data loss.

    Args:
        db: Database session
        theatre_id: ID of the theatre
        valid_shows: List of validated show data from AI parsing

    Returns:
        tuple[int, int]: (shows_replaced, shows_deleted)
    """
    logger.info(f"Replacing all shows for theatre {theatre_id}")

    # Safety check: ensure we have valid input
    if not theatre_id:
        raise ValueError("theatre_id cannot be empty")
    if valid_shows is None:
        raise ValueError("valid_shows cannot be None")

    # Count existing shows before deletion (for logging)
    existing_count = db.query(Show).filter(Show.theatre_id == theatre_id).count()
    logger.info(f"Found {existing_count} existing shows for theatre {theatre_id}")

    # Safety check: if we're about to delete a lot of shows but have no new data,
    # this might indicate a parsing error rather than actual deletions
    if existing_count > 0 and len(valid_shows) == 0:
        logger.warning(f"SAFETY CHECK: About to delete {existing_count} shows but no new shows found. "
                      f"This might indicate a parsing error. Aborting replacement.")
        raise ValueError(f"Refusing to delete {existing_count} shows when no new shows are available")

    # Perform atomic replacement within a transaction
    try:
        # Delete all existing shows for this theatre
        deleted_count = db.query(Show).filter(Show.theatre_id == theatre_id).delete()
        logger.info(f"Deleted {deleted_count} existing shows for theatre {theatre_id}")

        # Insert all new shows
        replaced_count = 0
        for show_data in valid_shows:
            try:
                new_show = Show(
                    theatre_id=theatre_id,
                    title=show_data.title,
                    start_datetime_utc=show_data.start_datetime,
                    description=show_data.description,
                    image_url=show_data.image_url,
                    ticket_url=show_data.ticket_url,
                    raw_data=show_data.raw_data
                )

                db.add(new_show)
                replaced_count += 1
                logger.debug(f"Added new show: {show_data.title}")

            except Exception as e:
                logger.error(f"Failed to add show '{show_data.title}': {str(e)}")
                # Continue with other shows rather than failing the entire transaction
                continue

        logger.info(f"Successfully replaced {replaced_count} shows for theatre {theatre_id}")
        return replaced_count, deleted_count

    except Exception as e:
        logger.error(f"Error during show replacement for theatre {theatre_id}: {str(e)}")
        # Re-raise to trigger transaction rollback in the calling function
        raise


def _trigger_image_processing(db: Session, theatre_id: str):
    """Trigger image processing for new shows with images."""
    try:
        # Find shows with images that don't have processed URLs
        shows_with_images = db.query(Show).filter(
            Show.theatre_id == theatre_id,
            Show.image_url.isnot(None),
            Show.image_url != ""  # Not empty string
        ).all()

        logger.info(f"Found {len(shows_with_images)} shows with images to process")

        # Trigger image processing tasks
        from .images import process_show_image

        for show in shows_with_images:
            try:
                # Check if image URL looks like it needs processing
                # (e.g., not already a blob URL)
                if not show.image_url.startswith("https://your-blob-store"):
                    process_show_image.delay(show.id, show.image_url)
                    logger.debug(f"Triggered image processing for show {show.id}")
            except Exception as e:
                logger.warning(f"Failed to trigger image processing for show {show.id}: {str(e)}")

    except Exception as e:
        logger.error(f"Error triggering image processing for theatre {theatre_id}: {str(e)}")


@celery_app.task(bind=True, name="app.tasks.parsing.cleanup_old_shows")
def cleanup_old_shows(self, days_old: int = 30) -> Dict[str, Any]:
    """
    Clean up old shows from the database.

    Args:
        days_old: Remove shows older than this many days

    Returns:
        Dict containing cleanup results
    """
    from datetime import timedelta

    logger.info(f"Starting cleanup of shows older than {days_old} days")

    db = SessionLocal()
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)

        # Count shows to be deleted
        old_shows_count = db.query(Show).filter(
            Show.start_datetime_utc < cutoff_date
        ).count()

        # Delete old shows
        deleted_count = db.query(Show).filter(
            Show.start_datetime_utc < cutoff_date
        ).delete()

        db.commit()

        logger.info(f"Cleaned up {deleted_count} old shows")

        return {
            "status": "completed",
            "shows_deleted": deleted_count,
            "cutoff_date": cutoff_date.isoformat()
        }

    except Exception as e:
        logger.error(f"Error during cleanup: {str(e)}")
        db.rollback()

        return {
            "status": "error",
            "error": str(e)
        }

    finally:
        db.close()
