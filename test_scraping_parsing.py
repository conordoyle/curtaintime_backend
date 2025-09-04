#!/usr/bin/env python3
"""
Standalone test for Firecrawl scraping and Gemini AI parsing.
Tests core functionality without database dependencies.
"""
import os
import sys

def test_firecrawl_direct():
    """Test Firecrawl scraping directly."""
    print("\n🔥 Testing Firecrawl Scraping...")

    try:
        from firecrawl import Firecrawl

        api_key = os.getenv('FIRECRAWL_API_KEY')
        if not api_key:
            print("⚠️  FIRECRAWL_API_KEY not set")
            print("   Set it to test scraping: export FIRECRAWL_API_KEY=your-key")
            return False

        fc = Firecrawl(api_key=api_key)

        # Test with a simple webpage
        test_url = "https://httpbin.org/html"  # Simple HTML page for testing
        print(f"   Scraping: {test_url}")

        result = fc.scrape(test_url, formats=['markdown'])

        if hasattr(result, 'markdown') and result.markdown:
            print("✅ Firecrawl scraping works!")
            print(f"   Got {len(result.markdown)} characters of markdown")
            return True
        else:
            print("❌ Firecrawl returned no markdown")
            return False

    except Exception as e:
        print(f"❌ Firecrawl test failed: {e}")
        return False


def test_openai_direct():
    """Test OpenAI parsing directly."""
    print("\n🤖 Testing OpenAI Parsing...")

    try:
        from openai import OpenAI

        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            print("⚠️  OPENAI_API_KEY not set")
            print("   Set it to test parsing: export OPENAI_API_KEY=your-key")
            return False

        client = OpenAI(api_key=api_key)

        # Test prompt
        prompt = """
Parse this theatre show information into JSON:

Show: Hamilton
Date: December 25, 2024
Time: 8:00 PM
Description: The revolutionary musical

Return only valid JSON with fields: title, date, time, description
"""

        print("   Sending test prompt to OpenAI...")

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=1000,
            response_format={"type": "json_object"}
        )

        if response and response.choices:
            print("✅ OpenAI works!")
            print(f"   Response: {response.choices[0].message.content[:100]}...")
            return True
        else:
            print("❌ OpenAI returned no response")
            return False

    except ImportError:
        print("❌ openai not installed")
        print("   Install with: pip install openai")
        return False
    except Exception as e:
        print(f"❌ OpenAI test failed: {e}")
        return False


def test_dependencies():
    """Test if required dependencies are installed."""
    print("\n📦 Testing Dependencies...")

    dependencies = [
        ('firecrawl', 'Firecrawl scraping'),
        ('google.generativeai', 'Gemini AI parsing'),
        ('pydantic', 'Data validation'),
        ('sqlalchemy', 'Database ORM'),
    ]

    all_good = True

    for module, purpose in dependencies:
        try:
            __import__(module)
            print(f"   ✅ {module} - {purpose}")
        except ImportError:
            print(f"   ❌ {module} - {purpose} (missing)")
            all_good = False

    return all_good


def main():
    """Run all tests."""
    print("🎭 CurtainTime Core Functionality Test")
    print("=" * 50)

    print("\n🔧 Environment Setup:")
    print("   To test fully, set these environment variables:")
    print("   export FIRECRAWL_API_KEY=your-firecrawl-key")
    print("   export OPENAI_API_KEY=your-openai-key")
    print("   export DATABASE_URL=postgresql://...  # Optional for full system")

    # Test dependencies first
    deps_ok = test_dependencies()

    if not deps_ok:
        print("\n❌ Dependencies missing!")
        print("   Install with: pip install -r requirements.txt")
        return

    # Test core functionality
    tests = [
        ("Firecrawl Scraping", test_firecrawl_direct),
        ("OpenAI Parsing", test_openai_direct),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = test_firecrawl_direct()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} crashed: {e}")
            results.append((test_name, False))

    # Summary
    print("\n" + "=" * 50)
    print("📊 RESULTS:")

    passed = sum(1 for _, result in results if result)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL/SKIP"
        print(f"   {status} {test_name}")

    print(f"\n🎯 Core functionality: {passed}/2 tests working")

    if passed == 2:
        print("\n🎉 Everything works! Ready to test scraping & parsing!")
        print("\n🚀 Quick test commands:")
        print("   # Test scraping a theatre:")
        print("   python -c \"from app.scrapers.theatre_scraper import TheatreScraper; print('Scraper ready!')\"")
        print("   ")
        print("   # Test AI parsing:")
        print("   python -c \"from app.parsers.openai_parser import OpenAIParser; print('Parser ready!')\"")
    elif passed == 1:
        print("\n⚠️  Partial success - check API keys for failed tests")
    else:
        print("\n❌ Need API keys to test scraping and parsing")

    print("\n💡 To run full system:")
    print("   1. Set DATABASE_URL for PostgreSQL")
    print("   2. Run: python scripts/init_db.py")
    print("   3. Start: python -m app.api.main")


if __name__ == "__main__":
    main()
