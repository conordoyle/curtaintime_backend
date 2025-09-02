#!/usr/bin/env python3
"""
Test Firecrawl scraping functionality
"""
import os

def test_firecrawl_scraping():
    """Test Firecrawl with a simple webpage."""
    print("🔥 Testing Firecrawl Scraping...")

    try:
        from firecrawl import Firecrawl

        api_key = os.getenv('FIRECRAWL_API_KEY')
        if not api_key:
            print("❌ FIRECRAWL_API_KEY not set!")
            return

        fc = Firecrawl(api_key=api_key)

        # Test with a simple webpage
        test_url = "https://httpbin.org/html"
        print(f"   Scraping: {test_url}")

        result = fc.scrape(test_url, formats=['markdown'])

        if hasattr(result, 'markdown') and result.markdown:
            print("✅ Firecrawl works!")
            print(f"   Got {len(result.markdown)} characters")
            print(f"   Preview: {result.markdown[:200]}...")
            return True
        else:
            print("❌ No markdown returned")
            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    test_firecrawl_scraping()
