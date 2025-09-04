#!/usr/bin/env python3
"""
Test OpenAI parsing functionality
"""
import os

def test_openai_parsing():
    """Test OpenAI with sample theatre markdown."""
    print("🤖 Testing OpenAI Parsing...")

    try:
        from openai import OpenAI

        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            print("❌ OPENAI_API_KEY not set!")
            return

        client = OpenAI(api_key=api_key)

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

        print(f"   Sending {len(sample_markdown)} chars to OpenAI...")

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
            print(f"   Response: {response.choices[0].message.content[:300]}...")
            return True
        else:
            print("❌ No response from OpenAI")
            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    test_openai_parsing()
