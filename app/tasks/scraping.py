"""
Celery tasks for theatre scraping operations.
Handles the orchestration of scraping, logging, and triggering parsing.
"""
import logging
from datetime import datetime
from typing import Dict, Any
from sqlalchemy.orm import Session

from ..celery_app import celery_app
from ..models.database import SessionLocal, Theatre, ScrapeLog
from ..scrapers.theatre_scraper import TheatreScraper

# Configure logging
logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="app.tasks.scraping.scrape_single_theatre")
def scrape_single_theatre(self, theatre_id: str, force_scrape: bool = False) -> Dict[str, Any]:
    """
    Celery task to scrape a single theatre.

    Args:
        theatre_id: ID of the theatre to scrape
        force_scrape: If True, bypass change tracking and force a full scrape.
                     If False (default), use change tracking for efficiency.

    Returns:
        Dict containing scrape results and status
    """
    logger.info(f"Starting scrape task for theatre: {theatre_id}")

    db = SessionLocal()
    try:
        # Check if theatre exists and is enabled
        theatre = db.query(Theatre).filter(Theatre.id == theatre_id).first()
        if not theatre:
            raise ValueError(f"Theatre '{theatre_id}' not found")

        if not theatre.enabled:
            logger.info(f"Theatre '{theatre_id}' is disabled, skipping")
            return {
                "status": "skipped",
                "theatre_id": theatre_id,
                "message": "Theatre is disabled"
            }

        # Create scrape log entry
        scrape_log = ScrapeLog(
            theatre_id=theatre_id,
            status="running",
            shows_found=0,
            shows_added=0,
            shows_updated=0
        )
        db.add(scrape_log)
        db.commit()
        db.refresh(scrape_log)

        logger.info(f"Created scrape log entry: {scrape_log.id}")

        # Initialize scraper and perform scraping
        scraper = TheatreScraper.from_env()

        # Determine change tracking behavior based on force_scrape flag
        if force_scrape:
            # Manual scrape: always bypass change tracking for immediate results
            enable_change_tracking = False
            logger.info(f"Manual scrape: bypassing change tracking for immediate results")
        else:
            # Scheduled scrape: use change tracking for efficiency
            enable_change_tracking = theatre.config_data.get('change_tracking', {}).get('enabled', True) if theatre.config_data else True
            logger.info(f"Scheduled scrape: change tracking {'enabled' if enable_change_tracking else 'disabled'}")

        result = scraper.scrape_theatre_by_id(theatre_id, enable_change_tracking)

        # Store raw markdown in scrape log
        scrape_log.raw_markdown = result.markdown_content
        scrape_log.scrape_metadata = result.metadata

        # Store change tracking data if available
        if hasattr(result, 'change_status') and result.change_status:
            scrape_log.change_status = result.change_status
            scrape_log.previous_scrape_at = result.previous_scrape_at
            scrape_log.page_visibility = result.page_visibility
            scrape_log.change_metadata = result.change_metadata

            logger.info(f"Change tracking: {result.change_status} (previous: {result.previous_scrape_at})")

        # Update scrape log with results
        scrape_log.pages_scraped = result.pages_scraped
        scrape_log.successful_pages = result.successful_pages

        if result.errors:
            scrape_log.error_message = "; ".join(result.errors)

        # Determine final status
        if result.successful_pages == 0:
            scrape_log.status = "error"
        elif result.successful_pages < result.pages_scraped:
            scrape_log.status = "partial_success"
        else:
            scrape_log.status = "success"

        scrape_log.completed_at = datetime.utcnow()
        db.commit()

        # If we have successful content, trigger parsing
        if result.markdown_content and result.successful_pages > 0:
            from .parsing import parse_theatre_shows
            logger.info(f"Triggering parsing task for scrape log {scrape_log.id}")

            # Trigger parsing task asynchronously
            parse_task = parse_theatre_shows.delay(
                scrape_log_id=scrape_log.id,
                markdown=result.markdown_content,
                theatre_name=theatre.name
            )

            logger.info(f"Parsing task triggered: {parse_task.id}")

        logger.info(f"Completed scrape task for {theatre_id}: {scrape_log.status}")

        return {
            "status": scrape_log.status,
            "theatre_id": theatre_id,
            "scrape_log_id": scrape_log.id,
            "pages_scraped": result.pages_scraped,
            "successful_pages": result.successful_pages,
            "errors": result.errors,
            "parsing_triggered": bool(result.markdown_content and result.successful_pages > 0)
        }

    except Exception as e:
        logger.error(f"Error in scrape_single_theatre for {theatre_id}: {str(e)}")

        # Update scrape log with error if it exists
        if 'scrape_log' in locals():
            scrape_log.status = "error"
            scrape_log.error_message = str(e)
            scrape_log.completed_at = datetime.utcnow()
            db.commit()

        db.rollback()

        return {
            "status": "error",
            "theatre_id": theatre_id,
            "error": str(e)
        }

    finally:
        db.close()


