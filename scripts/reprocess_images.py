#!/usr/bin/env python3
"""
Script to reprocess images for existing shows to fix Vercel Blob URLs.
This will update all shows with images to use the correct public URLs.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.database import SessionLocal, Show
from app.services.vercel_blob import VercelBlobService
from sqlalchemy import and_
from dotenv import load_dotenv

load_dotenv()

def reprocess_show_images():
    """Reprocess images for all shows to get correct Vercel Blob URLs."""
    print("🔄 Reprocessing images for existing shows...")

    db = SessionLocal()
    try:
        # Get all shows with images
        shows_with_images = db.query(Show).filter(
            and_(Show.image_url.isnot(None), Show.image_url != '')
        ).all()

        print(f"Found {len(shows_with_images)} shows with images to reprocess")

        if not shows_with_images:
            print("No shows with images found.")
            return

        # Initialize blob service
        blob_service = VercelBlobService.from_env()

        processed_count = 0
        error_count = 0

        for show in shows_with_images:
            try:
                print(f"🔄 Processing show {show.id}: {show.title[:50]}...")

                # Re-process the image
                blob_url = blob_service.process_and_upload_image(show.id, show.image_url)

                if blob_url:
                    # Update the show with the correct URL
                    show.image_url = blob_url
                    db.commit()
                    processed_count += 1
                    print(f"  ✅ Updated URL: {blob_url}")
                else:
                    error_count += 1
                    print(f"  ❌ Failed to reprocess image for show {show.id}")

            except Exception as e:
                error_count += 1
                print(f"  ❌ Error processing show {show.id}: {str(e)}")
                continue

        print("\n📊 Reprocessing complete!")
        print(f"  ✅ Successfully processed: {processed_count}")
        print(f"  ❌ Errors: {error_count}")
        print(f"  📝 Total shows: {len(shows_with_images)}")

    except Exception as e:
        print(f"❌ Error during reprocessing: {e}")
        db.rollback()

    finally:
        db.close()

if __name__ == "__main__":
    reprocess_show_images()
