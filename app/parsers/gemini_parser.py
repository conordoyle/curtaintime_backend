"""
Gemini AI parser for converting theatre markdown to structured show data.
"""
import os
import json
import logging
import re
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from dateutil import parser as date_parser

try:
    import google.generativeai as genai
except ImportError:
    genai = None

from ..models.database import Show, SessionLocal

# Configure logging
logger = logging.getLogger(__name__)


class ShowData(BaseException):
    """Structured data for a single show."""
    def __init__(self, title: str, start_datetime: datetime, description: Optional[str] = None,
                 image_url: Optional[str] = None, ticket_url: Optional[str] = None,
                 raw_data: Optional[Dict[str, Any]] = None):
        self.title = title
        self.start_datetime = start_datetime
        self.description = description
        self.image_url = image_url
        self.ticket_url = ticket_url
        self.raw_data = raw_data or {}


class GeminiParser:
    """AI-powered parser that converts theatre markdown to structured show data."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Gemini parser.

        Args:
            api_key: Gemini API key (optional, can be loaded from env)
        """
        if genai is None:
            raise ImportError("google-generativeai package is required for GeminiParser")

        api_key = api_key or os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY is required for GeminiParser")

        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash')

    def parse_theatre_markdown(self, markdown: str, theatre_name: str, scrape_log_id: Optional[int] = None) -> List[ShowData]:
        """
        Parse theatre markdown into structured show data using Gemini AI.

        Args:
            markdown: Raw markdown content from Firecrawl
            theatre_name: Name of the theatre for context
            scrape_log_id: Optional scrape log ID to store the prompt

        Returns:
            List[ShowData]: List of parsed shows
        """
        if not markdown or not markdown.strip():
            logger.warning(f"No markdown content to parse for {theatre_name}")
            return []

        # Create the parsing prompt
        prompt = self._create_parsing_prompt(markdown, theatre_name)

        # Store the prompt in the scrape log if provided
        if scrape_log_id:
            try:
                db = SessionLocal()
                from ..models.database import ScrapeLog
                scrape_log = db.query(ScrapeLog).filter(ScrapeLog.id == scrape_log_id).first()
                if scrape_log:
                    scrape_log.gemini_prompt = prompt
                    db.commit()
                    logger.debug(f"Stored Gemini prompt for scrape log {scrape_log_id}")
                db.close()
            except Exception as e:
                logger.warning(f"Failed to store Gemini prompt for scrape log {scrape_log_id}: {str(e)}")
                if 'db' in locals():
                    db.close()

        try:
            logger.info(f"Sending {len(markdown)} chars of markdown to Gemini for {theatre_name}")

            # Generate response from Gemini
            response = self.model.generate_content(prompt)

            if not response or not response.text:
                logger.error(f"No response from Gemini for {theatre_name}")
                return []

            # Extract JSON from response
            json_data = self._extract_json_from_response(response.text)

            if not json_data:
                logger.error(f"Failed to extract JSON from Gemini response for {theatre_name}")
                return []

            # Parse the JSON data into ShowData objects
            shows = self._parse_json_to_shows(json_data, theatre_name)

            logger.info(f"Successfully parsed {len(shows)} shows from {theatre_name}")
            return shows

        except Exception as e:
            logger.error(f"Error parsing markdown for {theatre_name}: {str(e)}")
            return []

    def _create_parsing_prompt(self, markdown: str, theatre_name: str) -> str:
        """Create the prompt for Gemini to parse the theatre markdown."""

        prompt = f"""
You are an expert at parsing theatre and concert venue websites to extract show information.

Please analyze the following markdown content from {theatre_name} and extract all upcoming shows/events.

For each show, extract:
- title: The full name/title of the show or performance
- date: The date of the show (in YYYY-MM-DD format if possible)
- time: The start time of the show (in HH:MM format if available)
- description: A brief description of the show (if available)
- image_url: URL to the show's poster/image (if available)
- ticket_url: URL to purchase tickets (if available)

IMPORTANT:
1. Return ONLY a valid JSON array of show objects
2. Normalize all dates to YYYY-MM-DD format
3. Normalize times to HH:MM 24-hour format
4. If date or time is ambiguous, use your best judgment
5. Only include shows with clear dates (ignore "TBD" or "TBA")
6. If multiple performances of the same show, list each separately
7. Combine date and time into a single datetime field when both are available

Expected JSON format:
[
  {{
    "title": "Show Title",
    "date": "2024-12-25",
    "time": "19:30",
    "description": "Show description here",
    "image_url": "https://example.com/image.jpg",
    "ticket_url": "https://example.com/tickets"
  }},
  ...
]

Markdown content:
{markdown}
"""

        return prompt

    def _extract_json_from_response(self, response_text: str) -> Optional[List[Dict[str, Any]]]:
        """Extract JSON array from Gemini's response text."""
        try:
            # First, try to parse the entire response as JSON
            return json.loads(response_text.strip())
        except json.JSONDecodeError:
            pass

        # Look for JSON array in the response
        json_pattern = r'\[[\s\S]*?\]'
        matches = re.findall(json_pattern, response_text)

        for match in matches:
            try:
                return json.loads(match)
            except json.JSONDecodeError:
                continue

        # Try to find JSON object if array not found
        json_pattern = r'\{[\s\S]*?\}'
        matches = re.findall(json_pattern, response_text)

        for match in matches:
            try:
                data = json.loads(match)
                # If it's a single object, wrap it in a list
                if isinstance(data, dict):
                    return [data]
                elif isinstance(data, list):
                    return data
            except json.JSONDecodeError:
                continue

        logger.error(f"Could not extract valid JSON from response: {response_text[:200]}...")
        return None

    def _parse_json_to_shows(self, json_data: List[Dict[str, Any]], theatre_name: str) -> List[ShowData]:
        """Parse JSON data into ShowData objects."""
        shows = []

        for item in json_data:
            try:
                show = self._parse_single_show(item)
                if show:
                    shows.append(show)
            except Exception as e:
                logger.warning(f"Failed to parse show item: {item}. Error: {str(e)}")

        return shows

    def _parse_single_show(self, item: Dict[str, Any]) -> Optional[ShowData]:
        """Parse a single show item from the JSON data."""
        try:
            title = item.get('title', '').strip()
            if not title:
                return None

            # Parse date and time
            date_str = item.get('date', '')
            time_str = item.get('time', '')

            if not date_str:
                logger.warning(f"No date found for show: {title}")
                return None

            # Combine date and time
            datetime_str = date_str
            if time_str:
                datetime_str += f" {time_str}"

            try:
                # Parse the datetime
                parsed_datetime = date_parser.parse(datetime_str)

                # Ensure it's timezone-aware (assume local time if not specified)
                if parsed_datetime.tzinfo is None:
                    parsed_datetime = parsed_datetime.replace(tzinfo=timezone.utc)
                else:
                    parsed_datetime = parsed_datetime.astimezone(timezone.utc)

            except Exception as e:
                logger.warning(f"Failed to parse datetime '{datetime_str}' for show '{title}': {str(e)}")
                return None

            # Extract other fields
            description = item.get('description')
            description = description.strip() if description else None

            image_url = item.get('image_url')
            image_url = image_url.strip() if image_url else None

            ticket_url = item.get('ticket_url')
            ticket_url = ticket_url.strip() if ticket_url else None

            # Validate URLs
            if image_url and not image_url.startswith(('http://', 'https://')):
                image_url = None
            if ticket_url and not ticket_url.startswith(('http://', 'https://')):
                ticket_url = None

            return ShowData(
                title=title,
                start_datetime=parsed_datetime,
                description=description,
                image_url=image_url,
                ticket_url=ticket_url,
                raw_data=item
            )

        except Exception as e:
            logger.error(f"Error parsing show item {item}: {str(e)}")
            return None

    def validate_show_data(self, shows: List[ShowData]) -> List[ShowData]:
        """Validate and clean the parsed show data."""
        valid_shows = []

        for show in shows:
            if not show.title or not show.start_datetime:
                continue

            # Ensure datetime is in the future (with some buffer)
            now = datetime.now(timezone.utc)
            if show.start_datetime < now:
                logger.info(f"Skipping past show: {show.title} at {show.start_datetime}")
                continue

            # Basic validation
            if len(show.title.strip()) < 3:
                continue

            valid_shows.append(show)

        return valid_shows

    @classmethod
    def from_env(cls) -> 'GeminiParser':
        """Create parser instance from environment variables."""
        api_key = os.getenv('GEMINI_API_KEY')
        return cls(api_key=api_key)


