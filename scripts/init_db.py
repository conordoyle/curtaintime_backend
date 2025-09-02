#!/usr/bin/env python3
"""
Database initialization script for CurtainTime backend.
Creates tables and imports theatre configurations from the existing scraper system.
"""
import sys
import os
import json
from pathlib import Path

# Add the app directory to the Python path
sys.path.append(str(Path(__file__).parent.parent))

from app.models.database import init_db, Theatre, SessionLocal

# Path to the existing theatre scraper configurations
THEATRE_SCRAPER_CONFIGS = Path(__file__).parent.parent.parent / "theatre_scraper" / "configs"


def load_theatre_configs():
    """Load theatre configurations from the existing scraper system."""
    configs = {}

    if not THEATRE_SCRAPER_CONFIGS.exists():
        print(f"Warning: Theatre scraper configs directory not found: {THEATRE_SCRAPER_CONFIGS}")
        return configs

    for config_file in THEATRE_SCRAPER_CONFIGS.glob("*.json"):
        theatre_id = config_file.stem  # Remove .json extension

        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)

            configs[theatre_id] = config_data
            print(f"Loaded config for theatre: {theatre_id}")

        except Exception as e:
            print(f"Error loading config for {theatre_id}: {e}")

    return configs


def import_theatres_to_db(theatre_configs):
    """Import theatre configurations into the database."""
    db = SessionLocal()

    try:
        imported_count = 0

        for theatre_id, config_data in theatre_configs.items():
            # Check if theatre already exists
            existing_theatre = db.query(Theatre).filter(Theatre.id == theatre_id).first()

            if existing_theatre:
                print(f"Theatre {theatre_id} already exists, updating...")
                existing_theatre.name = config_data.get('theatre_name', theatre_id)
                existing_theatre.base_url = config_data.get('base_url', '')
                existing_theatre.config_data = config_data
                existing_theatre.enabled = config_data.get('enabled', True)
            else:
                # Create new theatre
                theatre = Theatre(
                    id=theatre_id,
                    name=config_data.get('theatre_name', theatre_id),
                    base_url=config_data.get('base_url', ''),
                    config_data=config_data,
                    enabled=config_data.get('enabled', True)
                )
                db.add(theatre)
                imported_count += 1

        db.commit()
        print(f"Successfully imported {imported_count} theatres to database")

        # Print summary
        total_theatres = db.query(Theatre).count()
        enabled_theatres = db.query(Theatre).filter(Theatre.enabled == True).count()
        print(f"Total theatres in database: {total_theatres}")
        print(f"Enabled theatres: {enabled_theatres}")

    except Exception as e:
        db.rollback()
        print(f"Error importing theatres: {e}")
        raise
    finally:
        db.close()


def main():
    """Main initialization function."""
    print("🎭 CurtainTime Database Initialization")
    print("=" * 50)

    # Step 1: Initialize database tables
    print("\n1. Creating database tables...")
    try:
        init_db()
        print("✅ Database tables created successfully!")
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        return 1

    # Step 2: Load theatre configurations
    print("\n2. Loading theatre configurations...")
    theatre_configs = load_theatre_configs()
    if not theatre_configs:
        print("❌ No theatre configurations found!")
        return 1

    print(f"✅ Loaded {len(theatre_configs)} theatre configurations")

    # Step 3: Import theatres to database
    print("\n3. Importing theatres to database...")
    try:
        import_theatres_to_db(theatre_configs)
        print("✅ Theatre configurations imported successfully!")
    except Exception as e:
        print(f"❌ Error importing theatres: {e}")
        return 1

    print("\n🎉 Database initialization completed successfully!")
    print("\nNext steps:")
    print("- Set up your environment variables (.env file)")
    print("- Run the development server: python -m app.api.main")
    print("- Or start Celery worker: celery -A app.celery_app worker --loglevel=info")

    return 0


if __name__ == "__main__":
    sys.exit(main())
