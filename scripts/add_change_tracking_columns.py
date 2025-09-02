"""
Migration script to add change tracking columns to scrape_logs table.
Run this script to add the new columns to existing databases.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.database import engine
from sqlalchemy import text

def add_change_tracking_columns():
    """Add change tracking columns to scrape_logs table."""
    try:
        # Check if columns already exist
        with engine.connect() as conn:
            # Check change_status column
            result = conn.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'scrape_logs' AND column_name = 'change_status'
            """))
            if not result.fetchone():
                # Add change tracking columns
                conn.execute(text("""
                    ALTER TABLE scrape_logs
                    ADD COLUMN change_status VARCHAR(50),
                    ADD COLUMN previous_scrape_at TIMESTAMP WITH TIME ZONE,
                    ADD COLUMN page_visibility VARCHAR(20),
                    ADD COLUMN change_metadata JSONB
                """))
                print("✅ Added change tracking columns to scrape_logs table")
            else:
                print("✅ Change tracking columns already exist")

        print("✅ Database migration completed successfully")

    except Exception as e:
        print(f"❌ Error adding change tracking columns: {e}")

if __name__ == "__main__":
    add_change_tracking_columns()
