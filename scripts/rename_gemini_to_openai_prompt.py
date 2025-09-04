"""
Migration script to rename gemini_prompt column to openai_prompt in scrape_logs table.
Run this script to update existing databases.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.database import engine
from sqlalchemy import text

def rename_gemini_to_openai_prompt():
    """Rename gemini_prompt column to openai_prompt in scrape_logs table."""
    try:
        # Check if gemini_prompt column exists
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'scrape_logs' AND column_name = 'gemini_prompt'
            """))
            if not result.fetchone():
                print("gemini_prompt column does not exist. Checking if openai_prompt already exists...")
                result = conn.execute(text("""
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name = 'scrape_logs' AND column_name = 'openai_prompt'
                """))
                if result.fetchone():
                    print("openai_prompt column already exists.")
                    return
                else:
                    print("Neither gemini_prompt nor openai_prompt column exists. Please run add_gemini_prompt_column.py first.")
                    return

            # Rename the column
            conn.execute(text("""
                ALTER TABLE scrape_logs RENAME COLUMN gemini_prompt TO openai_prompt
            """))
            conn.commit()

        print("✅ Successfully renamed gemini_prompt column to openai_prompt in scrape_logs table")

    except Exception as e:
        print(f"❌ Error renaming column: {e}")

if __name__ == "__main__":
    rename_gemini_to_openai_prompt()
