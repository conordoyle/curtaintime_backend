#!/usr/bin/env python3
"""
Test the full theatre scraping pipeline
"""
import os
import json

def test_theatre_scraping():
    """Test scraping a theatre using our TheatreScraper."""
    print("🎭 Testing Theatre Scraping Pipeline...")

    try:
        from app.scrapers.theatre_scraper import TheatreScraper

        # Load a theatre config from the existing scraper
        config_path = "../theatre_scraper/configs/music_hall.json"

        if not os.path.exists(config_path):
            print(f"❌ Config file not found: {config_path}")
            return

        with open(config_path, 'r') as f:
            config_data = json.load(f)

        print(f"   Testing theatre: {config_data['theatre_name']}")
        print(f"   URL: {config_data['base_url']}")

        # Create scraper and test
        scraper = TheatreScraper.from_env()

        # Test with a simple example URL first
        test_url = "https://httpbin.org/html"
        print(f"   Testing scrape of: {test_url}")

        result = scraper._scrape_single_url(test_url, {'formats': ['markdown']})

        if 'markdown' in result and result['markdown']:
            print("✅ Theatre scraper works!")
            print(f"   Got {len(result['markdown'])} characters")
            return True
        else:
            print("❌ No markdown content")
            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_ai_parsing_pipeline():
    """Test the AI parsing with sample data."""
    print("\n🧠 Testing AI Parsing Pipeline...")

    try:
        from app.parsers.gemini_parser import GeminiParser

        # Sample markdown for testing
        sample_markdown = """
# Test Theatre Shows

## Hamilton
Date: December 25, 2024
Time: 8:00 PM
Description: The revolutionary musical

## Wicked
Date: December 26, 2024
Time: 7:30 PM
Description: The untold story of the Witches of Oz
"""

        parser = GeminiParser.from_env()
        shows = parser.parse_theatre_markdown(sample_markdown, "Test Theatre")

        if shows and len(shows) > 0:
            print("✅ AI parsing works!")
            print(f"   Parsed {len(shows)} shows:")
            for show in shows[:2]:
                print(f"   - {show.title}: {show.start_datetime}")
            return True
        else:
            print("❌ AI parsing failed")
            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    # Test individual components
    scrape_ok = test_theatre_scraping()
    parse_ok = test_ai_parsing_pipeline()

    print(f"\n📊 Results:")
    print(f"   Scraping: {'✅' if scrape_ok else '❌'}")
    print(f"   AI Parsing: {'✅' if parse_ok else '❌'}")

    if scrape_ok and parse_ok:
        print("\n🎉 Full pipeline ready!")
    else:
        print("\n⚠️  Some components need attention")
