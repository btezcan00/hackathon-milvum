"""
Government Data API Service

Service for fetching data from Dutch government open data APIs:
- data.overheid.nl CKAN API (primary)
- Future: open-overheid.nl API when available
"""

import requests
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)


class GovernmentDataService:
    """Service for interacting with Dutch government open data APIs"""
    
    # Base URLs for government data APIs
    DATA_OVERHEID_BASE_URL = "https://data.overheid.nl/data/api/3/action"
    
    def __init__(self, timeout: int = 30):
        """
        Initialize government data service
        
        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'RAG-Backend/1.0 (WOO Research Assistant)',
            'Accept': 'application/json'
        })
    
    def search_datasets(
        self, 
        query: str, 
        rows: int = 10, 
        start: int = 0,
        filters: Optional[Dict[str, str]] = None,
        sort: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Search datasets on data.overheid.nl using CKAN API
        
        Args:
            query: Search query string
            rows: Number of results to return (max 1000)
            start: Offset for pagination
            filters: Optional filters (e.g., organization, tags)
            sort: Optional sort parameter (e.g., "metadata_modified desc")
            
        Returns:
            Dict with 'success', 'count', 'results' keys
        """
        try:
            # Build request URL
            url = f"{self.DATA_OVERHEID_BASE_URL}/package_search"
            
            # Build query parameters
            params = {
                'q': query,
                'rows': min(rows, 1000),  # CKAN max is 1000
                'start': start
            }
            
            # Add filters if provided (CKAN uses fq parameter for filtering)
            if filters:
                fq_parts = []
                for key, value in filters.items():
                    fq_parts.append(f"{key}:{value}")
                if fq_parts:
                    params['fq'] = ' AND '.join(fq_parts)
            
            # Add sort if provided
            if sort:
                params['sort'] = sort
            
            logger.info(f"Searching data.overheid.nl with query: {query}, params: {params}")
            
            # Make API request
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            # Parse response
            data = response.json()
            
            if not data.get('success'):
                logger.error(f"API returned success=false: {data.get('error', 'Unknown error')}")
                return {
                    'success': False,
                    'count': 0,
                    'results': [],
                    'error': data.get('error', {}).get('message', 'Unknown error')
                }
            
            result = data.get('result', {})
            count = result.get('count', 0)
            results = result.get('results', [])
            
            logger.info(f"Found {count} datasets, returning {len(results)} results")
            
            return {
                'success': True,
                'count': count,
                'results': results
            }
            
        except requests.exceptions.Timeout:
            logger.error(f"Timeout while searching data.overheid.nl")
            return {
                'success': False,
                'count': 0,
                'results': [],
                'error': 'Request timeout'
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"Error searching data.overheid.nl: {str(e)}")
            return {
                'success': False,
                'count': 0,
                'results': [],
                'error': str(e)
            }
        except Exception as e:
            logger.error(f"Unexpected error in search_datasets: {str(e)}")
            return {
                'success': False,
                'count': 0,
                'results': [],
                'error': str(e)
            }
    
    def get_dataset_details(self, dataset_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific dataset
        
        Args:
            dataset_id: Dataset ID or name
            
        Returns:
            Dataset details dict or None if not found
        """
        try:
            url = f"{self.DATA_OVERHEID_BASE_URL}/package_show"
            params = {'id': dataset_id}
            
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            
            if not data.get('success'):
                logger.error(f"Failed to get dataset {dataset_id}")
                return None
            
            return data.get('result')
            
        except Exception as e:
            logger.error(f"Error getting dataset details for {dataset_id}: {str(e)}")
            return None
    
    def parse_results_to_clean_context_and_citations(
        self, 
        results: List[Dict[str, Any]]
    ) -> tuple[str, List[Dict[str, Any]]]:
        """
        Parse API results into TWO separate structures:
        1. Clean text context for LLM (no metadata)
        2. Full citation objects for frontend
        
        This is CRITICAL for clean LLM responses.
        
        Args:
            results: Raw API results from data.overheid.nl
            
        Returns:
            Tuple of (clean_context_string, citations_list)
        """
        clean_context_parts = []
        citations = []
        
        for i, result in enumerate(results, 1):
            try:
                # Extract basic info
                title = result.get('title', 'Untitled')
                notes = result.get('notes', '')
                dataset_id = result.get('id', '')
                
                # Get organization/publisher
                organization = result.get('organization', {})
                publisher = organization.get('title', 'Onbekende organisatie') if organization else 'Onbekende organisatie'
                
                # Get dates
                metadata_created = result.get('metadata_created', '')
                metadata_modified = result.get('metadata_modified', '')
                
                # Get resources (downloadable files)
                resources = result.get('resources', [])
                download_url = None
                file_format = None
                
                if resources:
                    # Get first resource as primary download
                    first_resource = resources[0]
                    download_url = first_resource.get('url', '')
                    file_format = first_resource.get('format', 'Unknown')
                
                # Build dataset page URL
                dataset_url = f"https://data.overheid.nl/dataset/{dataset_id}"
                
                # === 1. CLEAN CONTEXT FOR LLM (no metadata, just content) ===
                clean_text = f"[{i}] {title}\n\n{notes if notes else 'Geen beschrijving beschikbaar.'}"
                clean_context_parts.append(clean_text)
                
                # === 2. FULL CITATION FOR FRONTEND (all metadata) ===
                # Create snippet from notes (first 300 chars)
                snippet = notes[:300] + '...' if len(notes) > 300 else notes
                if not snippet:
                    snippet = f"Dataset gepubliceerd door {publisher}"
                
                citation = {
                    'id': str(uuid.uuid4()),
                    'url': dataset_url,
                    'downloadUrl': download_url,  # May be None
                    'title': title,
                    'snippet': snippet,
                    'relevanceScore': 1.0 - (i * 0.05),  # Simple relevance based on API order
                    'domain': 'data.overheid.nl',
                    'publisher': publisher,
                    'format': file_format,
                    'crawledAt': datetime.now().isoformat(),
                    'type': 'government_dataset',
                    'highlightText': notes  # Full text for potential highlighting
                }
                
                # Add dates if available
                if metadata_created:
                    citation['publishedDate'] = metadata_created
                if metadata_modified:
                    citation['modifiedDate'] = metadata_modified
                
                citations.append(citation)
                
            except Exception as e:
                logger.error(f"Error parsing result {i}: {str(e)}")
                continue
        
        # Join clean context parts with double newlines
        clean_context = "\n\n".join(clean_context_parts)
        
        logger.info(f"Parsed {len(citations)} results into clean context ({len(clean_context)} chars) and citations")
        
        return clean_context, citations
    
    def search_and_parse_with_retry(
        self,
        query: str,
        rows: int = 10,
        filters: Optional[Dict[str, str]] = None,
        sort: Optional[str] = None
    ) -> tuple[str, List[Dict[str, Any]], Dict[str, Any]]:
        """
        Smart search with automatic retry strategies when 0 results found
        
        Tries multiple approaches:
        1. Original query
        2. Query without sort (broader search)
        3. Individual words from query (fallback)
        4. Remove filters (even broader)
        
        Args:
            query: Search query
            rows: Number of results
            filters: Optional filters
            sort: Optional sort parameter
            
        Returns:
            Tuple of (clean_context, citations, metadata)
        """
        attempts = []
        
        # Strategy 1: Original query
        attempts.append({
            'query': query,
            'filters': filters,
            'sort': sort,
            'strategy': 'original'
        })
        
        # Strategy 2: Remove sort if present (sometimes sorting reduces results)
        if sort:
            attempts.append({
                'query': query,
                'filters': filters,
                'sort': None,
                'strategy': 'no_sort'
            })
        
        # Strategy 3: Simplify query (take first 2-3 words)
        words = query.split()
        if len(words) > 2:
            simplified_query = ' '.join(words[:2])
            attempts.append({
                'query': simplified_query,
                'filters': filters,
                'sort': None,
                'strategy': 'simplified'
            })
        
        # Strategy 4: Remove filters (broadest search)
        if filters:
            attempts.append({
                'query': query,
                'filters': None,
                'sort': None,
                'strategy': 'no_filters'
            })
        
        # Strategy 5: Single most important word
        if len(words) > 1:
            # Take longest word (usually most specific)
            main_word = max(words, key=len)
            attempts.append({
                'query': main_word,
                'filters': None,
                'sort': None,
                'strategy': 'single_word'
            })
        
        # Try each strategy until we get results
        for i, attempt in enumerate(attempts):
            logger.info(f"Attempt {i+1}/{len(attempts)} with strategy '{attempt['strategy']}': query='{attempt['query']}'")
            
            search_result = self.search_datasets(
                query=attempt['query'],
                rows=rows,
                filters=attempt.get('filters'),
                sort=attempt.get('sort')
            )
            
            if not search_result.get('success'):
                logger.warning(f"Attempt {i+1} failed: {search_result.get('error')}")
                continue
            
            results = search_result.get('results', [])
            
            if results:
                # Success! Parse and return
                clean_context, citations = self.parse_results_to_clean_context_and_citations(results)
                
                metadata = {
                    'success': True,
                    'total_count': search_result.get('count', 0),
                    'returned_count': len(citations),
                    'query': attempt['query'],
                    'original_query': query,
                    'strategy_used': attempt['strategy'],
                    'attempts': i + 1
                }
                
                if attempt['strategy'] != 'original':
                    logger.info(f"✓ Found {len(citations)} results using '{attempt['strategy']}' strategy (query: '{attempt['query']}')")
                
                return clean_context, citations, metadata
            else:
                logger.info(f"Attempt {i+1} returned 0 results, trying next strategy...")
        
        # All strategies failed
        logger.warning(f"All {len(attempts)} search strategies returned 0 results for: {query}")
        return "", [], {
            'success': True,
            'total_count': 0,
            'returned_count': 0,
            'query': query,
            'strategy_used': 'all_failed',
            'attempts': len(attempts)
        }
    
    def search_and_parse(
        self,
        query: str,
        rows: int = 10,
        filters: Optional[Dict[str, str]] = None,
        sort: Optional[str] = None
    ) -> tuple[str, List[Dict[str, Any]], Dict[str, Any]]:
        """
        High-level method: Search and parse in one call with smart retry
        
        Args:
            query: Search query
            rows: Number of results
            filters: Optional filters
            sort: Optional sort parameter
            
        Returns:
            Tuple of (clean_context, citations, metadata)
            metadata includes: total_count, query_info, etc.
        """
        # Use retry logic by default
        return self.search_and_parse_with_retry(query, rows, filters, sort)
    
    def close(self):
        """Close the session"""
        self.session.close()

