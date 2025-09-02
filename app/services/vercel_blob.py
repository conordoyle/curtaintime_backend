"""
Vercel Blob Storage service for image upload and management.
Handles downloading, optimizing, and uploading show images.
"""
import os
import requests
import logging
from io import BytesIO
from typing import Optional, Dict, Any
from urllib.parse import urlparse

try:
    from PIL import Image
except ImportError:
    Image = None

# Configure logging
logger = logging.getLogger(__name__)


class VercelBlobService:
    """Service for uploading images to Vercel Blob Storage."""

    def __init__(self, token: Optional[str] = None):
        """
        Initialize the Vercel Blob service.

        Args:
            token: Vercel Blob read/write token
        """
        self.token = token or os.getenv('BLOB_READ_WRITE_TOKEN')
        if not self.token:
            raise ValueError("BLOB_READ_WRITE_TOKEN is required for VercelBlobService")

        self.base_url = "https://blob.vercel-storage.com"

    def upload(self, file_data: bytes, pathname: str, content_type: str = "image/jpeg") -> str:
        """
        Upload file data to Vercel Blob Storage.

        Args:
            file_data: Raw file bytes
            pathname: Path/name for the file in storage
            content_type: MIME type of the file

        Returns:
            str: Public URL of the uploaded file

        Raises:
            Exception: If upload fails
        """
        url = f"{self.base_url}/{pathname}"

        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": content_type,
            "x-amz-meta-name": pathname,
        }

        try:
            logger.info(f"Uploading {len(file_data)} bytes to Vercel Blob: {pathname}")

            response = requests.put(url, data=file_data, headers=headers)

            if response.status_code == 200:
                # Parse the response to get the actual public URL
                try:
                    response_data = response.json()
                    public_url = response_data.get('url')
                    if public_url:
                        logger.info(f"Successfully uploaded image: {pathname} -> {public_url}")
                        return public_url
                    else:
                        logger.warning(f"Upload succeeded but no URL returned: {response_data}")
                        return url
                except Exception as parse_error:
                    logger.warning(f"Could not parse upload response: {parse_error}")
                    return url
            else:
                raise Exception(f"Upload failed with status {response.status_code}: {response.text}")

        except Exception as e:
            logger.error(f"Failed to upload to Vercel Blob: {str(e)}")
            raise

    def download_and_optimize_image(self, image_url: str, max_width: int = 800,
                                   max_height: int = 600, quality: int = 85) -> Optional[bytes]:
        """
        Download an image from URL and optimize it for web.

        Args:
            image_url: URL of the image to download
            max_width: Maximum width in pixels
            max_height: Maximum height in pixels
            quality: JPEG quality (1-100)

        Returns:
            Optional[bytes]: Optimized image data, or None if failed
        """
        if not Image:
            logger.warning("PIL not available, skipping image optimization")
            return None

        try:
            logger.info(f"Downloading and optimizing image: {image_url}")

            # Download the image
            response = requests.get(image_url, timeout=30)
            response.raise_for_status()

            # Open with PIL
            image = Image.open(BytesIO(response.content))

            # Convert to RGB if necessary (for JPEG)
            if image.mode in ('RGBA', 'LA', 'P'):
                image = image.convert('RGB')

            # Resize if too large
            if image.width > max_width or image.height > max_height:
                image.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)

            # Save optimized version
            output = BytesIO()
            image.save(output, format='JPEG', quality=quality, optimize=True)
            optimized_data = output.getvalue()

            logger.info(f"Optimized image from {len(response.content)} to {len(optimized_data)} bytes")
            return optimized_data

        except Exception as e:
            logger.error(f"Failed to download/optimize image {image_url}: {str(e)}")
            return None

    def generate_pathname(self, show_id: int, original_url: str) -> str:
        """
        Generate a unique pathname for an image in blob storage.

        Args:
            show_id: Database ID of the show
            original_url: Original image URL

        Returns:
            str: Unique pathname for blob storage
        """
        # Extract filename from original URL
        parsed_url = urlparse(original_url)
        filename = os.path.basename(parsed_url.path)

        # Remove query parameters and extension
        name_without_ext = os.path.splitext(filename)[0]

        # Clean the name and create unique path
        clean_name = "".join(c for c in name_without_ext if c.isalnum() or c in ('-', '_')).rstrip()
        if not clean_name:
            clean_name = f"show_{show_id}"

        pathname = f"curtaintime/shows/{show_id}/{clean_name}.jpg"

        return pathname

    def process_and_upload_image(self, show_id: int, image_url: str) -> Optional[str]:
        """
        Complete pipeline: download, optimize, and upload an image.

        Args:
            show_id: Database ID of the show
            image_url: URL of the image to process

        Returns:
            Optional[str]: Blob URL if successful, None if failed
        """
        try:
            # Generate unique pathname
            pathname = self.generate_pathname(show_id, image_url)

            # Download and optimize
            optimized_data = self.download_and_optimize_image(image_url)

            if not optimized_data:
                logger.warning(f"Could not optimize image for show {show_id}, uploading original")
                # Fall back to original image data
                response = requests.get(image_url, timeout=30)
                response.raise_for_status()
                optimized_data = response.content

            # Upload to blob storage
            blob_url = self.upload(optimized_data, pathname, "image/jpeg")

            logger.info(f"Successfully processed and uploaded image for show {show_id}: {blob_url}")
            return blob_url

        except Exception as e:
            logger.error(f"Failed to process and upload image for show {show_id}: {str(e)}")
            return None

    @classmethod
    def from_env(cls) -> 'VercelBlobService':
        """Create service instance from environment variables."""
        token = os.getenv('BLOB_READ_WRITE_TOKEN')
        return cls(token=token)