@celery_app.task(bind=True, name="app.tasks.scraping.scrape_all_theatres")
def scrape_all_theatres(self, force_scrape: bool = False) -> Dict[str, Any]:
    """
    Celery task to scrape all enabled theatres.
    This is the main scheduled task that runs daily.

    Args:
        force_scrape: If True, bypass change tracking and force full scrapes.
                     If False (default), use change tracking for efficiency.
    """
    logger.info("Starting scrape_all_theatres task")

    db = SessionLocal()
    try:
        # Get all enabled theatres
        theatres = db.query(Theatre).filter(Theatre.enabled == True).all()

        if not theatres:
            logger.warning("No enabled theatres found")
            return {
                "status": "completed",
                "message": "No enabled theatres found",
                "theatres_scraped": 0
            }

        logger.info(f"Found {len(theatres)} enabled theatres to scrape")

        # Launch individual scraping tasks
        scrape_tasks = []
        for theatre in theatres:
            logger.info(f"Triggering scrape for theatre: {theatre.name} ({theatre.id})")

            # Launch task asynchronously
            task = scrape_single_theatre.delay(theatre.id, force_scrape=force_scrape)
            scrape_tasks.append({
                "theatre_id": theatre.id,
                "theatre_name": theatre.name,
                "task_id": task.id
            })

        logger.info(f"Triggered {len(scrape_tasks)} scraping tasks")

        return {
            "status": "completed",
            "message": f"Triggered scraping for {len(theatres)} theatres",
            "theatres_scraped": len(theatres),
            "tasks": scrape_tasks
        }

    except Exception as e:
        logger.error(f"Error in scrape_all_theatres: {str(e)}")
        db.rollback()

        return {
            "status": "error",
            "error": str(e),
            "theatres_scraped": 0
        }

    finally:
        db.close()


@celery_app.task(bind=True, name="app.tasks.scraping.get_scrape_status")
def get_scrape_status(self, scrape_log_id: int) -> Dict[str, Any]:
    """
    Get the status of a specific scrape operation.

    Args:
        scrape_log_id: ID of the scrape log entry

    Returns:
        Dict containing scrape status information
    """
    db = SessionLocal()
    try:
        scrape_log = db.query(ScrapeLog).filter(ScrapeLog.id == scrape_log_id).first()

        if not scrape_log:
            return {
                "status": "not_found",
                "scrape_log_id": scrape_log_id,
                "error": "Scrape log not found"
            }

        return {
            "status": "found",
            "scrape_log_id": scrape_log.id,
            "theatre_id": scrape_log.theatre_id,
            "scrape_status": scrape_log.status,
            "started_at": scrape_log.started_at.isoformat() if scrape_log.started_at else None,
            "completed_at": scrape_log.completed_at.isoformat() if scrape_log.completed_at else None,
            "shows_found": scrape_log.shows_found,
            "shows_added": scrape_log.shows_added,
            "shows_updated": scrape_log.shows_updated,
            "error_message": scrape_log.error_message,
            "has_raw_markdown": bool(scrape_log.raw_markdown)
        }

    except Exception as e:
        logger.error(f"Error getting scrape status for {scrape_log_id}: {str(e)}")
        return {
            "status": "error",
            "scrape_log_id": scrape_log_id,
            "error": str(e)
        }

    finally:
        db.close()
