#!/usr/bin/env python3
"""
Database migration script to add the scheduled_scrapes table.
This script adds the new table without affecting existing data.
"""
import sys
from pathlib import Path

# Add the app directory to the Python path
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from app.models.database import ScheduledScrape

def create_scheduled_scrapes_table():
    """Create the scheduled_scrapes table if it doesn't exist."""
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
        # Check if table exists
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'scheduled_scrapes'
                );
            """))
            table_exists = result.fetchone()[0]

            if table_exists:
                print("✅ scheduled_scrapes table already exists")
                return True

            # Create the table using SQLAlchemy's create_all
            from sqlalchemy import MetaData
            metadata = MetaData()

            # Define the table structure manually to ensure it matches our model
            create_table_sql = """
            CREATE TABLE scheduled_scrapes (
                id SERIAL PRIMARY KEY,
                theatre_id VARCHAR NOT NULL REFERENCES theatres(id),
                enabled BOOLEAN DEFAULT TRUE,
                schedule_type VARCHAR DEFAULT 'daily',
                schedule_config JSON,
                last_run TIMESTAMP WITH TIME ZONE,
                next_run TIMESTAMP WITH TIME ZONE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
            """

            print("🔧 Creating scheduled_scrapes table...")
            conn.execute(text(create_table_sql))
            conn.commit()

            print("✅ scheduled_scrapes table created successfully!")
            return True

    except Exception as e:
        print(f"❌ Error creating table: {e}")
        return False

def main():
    """Main migration function."""
    print("🗃️  Database Migration: Add scheduled_scrapes table")
    print("=" * 50)

    success = create_scheduled_scrapes_table()

    if success:
        print("\n✅ Migration completed successfully!")
        print("\nYou can now access: http://localhost:8000/dashboard/schedules")
    else:
        print("\n❌ Migration failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
