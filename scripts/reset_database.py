"""
Script to completely reset the database - drops all tables and recreates them.
WARNING: This will delete ALL data including theatres, shows, and scrape logs!
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.database import reset_db

def main():
    print("⚠️  WARNING: This will DELETE ALL database data!")
    print("   - All theatres")
    print("   - All shows") 
    print("   - All scrape logs")
    print("   - All scheduled scrapes")
    print()
    
    confirm = input("Are you sure you want to proceed? Type 'YES' to confirm: ")
    
    if confirm == "YES":
        print("🗑️  Resetting database...")
        try:
            reset_db()
            print("✅ Database has been completely reset!")
            print("   - All tables dropped and recreated")
            print("   - Ready for fresh data")
        except Exception as e:
            print(f"❌ Error resetting database: {e}")
    else:
        print("❌ Database reset cancelled.")

if __name__ == "__main__":
    main()
