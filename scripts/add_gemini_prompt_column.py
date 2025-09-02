"""
Migration script to add gemini_prompt column to scrape_logs table.
Run this script to add the new column to existing databases.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.database import engine, ScrapeLog
from sqlalchemy import text

def add_gemini_prompt_column():
    """Add gemini_prompt column to scrape_logs table."""
    try:
        # Check if column already exists
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'scrape_logs' AND column_name = 'gemini_prompt'
            """))
            if result.fetchone():
                print("gemini_prompt column already exists.")
                return

            # Add the column
            conn.execute(text("""
                ALTER TABLE scrape_logs ADD COLUMN gemini_prompt TEXT
            """))
            conn.commit()

        print("✅ Successfully added gemini_prompt column to scrape_logs table")

    except Exception as e:
        print(f"❌ Error adding gemini_prompt column: {e}")

if __name__ == "__main__":
    add_gemini_prompt_column()
