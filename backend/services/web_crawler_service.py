import os
import re
import time
import logging
import asyncio
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
            domain = self._extract_domain(url)
            logger.info(f"Crawling website: {url} (domain: {domain})")
            
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
        Crawl multiple URLs in parallel using asyncio
        
        Args:
            urls: List of URLs to crawl
            query: Query string for context (optional)
            
        Returns:
            List of extracted content dictionaries
        """
        urls_to_crawl = urls[:self.max_pages]  # Limit to max_pages
        
        logger.info(f"Starting parallel crawl of {len(urls_to_crawl)} URLs (query: {query})")
        logger.info(f"URLs to crawl: {urls_to_crawl}")
        
        # Create tasks for parallel crawling
        async def crawl_single(url: str, index: int) -> Optional[Dict[str, Any]]:
            """Crawl a single URL with error handling"""
            try:
                logger.info(f"[{index+1}/{len(urls_to_crawl)}] Starting parallel crawl: {url}")
                content = await self.extract_content(url)
                if content:
                    title = content.get('title', 'N/A')
                    text_length = len(content.get('text', ''))
                    logger.info(f"[{index+1}/{len(urls_to_crawl)}] ✓ Successfully crawled: {url} (Title: {title}, Content: {text_length} chars)")
                    return content
                else:
                    logger.warning(f"[{index+1}/{len(urls_to_crawl)}] ✗ Failed to extract content from: {url}")
                    return None
            except Exception as e:
                logger.error(f"[{index+1}/{len(urls_to_crawl)}] ✗ Error crawling {url}: {str(e)}")
                return None
        
        # Execute all crawls in parallel
        tasks = [crawl_single(url, i) for i, url in enumerate(urls_to_crawl)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out None values and exceptions
        valid_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Exception during crawl of {urls_to_crawl[i]}: {str(result)}")
            elif result is not None:
                valid_results.append(result)
        
        logger.info(f"Crawled {len(valid_results)}/{len(urls_to_crawl)} URLs successfully (parallel execution)")
        return valid_results
    
    async def crawl_website_multi_page(
        self, 
        entry_url: str, 
        query: str = "", 
        max_pages: int = 10,
        depth: int = 2
    ) -> List[Dict[str, Any]]:
        """
        Crawl multiple pages from a website starting from an entry URL.
        Uses crawl4ai's link discovery capabilities to find and crawl multiple related pages.
        
        Args:
            entry_url: Starting URL for crawling
            query: Query string for context (optional, used to prioritize relevant pages)
            max_pages: Maximum number of pages to crawl from this website
            depth: Maximum depth to crawl (1 = only entry page, 2 = entry + linked pages, etc.)
            
        Returns:
            List of extracted content dictionaries from multiple pages
        """
        if not self._is_allowed_domain(entry_url):
            logger.warning(f"Domain not allowed for URL: {entry_url}")
            return []
        
        try:
            domain = self._extract_domain(entry_url)
            logger.info(f"Starting multi-page crawl of website: {domain} (entry: {entry_url}, max_pages: {max_pages}, depth: {depth})")
            
            # Get or initialize crawler
            crawler = self._get_crawler()
            
            # Track crawled URLs to avoid duplicates
            crawled_urls = set()
            all_results = []
            
            # Start with entry URL
            urls_to_crawl = [entry_url]
            current_depth = 0
            
            while urls_to_crawl and current_depth < depth and len(all_results) < max_pages:
                # Get URLs to crawl in this batch (up to max_pages or 10 parallel, whichever is smaller)
                batch_urls = [url for url in urls_to_crawl[:max_pages - len(all_results)] if url not in crawled_urls]
                
                if not batch_urls:
                    break
                
                # Crawl current batch of URLs in parallel (up to 10 concurrent requests)
                max_concurrent = min(10, len(batch_urls), max_pages - len(all_results))
                
                logger.info(f"[Depth {current_depth}] Crawling {len(batch_urls)} URLs in parallel (max {max_concurrent} concurrent)")
                
                # Create tasks for parallel crawling
                async def crawl_single_with_tracking(url: str) -> Optional[Dict[str, Any]]:
                    """Crawl a single URL with tracking"""
                    try:
                        logger.info(f"[Depth {current_depth}] Starting: {url}")
                        content = await self.extract_content(url)
                        if content:
                            logger.info(f"[Depth {current_depth}] ✓ Completed: {url} (Title: {content.get('title', 'N/A')})")
                        else:
                            logger.warning(f"[Depth {current_depth}] ✗ Failed: {url}")
                        return content
                    except Exception as e:
                        logger.error(f"[Depth {current_depth}] ✗ Error crawling {url}: {str(e)}")
                        return None
                
                # Create semaphore to limit concurrent requests
                semaphore = asyncio.Semaphore(max_concurrent)
                
                async def crawl_with_semaphore(url: str) -> Optional[Dict[str, Any]]:
                    """Crawl with semaphore to limit concurrency"""
                    async with semaphore:
                        return await crawl_single_with_tracking(url)
                
                # Execute all crawls in parallel with concurrency limit
                tasks = [crawl_with_semaphore(url) for url in batch_urls]
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Process results
                for i, result in enumerate(batch_results):
                    if isinstance(result, Exception):
                        logger.error(f"Exception during crawl of {batch_urls[i]}: {str(result)}")
                        continue
                    
                    if result is not None:
                        url = batch_urls[i]
                        crawled_urls.add(url)
                        all_results.append(result)
                        logger.info(f"✓ Total crawled: {len(all_results)}/{max_pages} pages")
                
                # If we have more capacity, discover new links from crawled pages
                if len(all_results) < max_pages and current_depth < depth - 1:
                    # Try to extract links from the most recent pages
                    new_urls = await self._extract_links_from_content(
                        crawler=crawler,
                        entry_url=entry_url,
                        crawled_content=all_results[-min(5, len(all_results)):],  # Check last 5 pages
                        domain=domain,
                        max_links=20
                    )
                    
                    # Filter out already crawled URLs and ensure they're from the same domain
                    urls_to_crawl = [
                        url for url in new_urls 
                        if url not in crawled_urls 
                        and self._extract_domain(url) == domain
                        and self._is_allowed_domain(url)
                    ][:max_pages - len(all_results)]
                    
                    if urls_to_crawl:
                        logger.info(f"Discovered {len(urls_to_crawl)} new URLs for depth {current_depth + 1}")
                
                current_depth += 1
            
            logger.info(f"Completed multi-page crawl: {len(all_results)} pages from {domain}")
            return all_results
            
        except Exception as e:
            logger.error(f"Error in multi-page crawl of {entry_url}: {str(e)}")
            return []
    
    async def _extract_links_from_content(
        self,
        crawler,
        entry_url: str,
        crawled_content: List[Dict[str, Any]],
        domain: str,
        max_links: int = 20
    ) -> List[str]:
        """
        Extract links from crawled content that are relevant to the domain.
        
        Args:
            crawler: The crawl4ai crawler instance
            entry_url: Original entry URL
            crawled_content: List of crawled content dictionaries
            domain: Domain to filter links by
            max_links: Maximum number of links to return
            
        Returns:
            List of discovered URLs
        """
        discovered_urls = set()
        
        try:
            # Try to extract links from crawl4ai result objects
            for content in crawled_content[-3:]:  # Check last 3 pages
                # Try to get HTML from the original crawl result
                # We'll need to crawl again to get links, or parse from metadata
                pass
            
            # Crawl entry URL to get links
            try:
                result = await crawler.arun(url=entry_url) if hasattr(crawler, 'arun') else await crawler.crawl(url=entry_url)
                
                # Extract links from result
                links = []
                if isinstance(result, dict):
                    links = result.get('links', []) or []
                    # Also try to extract from HTML
                    html = result.get('html', '') or result.get('cleaned_html', '')
                elif hasattr(result, 'links'):
                    links = result.links if isinstance(result.links, list) else []
                    html = getattr(result, 'html', '') or getattr(result, 'cleaned_html', '')
                else:
                    html = ''
                
                # Parse HTML for links if available
                if html:
                    try:
                        from bs4 import BeautifulSoup
                        soup = BeautifulSoup(html, 'html.parser')
                        for a_tag in soup.find_all('a', href=True):
                            href = a_tag.get('href', '')
                            if href:
                                # Convert relative URLs to absolute
                                from urllib.parse import urljoin, urlparse
                                absolute_url = urljoin(entry_url, href)
                                # Extract just the URL path if it's a valid URL
                                parsed = urlparse(absolute_url)
                                if parsed.scheme and parsed.netloc:
                                    links.append(absolute_url)
                    except ImportError:
                        logger.debug("BeautifulSoup not available for HTML parsing")
                    except Exception as e:
                        logger.debug(f"Error parsing HTML for links: {e}")
                
                # Filter links by domain
                for link in links:
                    if isinstance(link, str) and link.startswith('http'):
                        link_domain = self._extract_domain(link)
                        if link_domain == domain:
                            discovered_urls.add(link)
            except Exception as e:
                logger.debug(f"Could not extract links from entry URL: {e}")
            
        except Exception as e:
            logger.debug(f"Error extracting links: {e}")
        
        return list(discovered_urls)[:max_links]
    
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

