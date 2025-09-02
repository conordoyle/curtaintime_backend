#!/usr/bin/env python3
"""
Test Gemini AI parsing functionality
"""
import os

def test_gemini_parsing():
    """Test Gemini AI with sample theatre markdown."""
    print("🤖 Testing Gemini AI Parsing...")

    try:
        import google.generativeai as genai

        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            print("❌ GEMINI_API_KEY not set!")
            return

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')

        # Sample theatre markdown
        sample_markdown = """
# Music Hall Shows

## Show 1: Hamilton
**Date:** December 25, 2024
**Time:** 8:00 PM
**Description:** The revolutionary musical about Alexander Hamilton

## Show 2: Wicked
**Date:** December 26, 2024
**Time:** 7:30 PM
**Description:** The untold story of the Witches of Oz
"""

        prompt = f"""
Parse this theatre show information into JSON format:

{sample_markdown}

Return only a valid JSON array with these fields for each show:
- title: The show name
- date: Date in YYYY-MM-DD format
- time: Time in HH:MM format
- description: Brief description

Example format:
[
  {{
    "title": "Show Name",
    "date": "2024-12-25",
    "time": "20:00",
    "description": "Show description"
  }}
]
"""

        print(f"   Sending {len(sample_markdown)} chars to Gemini...")

        response = model.generate_content(prompt)

        if response and response.text:
            print("✅ Gemini AI works!")
            print(f"   Response: {response.text[:300]}...")
            return True
        else:
            print("❌ No response from Gemini")
            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    test_gemini_parsing()
