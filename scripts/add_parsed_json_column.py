#!/usr/bin/env python3
"""
Database migration script to add the parsed_json column to scrape_logs table.
This script adds the new column without affecting existing data.
"""
import sys
from pathlib import Path

# Add the app directory to the Python path
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from app.models.database import ScrapeLog

def add_parsed_json_column():
    """Add the parsed_json column to the scrape_logs table."""
    # Import database URL from environment
    import os
    from dotenv import load_dotenv
    load_dotenv()

    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL not found in environment variables")
        return False

    # Create engine
    engine = create_engine(database_url)

    try:
        # Check if column exists
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.columns
                    WHERE table_name = 'scrape_logs'
                    AND column_name = 'parsed_json'
                );
            """))
            column_exists = result.fetchone()[0]

            if column_exists:
                print("✅ parsed_json column already exists")
                return True

            # Add the column
            print("🔧 Adding parsed_json column to scrape_logs table...")
            alter_sql = """
            ALTER TABLE scrape_logs
            ADD COLUMN parsed_json JSON;
            """

            conn.execute(text(alter_sql))
            conn.commit()

            print("✅ parsed_json column added successfully!")
            return True

    except Exception as e:
        print(f"❌ Error adding column: {e}")
        return False

def main():
    """Main migration function."""
    print("🗃️  Database Migration: Add parsed_json column to scrape_logs")
    print("=" * 60)

    success = add_parsed_json_column()

    if success:
        print("\n✅ Migration completed successfully!")
        print("\nYou can now access: http://localhost:8000/dashboard/scraping")
        print("The logging functionality should now work!")
    else:
        print("\n❌ Migration failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
