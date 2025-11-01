"""
URL Selection Service

This service uses LLM to intelligently select relevant government website URLs
based on the user's query. It analyzes the query and matches it against
the curated list of government sources.
"""

import json
import logging
from typing import List, Dict, Any
from services.llm_service import ChatService
from services.government_sources import GOVERNMENT_SOURCES, get_sources_info

logger = logging.getLogger(__name__)


class URLSelector:
    def __init__(self, chat_service: ChatService = None):
        """
        Initialize URL selector with optional chat service.
        
        Args:
            chat_service: Optional ChatService instance. If not provided, creates a new one.
        """
        self.chat_service = chat_service or ChatService()
        self.sources = GOVERNMENT_SOURCES
    
    def select_urls(self, query: str, max_urls: int = 5) -> List[str]:
        """
        Select relevant URLs from government sources based on the query.
        
        Args:
            query: User's query/question
            max_urls: Maximum number of URLs to return
            
        Returns:
            List of selected URLs
        """
        try:
            # Build prompt for LLM
            sources_info = get_sources_info()
            
            prompt = f"""You are helping select the most relevant Dutch government websites to crawl based on a user's question.

Available government sources:
{sources_info}

User's question: "{query}"

Based on the user's question, select the most relevant URLs (up to {max_urls}) that are likely to contain information to answer this question.

Respond with ONLY a JSON array of URL strings, nothing else. Example format:
["https://www.rijksoverheid.nl/onderwerpen/belastingen", "https://ind.nl/werk"]

Selected URLs:"""

            messages = [
                {
                    "role": "system",
                    "content": "You are a helpful assistant that selects relevant URLs from a list. Always respond with valid JSON array of URLs only."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]
            
            # Get LLM response
            response = self.chat_service.chat(messages)
            
            # Parse JSON response
            # Try to extract JSON from response (might have extra text)
            response = response.strip()
            
            # Remove markdown code blocks if present
            if response.startswith("```"):
                lines = response.split("\n")
                response = "\n".join(lines[1:-1]) if len(lines) > 2 else response
            
            # Parse JSON
            try:
                urls = json.loads(response)
                if not isinstance(urls, list):
                    logger.warning(f"LLM returned non-list response: {response}")
                    urls = []
            except json.JSONDecodeError:
                # Try to extract URLs manually if JSON parsing fails
                logger.warning(f"Failed to parse JSON from LLM response: {response}")
                urls = self._extract_urls_from_text(response)
            
            # Validate URLs are in our source list
            valid_urls = []
            source_urls = {s["url"] for s in self.sources}
            
            for url in urls:
                if isinstance(url, str) and url in source_urls:
                    valid_urls.append(url)
                elif isinstance(url, str):
                    # Try to find closest match
                    matched = self._find_closest_url(url, source_urls)
                    if matched:
                        valid_urls.append(matched)
            
            # Limit to max_urls
            valid_urls = valid_urls[:max_urls]
            
            # Fallback: if no URLs selected or selection failed, use keyword matching
            if not valid_urls:
                logger.info("LLM selection failed, using keyword-based fallback")
                valid_urls = self._keyword_based_selection(query, max_urls)
            
            logger.info(f"Selected {len(valid_urls)} URLs for query: {query[:50]}...")
            return valid_urls
            
        except Exception as e:
            logger.error(f"Error in URL selection: {str(e)}")
            # Fallback to keyword-based selection
            return self._keyword_based_selection(query, max_urls)
    
    def _extract_urls_from_text(self, text: str) -> List[str]:
        """Extract URLs from text using simple pattern matching."""
        import re
        urls = re.findall(r'https?://[^\s,)\]"]+', text)
        return urls[:5]
    
    def _find_closest_url(self, url: str, valid_urls: set) -> str:
        """Find closest matching URL from valid set."""
        # Simple substring matching
        for valid_url in valid_urls:
            if url in valid_url or valid_url in url:
                return valid_url
        return None
    
    def _keyword_based_selection(self, query: str, max_urls: int) -> List[str]:
        """
        Fallback keyword-based URL selection.
        Uses simple keyword matching when LLM selection fails.
        """
        query_lower = query.lower()
        
        # Category keywords mapping
        category_keywords = {
            "immigration": ["immigratie", "visa", "verblijfsvergunning", "ind", "paspoort", "nationaliteit"],
            "taxes": ["belasting", "belastingdienst", "aangifte", "btw", "inkomstenbelasting"],
            "employment": ["werk", "baan", "uitkering", "uwv", "werkloos", "bijstand"],
            "education": ["onderwijs", "school", "studie", "duo", "studiefinanciering"],
            "healthcare": ["zorg", "zorgverzekering", "ziekenhuis", "gezondheidszorg"],
            "pensions": ["pensioen", "aow", "svb"],
            "travel": ["reis", "buitenland", "paspoort"],
            "housing": ["huisvesting", "woning", "huur", "hypotheek"],
            "family": ["gezin", "gezinsbijslag", "kinderbijslag"],
            "transportation": ["rijbewijs", "rdw", "auto", "voertuig"],
            "digital_services": ["digid", "online", "digitaal"],
            "legal": ["recht", "rechter", "rechtspraak"],
            "business": ["ondernemen", "bedrijf", "zakelijk"],
        }
        
        # Score sources based on keyword matches
        scored_sources = []
        for source in self.sources:
            score = 0
            title_desc = f"{source['title']} {source['description']}".lower()
            category = source.get("category", "")
            
            # Check category keywords
            if category in category_keywords:
                for keyword in category_keywords[category]:
                    if keyword in query_lower:
                        score += 2
            
            # Check direct matches in title/description
            for word in query_lower.split():
                if len(word) > 3 and word in title_desc:
                    score += 1
            
            if score > 0:
                scored_sources.append((score, source["url"]))
        
        # Sort by score and return top URLs
        scored_sources.sort(reverse=True, key=lambda x: x[0])
        return [url for _, url in scored_sources[:max_urls]]

