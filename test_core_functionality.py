#!/usr/bin/env python3
"""
Test script for core scraping and parsing functionality.
Tests Firecrawl scraping and Gemini AI parsing without requiring database setup.
"""
import os
import sys
import json
from pathlib import Path

# Add current directory to path
sys.path.insert(0, '.')

def test_firecrawl_scraping():
    """Test Firecrawl scraping functionality."""
    print("\n🔥 Testing Firecrawl Scraping...")

    try:
        # Import the scraper (without database dependency)
        from app.scrapers.theatre_scraper import TheatreScraper

        # Check if API key is available
        api_key = os.getenv('FIRECRAWL_API_KEY')
        if not api_key:
            print("⚠️  FIRECRAWL_API_KEY not found in environment")
            print("   Skipping Firecrawl test - set API key to test scraping")
            return False

        # Create scraper instance
        scraper = TheatreScraper(api_key)

        # Test with a simple URL
        test_url = "https://example.com"
        print(f"   Testing scrape of: {test_url}")

        result = scraper._scrape_single_url(test_url, {'formats': ['markdown']})

        if 'markdown' in result:
            print("✅ Firecrawl scraping works!")
            print(f"   Scraped {len(result['markdown'])} characters")
            return True
        else:
            print("❌ Firecrawl scraping failed")
            return False

    except Exception as e:
        print(f"❌ Firecrawl test failed: {e}")
        return False


def test_openai_parsing():
    """Test OpenAI parsing functionality."""
    print("\n🤖 Testing OpenAI Parsing...")

    try:
        # Import the parser
        from app.parsers.openai_parser import OpenAIParser

        # Check if API key is available
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            print("⚠️  OPENAI_API_KEY not found in environment")
            print("   Skipping Gemini test - set API key to test parsing")
            return False

        # Create parser instance
        parser = OpenAIParser(api_key)

        # Test with sample markdown
        sample_markdown = """
# Test Theatre Shows

## Show 1: Hamilton
**Date:** December 25, 2024
**Time:** 8:00 PM
**Description:** The revolutionary musical about Alexander Hamilton

## Show 2: Wicked
**Date:** December 26, 2024
**Time:** 7:30 PM
**Description:** The untold story of the Witches of Oz
"""

        print(f"   Testing parsing of {len(sample_markdown)} characters")

        shows = parser.parse_theatre_markdown(sample_markdown, "Test Theatre")

        if shows and len(shows) > 0:
            print("✅ Gemini AI parsing works!")
            print(f"   Parsed {len(shows)} shows:")
            for show in shows[:2]:  # Show first 2
                print(f"   - {show.title}: {show.start_datetime}")
            return True
        else:
            print("❌ Gemini AI parsing failed - no shows parsed")
            return False

    except Exception as e:
        print(f"❌ Gemini test failed: {e}")
        return False


def test_config_loading():
    """Test loading theatre configurations from existing scraper."""
    print("\n📁 Testing Configuration Loading...")

    try:
        # Path to existing theatre scraper configs
        config_dir = Path("../theatre_scraper/configs")

        if not config_dir.exists():
            print("❌ Theatre scraper configs directory not found")
            print(f"   Expected: {config_dir.absolute()}")
            return False

        json_files = list(config_dir.glob("*.json"))
        if not json_files:
            print("❌ No JSON config files found in theatre_scraper/configs/")
            return False

        print(f"✅ Found {len(json_files)} theatre configurations:")

        # Load and validate first config
        with open(json_files[0], 'r') as f:
            config = json.load(f)

        required_fields = ['theatre_id', 'theatre_name', 'base_url']
        missing_fields = [field for field in required_fields if field not in config]

        if missing_fields:
            print(f"❌ Config missing required fields: {missing_fields}")
            return False

        print(f"   ✅ {config['theatre_id']}: {config['theatre_name']}")
        print("✅ Configuration loading works!")
        return True

    except Exception as e:
        print(f"❌ Config loading test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("🎭 CurtainTime Backend - Core Functionality Tests")
    print("=" * 60)

    # Check environment
    print("\n🔧 Environment Check:")
    print(f"   Python: {sys.version}")
    print(f"   Current directory: {Path.cwd()}")

    # Run tests
    tests = [
        ("Configuration Loading", test_config_loading),
        ("Firecrawl Scraping", test_firecrawl_scraping),
        ("OpenAI Parsing", test_openai_parsing),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} crashed: {e}")
            results.append((test_name, False))

    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST RESULTS:")

    passed = 0
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {status} {test_name}")
        if result:
            passed += 1

    print(f"\n🎯 Overall: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All systems ready! You can start testing scraping and parsing!")
        print("\n💡 Next steps:")
        print("   1. Set up environment variables (.env file)")
        print("   2. Run: python scripts/init_db.py")
        print("   3. Test with: python -m app.api.main")
    else:
        print("\n⚠️  Some tests failed. Check the output above for details.")
        print("   You may need to:")
        print("   - Install dependencies: pip install -r requirements.txt")
        print("   - Set environment variables")
        print("   - Check API keys")


if __name__ == "__main__":
    main()
