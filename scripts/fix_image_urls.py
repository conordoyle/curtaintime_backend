#!/usr/bin/env python3
"""
Script to fix image URLs by reverting to original theatre source URLs.
This will allow future scrapes to re-process images with correct Vercel Blob URLs.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.database import SessionLocal, Show
from sqlalchemy import and_
from dotenv import load_dotenv

load_dotenv()

def fix_image_urls():
    """Revert image URLs back to original theatre sources."""
    print("🔧 Fixing image URLs by reverting to original sources...")

    db = SessionLocal()
    try:
        # Get all shows with Vercel Blob URLs (the broken ones)
        shows_with_blob_urls = db.query(Show).filter(
            Show.image_url.like('https://blob.vercel-storage.com/%')
        ).all()

        print(f"Found {len(shows_with_blob_urls)} shows with broken Vercel Blob URLs")

        if not shows_with_blob_urls:
            print("No broken URLs found.")
            return

        # For each show, we need to find the original URL from raw_data
        fixed_count = 0
        no_original_count = 0

        for show in shows_with_blob_urls:
            try:
                # Look for original URL in raw_data
                if show.raw_data and 'image_url' in show.raw_data:
                    original_url = show.raw_data['image_url']
                    if original_url and not original_url.startswith('https://blob.vercel-storage.com'):
                        # Update to original URL
                        show.image_url = original_url
                        print(f"  ✅ Fixed show {show.id}: {original_url}")
                        fixed_count += 1
                    else:
                        print(f"  ⚠️  Show {show.id}: Original URL also broken or missing")
                        no_original_count += 1
                else:
                    print(f"  ❌ Show {show.id}: No raw_data with original URL")
                    no_original_count += 1

            except Exception as e:
                print(f"  ❌ Error processing show {show.id}: {str(e)}")
                no_original_count += 1
                continue

        # Commit all changes
        db.commit()

        print("\n📊 URL fixing complete!")
        print(f"  ✅ Fixed: {fixed_count}")
        print(f"  ❌ Could not fix: {no_original_count}")
        print(f"  📝 Total processed: {len(shows_with_blob_urls)}")

        if fixed_count > 0:
            print("\n🎯 Next steps:")
            print("  1. The images now point to original theatre URLs")
            print("  2. Run a new scrape to re-process images with correct Vercel Blob URLs")
            print("  3. Future scrapes will use the fixed VercelBlobService")

    except Exception as e:
        print(f"❌ Error during URL fixing: {e}")
        db.rollback()

    finally:
        db.close()

if __name__ == "__main__":
    fix_image_urls()
