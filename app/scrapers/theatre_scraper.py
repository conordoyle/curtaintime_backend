"""
Theatre scraping service for CurtainTime backend.
Adapts existing scraper logic to work with database models and new architecture.
"""
import os
import time
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Union
from firecrawl import Firecrawl
from pydantic import BaseModel

from ..models.database import Theatre, ScrapeLog, SessionLocal

# Configure logging
logger = logging.getLogger(__name__)


class ScrapingResult(BaseModel):
    """Result from a scraping operation."""
    theatre_id: str
    theatre_name: str
    urls_scraped: List[str]
    pages_scraped: int
    successful_pages: int
    markdown_content: str  # Combined markdown from all pages
    errors: List[str]
    scrape_duration: float
    metadata: Dict[str, Any] = {}

    # Change tracking fields
    change_status: Optional[str] = None  # new, same, changed, removed
    previous_scrape_at: Optional[datetime] = None
    page_visibility: Optional[str] = None  # visible, hidden
    change_metadata: Optional[Dict[str, Any]] = None


class TheatreScraper:
    """Enhanced theatre scraping service that integrates with the database."""

    def __init__(self, firecrawl_api_key: str, request_delay: float = 1.0, max_retries: int = 3):
        """
        Initialize the theatre scraper.

        Args:
            firecrawl_api_key: Firecrawl API key
            request_delay: Delay between requests in seconds
            max_retries: Maximum number of retries for failed requests
        """
        self.firecrawl = Firecrawl(api_key=firecrawl_api_key)
        self.request_delay = request_delay
        self.max_retries = max_retries

    def check_page_changes(self, url: str, enable_change_tracking: bool = True) -> Dict[str, Any]:
        """
        Check if a page has changed since the last scrape using Firecrawl Change Tracking.

        Args:
            url: The URL to check for changes
            enable_change_tracking: Whether to enable change tracking

        Returns:
            Dict containing change tracking results
        """
        if not enable_change_tracking:
            return {
                "change_status": "unknown",
                "message": "Change tracking disabled"
            }

        try:
            logger.info(f"Checking for changes on: {url}")

            # Use Firecrawl's change tracking
            response = self.firecrawl.scrape(
                url=url,
                formats=["markdown", "changeTracking"]
            )

            logger.info(f"Firecrawl response type: {type(response)}")
            logger.info(f"Firecrawl response: {response}")

            # Check if change tracking data exists (could be attribute or dict key)
            change_data = None
            if hasattr(response, 'change_tracking'):
                change_data = response.change_tracking
            elif hasattr(response, 'changeTracking'):
                change_data = response.changeTracking
            elif 'change_tracking' in response:
                change_data = response['change_tracking']
            elif 'changeTracking' in response:
                change_data = response['changeTracking']

            if change_data:
                logger.info(f"Change data found: {change_data}")
                change_status = getattr(change_data, 'changeStatus', None) or change_data.get('changeStatus', 'unknown')
                logger.info(f"Change status for {url}: {change_status}")

                return {
                    "change_status": change_status,
                    "previous_scrape_at": getattr(change_data, 'previousScrapeAt', None) or change_data.get('previousScrapeAt'),
                    "page_visibility": getattr(change_data, 'visibility', None) or change_data.get('visibility', 'unknown'),
                    "change_metadata": change_data,
                    "markdown_content": getattr(response, 'markdown', ''),
                    "success": True
                }
            else:
                logger.warning(f"No change tracking data received for {url}")
                return {
                    "change_status": "unknown",
                    "message": "No change tracking data received",
                    "success": False
                }

        except Exception as e:
            logger.error(f"Error checking page changes for {url}: {str(e)}")
            return {
                "change_status": "error",
                "message": f"Error checking changes: {str(e)}",
                "success": False
            }

    def scrape_theatre_by_id(self, theatre_id: str, enable_change_tracking: bool = False) -> ScrapingResult:
        """
        Scrape a theatre by its ID, loading configuration from database.

        Args:
            theatre_id: The theatre identifier
            enable_change_tracking: Whether to check for changes before full scraping

        Returns:
            ScrapingResult: Complete scraping results

        Raises:
            ValueError: If theatre not found or configuration invalid
        """
        # Load theatre configuration from database
        db = SessionLocal()
        try:
            theatre = db.query(Theatre).filter(Theatre.id == theatre_id).first()
            if not theatre:
                raise ValueError(f"Theatre '{theatre_id}' not found in database")

            if not theatre.config_data:
                raise ValueError(f"No configuration data found for theatre '{theatre_id}'")

            config_data = theatre.config_data
            return self.scrape_with_config(theatre, config_data, enable_change_tracking)

        finally:
            db.close()

    def scrape_with_config(self, theatre: Theatre, config_data: Dict[str, Any], enable_change_tracking: bool = False) -> ScrapingResult:
        """
        Scrape a theatre using its configuration data.

        Args:
            theatre: Theatre database model
            config_data: Configuration dictionary
            enable_change_tracking: Whether to check for changes before full scraping

        Returns:
            ScrapingResult: Complete scraping results
        """
        start_time = time.time()
        logger.info(f"Starting scrape for {theatre.name} ({theatre.id})")

        try:
            # Extract strategy and parameters from config
            strategy = config_data.get('scraping_strategy', {})
            strategy_type = strategy.get('type', 'single_url')
            scrape_params = config_data.get('scrape_params', {})

            # Check for changes if enabled
            change_tracking_result = None
            if enable_change_tracking and strategy_type in ['single_url', 'single_url_with_actions']:
                base_url = strategy.get('base_url', theatre.base_url)
                logger.info(f"🔄 Change tracking enabled for {strategy_type}, checking: {base_url}")
                logger.info(f"🎯 enable_change_tracking={enable_change_tracking}, strategy_type={strategy_type}")
                change_tracking_result = self.check_page_changes(base_url, enable_change_tracking)
                logger.info(f"📊 Change tracking result: {change_tracking_result}")

                # If page hasn't changed, return early with change status
                if change_tracking_result.get('change_status') == 'same':
                    logger.info(f"Page unchanged for {theatre.name}, skipping full scrape")
                    return ScrapingResult(
                        theatre_id=theatre.id,
                        theatre_name=theatre.name,
                        urls_scraped=[base_url],
                        pages_scraped=1,
                        successful_pages=1,
                        markdown_content=change_tracking_result.get('markdown_content', ''),
                        errors=[],
                        scrape_duration=time.time() - start_time,
                        metadata={"change_tracking": True},
                        change_status=change_tracking_result.get('change_status'),
                        previous_scrape_at=change_tracking_result.get('previous_scrape_at'),
                        page_visibility=change_tracking_result.get('page_visibility'),
                        change_metadata=change_tracking_result.get('change_metadata')
                    )

            # Route to appropriate scraping method
            if strategy_type == 'multi_url':
                result = self._handle_multi_url(theatre, strategy, scrape_params)
            elif strategy_type == 'single_url':
                result = self._handle_single_url(theatre, strategy, scrape_params)
            elif strategy_type == 'single_url_with_actions':
                result = self._handle_single_url_with_actions(theatre, strategy, scrape_params)
            elif strategy_type == 'crawl':
                result = self._handle_crawl(theatre, strategy, scrape_params)
            else:
                raise ValueError(f"Unknown strategy type: {strategy_type}")

            # Calculate duration
            duration = time.time() - start_time
            result.scrape_duration = duration

            # Add change tracking data to result if available
            if change_tracking_result and change_tracking_result.get('success'):
                result.change_status = change_tracking_result.get('change_status', 'unknown')
                result.previous_scrape_at = change_tracking_result.get('previous_scrape_at')
                result.page_visibility = change_tracking_result.get('page_visibility')
                result.change_metadata = change_tracking_result.get('change_metadata')
                result.metadata["change_tracking"] = True
            else:
                result.metadata["change_tracking"] = False

            logger.info(f"Completed scrape for {theatre.name}: {result.pages_scraped} pages, "
                       f"{result.successful_pages} successful")

            return result

        except Exception as e:
            logger.error(f"Fatal error scraping {theatre.name}: {str(e)}")
            duration = time.time() - start_time

            return ScrapingResult(
                theatre_id=theatre.id,
                theatre_name=theatre.name,
                urls_scraped=[],
                pages_scraped=0,
                successful_pages=0,
                markdown_content="",
                errors=[f"Fatal error: {str(e)}"],
                scrape_duration=duration,
                metadata={"error_type": "fatal"}
            )

    def _build_scrape_params(self, config_params: Dict[str, Any]) -> Dict[str, Any]:
        """Build Firecrawl parameters from configuration."""
        params = config_params.copy()

        # Convert parameter names to match Firecrawl SDK
        if 'onlyMainContent' in params:
            params['only_main_content'] = params.pop('onlyMainContent')
        if 'waitFor' in params:
            params['wait_for'] = params.pop('waitFor')

        # Remove formats since we're using markdown-only
        if 'formats' in params:
            del params['formats']

        # Set markdown format
        params['formats'] = ['markdown']

        return params

    def _handle_multi_url(self, theatre: Theatre, strategy: Dict[str, Any],
                         scrape_params: Dict[str, Any]) -> ScrapingResult:
        """Handle multi-URL strategy for scraping."""
        if not strategy.get('url_generation'):
            raise ValueError("Multi-URL strategy requires url_generation configuration")

        # Generate URLs (simplified version - would need full URL generation logic)
        url_gen = strategy['url_generation']
        base_url = theatre.base_url

        # For now, create a simple list - in production, implement full URL generation
        urls = [base_url]  # Placeholder

        logger.info(f"Generated {len(urls)} URLs for {theatre.name}")

        # Scrape each URL
        all_markdown = []
        urls_scraped = []
        errors = []

        params = self._build_scrape_params(scrape_params)

        for i, url in enumerate(urls):
            try:
                logger.info(f"Scraping URL {i+1}/{len(urls)}: {url}")

                if i > 0:
                    time.sleep(self.request_delay)

                result = self._scrape_single_url(url, params)
                if result.get('markdown'):
                    all_markdown.append(f"# {url}\n\n{result['markdown']}")
                    urls_scraped.append(url)
                else:
                    errors.append(f"No markdown content from {url}")

            except Exception as e:
                errors.append(f"Failed to scrape {url}: {str(e)}")

        return ScrapingResult(
            theatre_id=theatre.id,
            theatre_name=theatre.name,
            urls_scraped=urls_scraped,
            pages_scraped=len(urls),
            successful_pages=len(urls_scraped),
            markdown_content="\n\n---\n\n".join(all_markdown),
            errors=errors,
            scrape_duration=0.0,
            metadata={"strategy": "multi_url", "total_urls": len(urls)}
        )

    def _handle_single_url(self, theatre: Theatre, strategy: Dict[str, Any],
                          scrape_params: Dict[str, Any]) -> ScrapingResult:
        """Handle single URL strategy."""
        url = strategy.get('url') or theatre.base_url
        if not url:
            raise ValueError("URL is required for single_url strategy")

        logger.info(f"Scraping single URL: {url}")

        params = self._build_scrape_params(scrape_params)
        result = self._scrape_single_url(url, params)

        markdown_content = result.get('markdown', '')
        success = bool(markdown_content)

        return ScrapingResult(
            theatre_id=theatre.id,
            theatre_name=theatre.name,
            urls_scraped=[url] if success else [],
            pages_scraped=1,
            successful_pages=1 if success else 0,
            markdown_content=markdown_content,
            errors=[] if success else ["No markdown content returned"],
            scrape_duration=0.0,
            metadata={"strategy": "single_url"}
        )

    def _handle_single_url_with_actions(self, theatre: Theatre, strategy: Dict[str, Any],
                                       scrape_params: Dict[str, Any]) -> ScrapingResult:
        """Handle single URL with actions strategy."""
        url = strategy.get('url') or theatre.base_url
        if not url:
            raise ValueError("URL is required for single_url_with_actions strategy")

        logger.info(f"Scraping URL with actions: {url}")

        params = self._build_scrape_params(scrape_params)

        # Add actions if specified
        if strategy.get('actions'):
            # Simplified - would need full action building logic
            actions = strategy['actions']
            params['actions'] = actions

        result = self._scrape_single_url(url, params)

        markdown_content = result.get('markdown', '')
        success = bool(markdown_content)

        return ScrapingResult(
            theatre_id=theatre.id,
            theatre_name=theatre.name,
            urls_scraped=[url] if success else [],
            pages_scraped=1,
            successful_pages=1 if success else 0,
            markdown_content=markdown_content,
            errors=[] if success else ["No markdown content returned"],
            scrape_duration=0.0,
            metadata={"strategy": "single_url_with_actions"}
        )

    def _handle_crawl(self, theatre: Theatre, strategy: Dict[str, Any],
                     scrape_params: Dict[str, Any]) -> ScrapingResult:
        """Handle crawl strategy."""
        url = theatre.base_url
        logger.info(f"Starting crawl of: {url}")

        try:
            params = self._build_scrape_params(scrape_params)

            # Use Firecrawl's crawl endpoint
            crawl_result = self.firecrawl.crawl(url, **params)

            if isinstance(crawl_result, dict) and 'data' in crawl_result:
                # Extract markdown from crawl results
                crawl_data = crawl_result['data']
                markdown_content = crawl_data.get('markdown', '')
                urls_scraped = [url]  # Simplified

                return ScrapingResult(
                    theatre_id=theatre.id,
                    theatre_name=theatre.name,
                    urls_scraped=urls_scraped,
                    pages_scraped=1,
                    successful_pages=1 if markdown_content else 0,
                    markdown_content=markdown_content,
                    errors=[],
                    scrape_duration=0.0,
                    metadata={"strategy": "crawl", "crawl_id": crawl_result.get('id')}
                )
            else:
                return ScrapingResult(
                    theatre_id=theatre.id,
                    theatre_name=theatre.name,
                    urls_scraped=[],
                    pages_scraped=0,
                    successful_pages=0,
                    markdown_content="",
                    errors=["Crawl failed to return data"],
                    scrape_duration=0.0,
                    metadata={"strategy": "crawl"}
                )

        except Exception as e:
            return ScrapingResult(
                theatre_id=theatre.id,
                theatre_name=theatre.name,
                urls_scraped=[],
                pages_scraped=0,
                successful_pages=0,
                markdown_content="",
                errors=[f"Crawl failed: {str(e)}"],
                scrape_duration=0.0,
                metadata={"strategy": "crawl"}
            )

    def _scrape_single_url(self, url: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Scrape a single URL with retry logic."""
        last_error = None

        for attempt in range(self.max_retries):
            try:
                if attempt > 0:
                    delay = self.request_delay * (2 ** attempt)
                    logger.info(f"Retrying in {delay}s (attempt {attempt + 1}/{self.max_retries})")
                    time.sleep(delay)

                # Clean parameters
                clean_params = {k: v for k, v in params.items() if v is not None}

                # Scrape the URL
                response = self.firecrawl.scrape(url, **clean_params)

                # Handle different response formats
                if hasattr(response, 'markdown'):
                    return {'markdown': response.markdown, 'metadata': response.metadata}
                elif isinstance(response, dict) and 'markdown' in response:
                    return response
                else:
                    raise ValueError("No markdown content returned")

            except Exception as e:
                last_error = e
                logger.warning(f"Attempt {attempt + 1} failed for {url}: {str(e)}")

        # All retries failed
        raise Exception(f"Failed after {self.max_retries} attempts: {str(last_error)}")

    @classmethod
    def from_env(cls) -> 'TheatreScraper':
        """Create scraper instance from environment variables."""
        api_key = os.getenv('FIRECRAWL_API_KEY')
        if not api_key:
            raise ValueError("FIRECRAWL_API_KEY environment variable is required")

        request_delay = float(os.getenv('REQUEST_DELAY_SECONDS', '1.0'))
        max_retries = int(os.getenv('MAX_RETRIES', '3'))

        return cls(api_key, request_delay, max_retries)
