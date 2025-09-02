#!/usr/bin/env python3
"""
Test Vercel Blob Storage functionality
"""
from dotenv import load_dotenv
load_dotenv()

from app.services.vercel_blob import VercelBlobService

def test_blob_service():
    """Test the Vercel Blob service."""
    print("🗄️ Testing Vercel Blob Service...")

    try:
        blob = VercelBlobService.from_env()
        print("✅ Blob service initialized!")

        # Test with a simple text file
        test_content = b"This is a test file for CurtainTime blob storage!"
        test_path = "curtaintime/test/test_file.txt"

        print(f"   Uploading test file to: {test_path}")

        result_url = blob.upload(test_content, test_path, "text/plain")

        print("✅ File uploaded successfully!")
        print(f"   URL: {result_url}")

        return True

    except Exception as e:
        print(f"❌ Blob test failed: {e}")
        return False

if __name__ == "__main__":
    test_blob_service()
