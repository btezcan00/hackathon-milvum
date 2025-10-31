import os
import re
import time
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from urllib.parse import urlparse
# Try to import Crawl4AI - make it optional to allow backend to start
# Crawl4AI API may vary by version
CRAWL4AI_AVAILABLE = False
Crawler = None
BrowserConfig = None
AsyncWebCrawler = None

try:
    # Try new API first (v0.4+)
    from crawl4ai import AsyncWebCrawler
    CRAWL4AI_AVAILABLE = True
    AsyncWebCrawler = AsyncWebCrawler
except ImportError:
    try:
        # Try old API
        from crawl4ai import Crawler, BrowserConfig
        CRAWL4AI_AVAILABLE = True
        Crawler = Crawler
        BrowserConfig = BrowserConfig
    except ImportError:
        # Crawl4AI not available or different API
        logger.warning("Crawl4AI not available - web crawling features will be disabled")
        CRAWL4AI_AVAILABLE = False

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
        if CRAWL4AI_AVAILABLE and BrowserConfig:
            self._browser_config = BrowserConfig(
                headless=True,
                user_agent=self.user_agent,
                extra_args=["--no-sandbox", "--disable-dev-shm-usage"]
            )
        else:
            self._browser_config = None
    
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
            if Crawler:
                # Old API
                self.crawler = Crawler(browser_config=self._browser_config)
            elif AsyncWebCrawler:
                # New API
                self.crawler = AsyncWebCrawler()
            else:
                raise ImportError("Could not import Crawler from crawl4ai")
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
            
            # Crawl the page
            result = await crawler.arun(url=url)
            
            if not result.success:
                logger.warning(f"Failed to crawl {url}: {result.error_message}")
                return None
            
            # Extract content
            title = result.metadata.get('title', '') if result.metadata else ''
            if not title and result.markdown:
                # Try to extract title from markdown
                first_line = result.markdown.split('\n')[0] if result.markdown else ''
                if first_line.startswith('# '):
                    title = first_line[2:].strip()
            
            # Get text content (prefer markdown, fallback to html)
            text_content = result.markdown or result.cleaned_html or result.html or ''
            
            # Clean up text (remove excessive whitespace)
            text_content = re.sub(r'\s+', ' ', text_content).strip()
            
            # Limit text length (first 5000 characters)
            if len(text_content) > 5000:
                text_content = text_content[:5000] + "..."
            
            return {
                'url': url,
                'title': title or 'Untitled',
                'text': text_content,
                'metadata': {
                    'html_length': len(result.html) if result.html else 0,
                    'markdown_length': len(result.markdown) if result.markdown else 0,
                    'status_code': result.status_code if hasattr(result, 'status_code') else None,
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
                await self.crawler.close()
        except Exception as e:
            logger.error(f"Error closing crawler: {str(e)}")

