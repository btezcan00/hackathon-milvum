"""
URL Selection Service

This service uses LLM to intelligently select relevant government website URLs
based on the user's query. It analyzes the query and matches it against
the curated list of government sources.
"""

import json
import logging
import requests
from typing import List, Dict, Any
from services.groq_service import GroqService
from services.government_sources import GOVERNMENT_SOURCES, get_sources_info

logger = logging.getLogger(__name__)


class URLSelector:
    def __init__(self, groq_service: GroqService = None):
        """
        Initialize URL selector with Groq service for fast classification.
        
        Args:
            groq_service: Optional GroqService instance. If not provided, creates a new one.
        """
        self.groq_service = groq_service or GroqService()
        self.sources = GOVERNMENT_SOURCES
    
    def _prefilter_sources(self, query: str, max_candidates: int = 20) -> List[Dict[str, Any]]:
        """
        Pre-filter sources based on keyword matching before sending to Groq.
        This reduces the number of sources passed to the LLM.
        
        Args:
            query: User's query
            max_candidates: Maximum number of candidate sources to return
            
        Returns:
            Filtered list of source dictionaries
        """
        query_lower = query.lower()
        scored_sources = []
        
        # Keywords mapping for categories
        category_keywords = {
            "woo": ["woo", "wob", "wet openbaarheid", "open overheid", "woo-verzoek", "woo verzoek", "vrijheid van informatie"],
            "immigration": ["immigratie", "visa", "verblijfsvergunning", "ind", "paspoort", "nationaliteit", "verblijf"],
            "taxes": ["belasting", "belastingdienst", "aangifte", "btw", "inkomstenbelasting", "belastingaangifte"],
            "employment": ["werk", "baan", "uitkering", "uwv", "werkloos", "bijstand", "arbeid"],
            "education": ["onderwijs", "school", "studie", "duo", "studiefinanciering", "student"],
            "healthcare": ["zorg", "zorgverzekering", "ziekenhuis", "gezondheidszorg", "zorginstituut"],
            "pensions": ["pensioen", "aow", "svb", "ouderdomspensioen"],
            "travel": ["reis", "buitenland", "paspoort", "visum"],
            "housing": ["huisvesting", "woning", "huur", "hypotheek", "huurtoeslag"],
            "family": ["gezin", "gezinsbijslag", "kinderbijslag", "kinderen"],
            "transportation": ["rijbewijs", "rdw", "auto", "voertuig", "verkeer"],
            "digital_services": ["digid", "online", "digitaal"],
            "legal": ["recht", "rechter", "rechtspraak", "justitie"],
            "business": ["ondernemen", "bedrijf", "zakelijk", "ondernemer"],
        }
        
        # Score each source based on keyword matches
        for source in self.sources:
            score = 0
            title_desc = f"{source['title']} {source['description']}".lower()
            category = source.get("category", "")
            url_lower = source.get("url", "").lower()
            
            # Check direct query matches in title/description/URL
            query_words = query_lower.split()
            for word in query_words:
                if len(word) > 3:  # Only match meaningful words
                    if word in title_desc:
                        score += 3
                    if word in url_lower:
                        score += 2
            
            # Check category keyword matches
            if category in category_keywords:
                for keyword in category_keywords[category]:
                    if keyword in query_lower:
                        score += 5  # Strong match for category
            
            # Special handling for WOO queries
            if any(woo_kw in query_lower for woo_kw in ["woo", "wob", "wet openbaarheid"]):
                if category == "woo":
                    score += 10  # Very high priority for WOO category
            
            if score > 0:
                scored_sources.append((score, source))
        
        # Sort by score (highest first) and return top candidates
        scored_sources.sort(reverse=True, key=lambda x: x[0])
        return [source for _, source in scored_sources[:max_candidates]]
    
    def select_urls(self, query: str, max_urls: int = 5) -> List[str]:
        """
        Select relevant URLs from government sources based on the query.
        Uses keyword pre-filtering to narrow down candidates before Groq classification.
        
        Args:
            query: User's query/question
            max_urls: Maximum number of URLs to return
            
        Returns:
            List of selected URLs
        """
        try:
            # Pre-filter sources based on keywords to reduce the candidate pool
            logger.info(f"Pre-filtering sources for query: {query[:100]}...")
            candidate_sources = self._prefilter_sources(query, max_candidates=20)
            logger.info(f"Pre-filtered to {len(candidate_sources)} candidate sources from {len(self.sources)} total")
            
            if not candidate_sources:
                # If pre-filtering returns nothing, use keyword-based selection
                logger.warning("Pre-filtering returned no candidates, falling back to keyword-based selection")
                return self._keyword_based_selection(query, max_urls)
            
            # Build sources info only for candidates
            sources_info_lines = []
            for i, source in enumerate(candidate_sources, 1):
                sources_info_lines.append(
                    f"{i}. URL: {source['url']}\n"
                    f"   Title: {source['title']}\n"
                    f"   Description: {source['description']}\n"
                    f"   Category: {source.get('category', 'unknown')}\n"
                )
            sources_info = "\n".join(sources_info_lines)
            
            prompt = f"""You are helping select the most relevant Dutch government websites to crawl based on a user's question.

Available candidate sources (pre-filtered for relevance):
{sources_info}

User's question: "{query}"

Based on the user's question, select the most relevant URLs (up to {max_urls}) from the candidate list above that are likely to contain information to answer this question.

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
            
            # Get LLM response using Groq for fast classification
            logger.info(f"Using Groq to classify URLs for query: {query[:100]}...")
            
            # Check if Groq API key is available
            if not self.groq_service.api_key:
                error_msg = "GROQ_API_KEY is not set. Please set GROQ_API_KEY in your .env file to use web search."
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            response = self.groq_service.chat(messages, temperature=0.3, max_tokens=512)
            
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
            
            # If no URLs selected, raise error - we require Groq to work
            if not valid_urls:
                error_msg = f"Groq URL selection returned no valid URLs. Groq response: {response[:200]}"
                logger.error(error_msg)
                raise ValueError(f"No valid URLs selected by Groq. Response was: {response[:200]}")
            
            logger.info(f"Selected {len(valid_urls)} URLs for query: {query[:50]}...")
            return valid_urls
            
        except Exception as e:
            logger.error(f"Error in URL selection: {str(e)}")
            # Re-raise to let caller handle (no fallback)
            raise
    
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

