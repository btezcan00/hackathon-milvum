import os
import re
import time
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from urllib.parse import urlparse
# Make Crawl4AI completely optional - backend can start without it
# User will get an error when trying to use research feature if not available
CRAWL4AI_AVAILABLE = False
try:
    import crawl4ai
    # Don't import anything yet - just check if package exists
    CRAWL4AI_AVAILABLE = True
except:
    pass

logger = logging.getLogger(__name__)

class WebCrawlerService:
    """Service for crawling Dutch government websites using Crawl4AI"""
    
    # Default allowed Dutch government domains
    DEFAULT_GOV_DOMAINS = [
        r'.*\.nl$',
        r'.*\.overheid\.nl$',
        r'.*\.rijkoverheid\.nl$',
        r'.*\.rijksoverheid\.nl$',
        r'.*\.minbuza\.nl$',
        r'.*\.belastingdienst\.nl$',
        r'.*\.uwv\.nl$',
        r'.*\.cbs\.nl$',
        r'.*\.courant\.nl$',
        r'.*\.officielebekendmakingen\.nl$',
    ]
    
    def __init__(
        self,
        max_pages: int = 10,
        timeout: int = 30,
        delay_between_requests: float = 2.0,
        allowed_domains: Optional[List[str]] = None,
        user_agent: Optional[str] = None
    ):
        """
        Initialize web crawler service
        
        Args:
            max_pages: Maximum number of pages to crawl per query
            timeout: Timeout per page in seconds
            delay_between_requests: Delay between requests in seconds
            allowed_domains: List of regex patterns for allowed domains
            user_agent: User agent string for requests
        """
        self.max_pages = max_pages
        self.timeout = timeout
        self.delay_between_requests = delay_between_requests
        self.allowed_domains = allowed_domains or self.DEFAULT_GOV_DOMAINS
        self.user_agent = user_agent or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        
        # Initialize Crawl4AI crawler lazily (on first use)
        # This avoids initialization errors if crawler is never used
        self.crawler = None
        self._browser_config = None  # Will be set when crawler is initialized
        self._crawler_type = None  # Track which API version we're using
    
    def _is_allowed_domain(self, url: str) -> bool:
        """
        Check if URL belongs to an allowed domain
        
        Args:
            url: URL to check
            
        Returns:
            True if domain is allowed, False otherwise
        """
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            for pattern in self.allowed_domains:
                if re.match(pattern, domain):
                    return True
            return False
        except Exception as e:
            logger.error(f"Error checking domain for {url}: {str(e)}")
            return False
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL"""
        try:
            parsed = urlparse(url)
            return parsed.netloc.lower()
        except Exception:
            return ""
    
    def _get_crawler(self):
        """Get or initialize the crawler instance"""
        if not CRAWL4AI_AVAILABLE:
            raise ImportError("Crawl4AI is not available. Please install it: pip install crawl4ai")
        if self.crawler is None:
            # Try to import and use crawl4ai dynamically - try multiple import patterns
            crawler_initialized = False
            
            # Try new API first (AsyncWebCrawler)
            try:
                from crawl4ai import AsyncWebCrawler
                self.crawler = AsyncWebCrawler()
                self._crawler_type = "new"
                crawler_initialized = True
            except (ImportError, AttributeError):
                try:
                    from crawl4ai.async_webcrawler import AsyncWebCrawler
                    self.crawler = AsyncWebCrawler()
                    self._crawler_type = "new"
                    crawler_initialized = True
                except (ImportError, AttributeError):
                    pass
            
            # Try old API if new didn't work
            if not crawler_initialized:
                try:
                    from crawl4ai import Crawler, BrowserConfig
                    browser_config = BrowserConfig(
                        headless=True,
                        user_agent=self.user_agent,
                        extra_args=["--no-sandbox", "--disable-dev-shm-usage"]
                    )
                    self.crawler = Crawler(browser_config=browser_config)
                    self._crawler_type = "old"
                    crawler_initialized = True
                except (ImportError, AttributeError, Exception) as e:
                    raise ImportError(f"Could not import or initialize Crawler from crawl4ai: {e}. The package may not be properly installed or the API has changed.")
        
        return self.crawler
    
    async def extract_content(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Extract content from a single URL
        
        Args:
            url: URL to crawl
            
        Returns:
            Dictionary with url, title, text, metadata, extracted_at
        """
        if not self._is_allowed_domain(url):
            logger.warning(f"Domain not allowed for URL: {url}")
            return None
        
        try:
            logger.info(f"Crawling URL: {url}")
            
            # Get or initialize crawler
            crawler = self._get_crawler()
            
            # Crawl the page - try new API first, fallback to old API
            try:
                # Try new API (AsyncWebCrawler)
                result = await crawler.arun(url=url)
                
                # Check if result is dict (new API) or object (old API)
                if isinstance(result, dict):
                    # New API - result is a dict
                    success = result.get('success', True)
                    if not success:
                        error_msg = result.get('error_message', 'Unknown error')
                        logger.warning(f"Failed to crawl {url}: {error_msg}")
                        return None
                    
                    title = result.get('metadata', {}).get('title', '') if result.get('metadata') else ''
                    text_content = result.get('markdown', '') or result.get('cleaned_html', '') or result.get('html', '')
                else:
                    # Old API - result is an object
                    if not hasattr(result, 'success') or not result.success:
                        error_msg = getattr(result, 'error_message', 'Unknown error')
                        logger.warning(f"Failed to crawl {url}: {error_msg}")
                        return None
                    
                    title = result.metadata.get('title', '') if result.metadata else ''
                    text_content = result.markdown or result.cleaned_html or result.html or ''
                    
            except AttributeError:
                # Fallback: try different method names
                result = await crawler.crawl(url=url) if hasattr(crawler, 'crawl') else await crawler.arun(url=url)
                if isinstance(result, dict):
                    success = result.get('success', True)
                    if not success:
                        return None
                    title = result.get('metadata', {}).get('title', '') if result.get('metadata') else ''
                    text_content = result.get('markdown', '') or result.get('cleaned_html', '') or result.get('html', '')
                else:
                    if not result.success:
                        return None
                    title = result.metadata.get('title', '') if result.metadata else ''
                    text_content = result.markdown or result.cleaned_html or result.html or ''
            
            # Extract title if not found
            if not title and text_content:
                # Try to extract title from markdown
                first_line = text_content.split('\n')[0] if text_content else ''
                if first_line.startswith('# '):
                    title = first_line[2:].strip()
            
            # Clean up text (remove excessive whitespace)
            text_content = re.sub(r'\s+', ' ', text_content).strip()
            
            # Limit text length (first 5000 characters)
            if len(text_content) > 5000:
                text_content = text_content[:5000] + "..."
            
            # Get metadata safely
            html_length = 0
            markdown_length = 0
            status_code = None
            if isinstance(result, dict):
                html_length = len(result.get('html', '')) if result.get('html') else 0
                markdown_length = len(result.get('markdown', '')) if result.get('markdown') else 0
                status_code = result.get('status_code', None)
            else:
                html_length = len(result.html) if hasattr(result, 'html') and result.html else 0
                markdown_length = len(result.markdown) if hasattr(result, 'markdown') and result.markdown else 0
                status_code = getattr(result, 'status_code', None)
            
            return {
                'url': url,
                'title': title or 'Untitled',
                'text': text_content,
                'metadata': {
                    'html_length': html_length,
                    'markdown_length': markdown_length,
                    'status_code': status_code,
                },
                'extracted_at': datetime.now().isoformat(),
                'domain': self._extract_domain(url)
            }
            
        except Exception as e:
            logger.error(f"Error extracting content from {url}: {str(e)}")
            return None
    
    async def crawl_urls(self, urls: List[str], query: str = "") -> List[Dict[str, Any]]:
        """
        Crawl multiple URLs with rate limiting
        
        Args:
            urls: List of URLs to crawl
            query: Query string for context (optional)
            
        Returns:
            List of extracted content dictionaries
        """
        results = []
        urls_to_crawl = urls[:self.max_pages]  # Limit to max_pages
        
        logger.info(f"Starting to crawl {len(urls_to_crawl)} URLs (query: {query})")
        
        for i, url in enumerate(urls_to_crawl):
            try:
                # Add delay between requests (except first)
                if i > 0:
                    time.sleep(self.delay_between_requests)
                
                content = await self.extract_content(url)
                if content:
                    results.append(content)
                    logger.info(f"Successfully crawled {i+1}/{len(urls_to_crawl)}: {url}")
                
            except Exception as e:
                logger.error(f"Error crawling {url}: {str(e)}")
                continue
        
        logger.info(f"Crawled {len(results)}/{len(urls_to_crawl)} URLs successfully")
        return results
    
    def generate_search_urls(self, query: str, base_urls: Optional[List[str]] = None) -> List[str]:
        """
        Generate URLs to crawl based on query
        
        Args:
            query: Search query
            base_urls: Optional list of base URLs to search
            
        Returns:
            List of URLs to crawl
        """
        # For now, return base URLs if provided
        # In the future, this could integrate with search APIs
        if base_urls:
            return base_urls
        
        # Default: return empty list (URLs should be provided explicitly)
        logger.warning("No base URLs provided for search")
        return []
    
    async def close(self):
        """Clean up crawler resources"""
        try:
            if self.crawler is not None:
                # Try to close the crawler gracefully
                if hasattr(self.crawler, 'close'):
                    try:
                        await self.crawler.close()
                    except RuntimeError as e:
                        # Ignore event loop errors during cleanup
                        logger.debug(f"Event loop error during crawler close (this is usually OK): {str(e)}")
                elif hasattr(self.crawler, 'cleanup'):
                    await self.crawler.cleanup()
                self.crawler = None
        except Exception as e:
            # Log but don't raise - cleanup errors shouldn't break the flow
            logger.debug(f"Error closing crawler (non-critical): {str(e)}")

