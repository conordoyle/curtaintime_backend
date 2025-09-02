"""
Celery tasks for processing and uploading show images.
Handles image optimization and cloud storage upload.
"""
import logging
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from ..celery_app import celery_app
from ..models.database import SessionLocal, Show
from ..services.vercel_blob import VercelBlobService

# Configure logging
logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="app.tasks.images.process_show_image")
def process_show_image(self, show_id: int, image_url: str) -> Dict[str, Any]:
    """
    Celery task to process and upload a show image.

    Args:
        show_id: Database ID of the show
        image_url: Original image URL to process

    Returns:
        Dict containing processing results and status
    """
    logger.info(f"Starting image processing for show {show_id}: {image_url}")

    db = SessionLocal()
    try:
        # Get the show from database
        show = db.query(Show).filter(Show.id == show_id).first()
        if not show:
            raise ValueError(f"Show {show_id} not found")

        # Skip if already processed
        if show.image_url and show.image_url.startswith("https://blob.vercel-storage.com"):
            logger.info(f"Show {show_id} already has processed image, skipping")
            return {
                "status": "skipped",
                "show_id": show_id,
                "message": "Image already processed"
            }

        # Initialize blob service
        blob_service = VercelBlobService.from_env()

        # Process and upload image
        blob_url = blob_service.process_and_upload_image(show_id, image_url)

        if blob_url:
            # Update show with new image URL
            show.image_url = blob_url
            db.commit()

            logger.info(f"Successfully processed image for show {show_id}: {blob_url}")

            return {
                "status": "success",
                "show_id": show_id,
                "original_url": image_url,
                "blob_url": blob_url,
                "message": "Image processed and uploaded successfully"
            }
        else:
            logger.warning(f"Failed to process image for show {show_id}")
            return {
                "status": "failed",
                "show_id": show_id,
                "original_url": image_url,
                "message": "Image processing failed"
            }

    except Exception as e:
        logger.error(f"Error processing image for show {show_id}: {str(e)}")
        db.rollback()

        return {
            "status": "error",
            "show_id": show_id,
            "original_url": image_url,
            "error": str(e)
        }

    finally:
        db.close()


@celery_app.task(bind=True, name="app.tasks.images.process_theatre_images")
def process_theatre_images(self, theatre_id: str) -> Dict[str, Any]:
    """
    Process images for all shows in a theatre that don't have processed images.

    Args:
        theatre_id: ID of the theatre

    Returns:
        Dict containing processing results
    """
    logger.info(f"Starting batch image processing for theatre: {theatre_id}")

    db = SessionLocal()
    try:
        # Find shows with images that need processing
        shows_with_images = db.query(Show).filter(
            Show.theatre_id == theatre_id,
            Show.image_url.isnot(None),
            Show.image_url != ""
        ).all()

        logger.info(f"Found {len(shows_with_images)} shows with images in theatre {theatre_id}")

        # Filter shows that need processing
        shows_to_process = []
        for show in shows_with_images:
            # Check if image URL indicates it needs processing
            if not show.image_url.startswith("https://blob.vercel-storage.com"):
                shows_to_process.append(show)

        logger.info(f"Found {len(shows_to_process)} shows needing image processing")

        if not shows_to_process:
            return {
                "status": "completed",
                "theatre_id": theatre_id,
                "message": "No images to process",
                "shows_processed": 0
            }

        # Trigger individual image processing tasks
        processing_tasks = []
        for show in shows_to_process:
            try:
                task = process_show_image.delay(show.id, show.image_url)
                processing_tasks.append({
                    "show_id": show.id,
                    "task_id": task.id
                })
                logger.debug(f"Triggered image processing for show {show.id}")
            except Exception as e:
                logger.warning(f"Failed to trigger image processing for show {show.id}: {str(e)}")

        logger.info(f"Triggered {len(processing_tasks)} image processing tasks")

        return {
            "status": "completed",
            "theatre_id": theatre_id,
            "shows_to_process": len(shows_to_process),
            "tasks_triggered": len(processing_tasks),
            "tasks": processing_tasks
        }

    except Exception as e:
        logger.error(f"Error in batch image processing for theatre {theatre_id}: {str(e)}")
        db.rollback()

        return {
            "status": "error",
            "theatre_id": theatre_id,
            "error": str(e)
        }

    finally:
        db.close()


@celery_app.task(bind=True, name="app.tasks.images.cleanup_orphaned_images")
def cleanup_orphaned_images(self) -> Dict[str, Any]:
    """
    Clean up images in blob storage that are no longer referenced by shows.
    This is a maintenance task that should be run periodically.

    Returns:
        Dict containing cleanup results
    """
    logger.info("Starting orphaned image cleanup")

    try:
        # This is a placeholder for blob storage cleanup
        # In a production implementation, you would:
        # 1. List all images in blob storage
        # 2. Check which ones are still referenced in the database
        # 3. Delete unreferenced images

        logger.warning("Orphaned image cleanup not yet implemented")

        return {
            "status": "not_implemented",
            "message": "Orphaned image cleanup is a placeholder - implement based on your blob storage API"
        }

    except Exception as e:
        logger.error(f"Error during orphaned image cleanup: {str(e)}")

        return {
            "status": "error",
            "error": str(e)
        }


@celery_app.task(bind=True, name="app.tasks.images.validate_image_urls")
def validate_image_urls(self, theatre_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Validate that image URLs are accessible and working.

    Args:
        theatre_id: Optional theatre ID to limit validation scope

    Returns:
        Dict containing validation results
    """
    import requests

    logger.info(f"Starting image URL validation for theatre: {theatre_id or 'all'}")

    db = SessionLocal()
    try:
        # Query shows with images
        query = db.query(Show).filter(
            Show.image_url.isnot(None),
            Show.image_url != ""
        )

        if theatre_id:
            query = query.filter(Show.theatre_id == theatre_id)

        shows_with_images = query.all()

        logger.info(f"Validating {len(shows_with_images)} image URLs")

        valid_count = 0
        invalid_count = 0
        invalid_urls = []

        for show in shows_with_images:
            try:
                # Check if URL is accessible
                response = requests.head(show.image_url, timeout=10)

                if response.status_code == 200:
                    valid_count += 1
                else:
                    invalid_count += 1
                    invalid_urls.append({
                        "show_id": show.id,
                        "url": show.image_url,
                        "status_code": response.status_code
                    })

            except Exception as e:
                invalid_count += 1
                invalid_urls.append({
                    "show_id": show.id,
                    "url": show.image_url,
                    "error": str(e)
                })

        logger.info(f"Image validation complete: {valid_count} valid, {invalid_count} invalid")

        return {
            "status": "completed",
            "theatre_id": theatre_id,
            "total_images": len(shows_with_images),
            "valid_images": valid_count,
            "invalid_images": invalid_count,
            "invalid_urls": invalid_urls[:10]  # Limit to first 10 for brevity
        }

    except Exception as e:
        logger.error(f"Error during image URL validation: {str(e)}")
        db.rollback()

        return {
            "status": "error",
            "theatre_id": theatre_id,
            "error": str(e)
        }

    finally:
        db.close()
