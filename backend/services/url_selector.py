"""
Website Selection Service

This service uses LLM (agent) to intelligently select relevant government websites
based on the user's query. Instead of selecting individual URLs, it selects
websites (domains) which will then be crawled for multiple pages.
"""

import json
import logging
import requests
from typing import List, Dict, Any
from urllib.parse import urlparse
from services.groq_service import GroqService
from services.llm_service import ChatService
from services.government_sources import GOVERNMENT_SOURCES, get_sources_info

logger = logging.getLogger(__name__)


class URLSelector:
    def __init__(self, groq_service: GroqService = None, chat_service: ChatService = None):
        """
        Initialize website selector with LLM services for intelligent website selection.
        
        Args:
            groq_service: Optional GroqService instance. If not provided, creates a new one.
            chat_service: Optional ChatService instance for more capable reasoning. If not provided, creates a new one.
        """
        self.groq_service = groq_service or GroqService()
        self.chat_service = chat_service or ChatService()  # Use more capable model for selection
        self.sources = GOVERNMENT_SOURCES
        self._unique_websites = self._build_unique_websites()
    
    def _build_unique_websites(self) -> List[Dict[str, Any]]:
        """
        Build a list of unique websites (domains) with their entry URLs and descriptions.
        Groups multiple URLs from the same domain together.
        
        Returns:
            List of website dictionaries with domain, entry_urls, title, description, and categories
        """
        website_map = {}
        
        for source in self.sources:
            url = source.get("url", "")
            if not url:
                continue
            
            try:
                parsed = urlparse(url)
                domain = parsed.netloc.lower()
                # Remove www. prefix for grouping
                if domain.startswith("www."):
                    domain = domain[4:]
                
                if domain not in website_map:
                    website_map[domain] = {
                        "domain": domain,
                        "entry_urls": [],
                        "titles": [],
                        "descriptions": [],
                        "categories": set()
                    }
                
                website_map[domain]["entry_urls"].append(url)
                website_map[domain]["titles"].append(source.get("title", ""))
                website_map[domain]["descriptions"].append(source.get("description", ""))
                website_map[domain]["categories"].add(source.get("category", "general"))
            
            except Exception as e:
                logger.warning(f"Error parsing URL {url}: {e}")
                continue
        
        # Convert to list format
        websites = []
        for domain, data in website_map.items():
            # Get primary entry URL (usually the shortest or first one)
            entry_urls = sorted(data["entry_urls"], key=len)
            primary_url = entry_urls[0]
            
            # Combine descriptions
            unique_descriptions = list(set(data["descriptions"]))
            description = unique_descriptions[0] if unique_descriptions else ""
            if len(unique_descriptions) > 1:
                description += f" (and {len(unique_descriptions)-1} more related pages)"
            
            # Get primary title
            title = data["titles"][0] if data["titles"] else domain
            
            websites.append({
                "domain": domain,
                "entry_url": primary_url,
                "entry_urls": entry_urls,  # Keep all entry URLs for crawling
                "title": title,
                "description": description,
                "categories": list(data["categories"])
            })
        
        return websites
    
    def select_websites(self, query: str, max_websites: int = 2) -> List[Dict[str, Any]]:
        """
        Select relevant websites (domains) from government sources based on the query.
        Uses an agent (LLM) to intelligently choose which websites to crawl.
        Returns website dictionaries that can be used for multi-page crawling.
        
        Args:
            query: User's query/question
            max_websites: Maximum number of websites to select (default: 2 for focused crawling)
            
        Returns:
            List of selected website dictionaries with domain, entry_url, etc.
        """
        try:
            # Pre-filter websites based on keywords
            logger.info(f"Pre-filtering websites for query: {query[:100]}...")
            candidate_websites = self._prefilter_websites(query, max_candidates=15)
            logger.info(f"Pre-filtered to {len(candidate_websites)} candidate websites from {len(self._unique_websites)} total")
            
            if not candidate_websites:
                logger.warning("Pre-filtering returned no candidates, falling back to keyword-based selection")
                return self._keyword_based_website_selection(query, max_websites)
            
            # Build website info for LLM with more detail
            websites_info_lines = []
            for i, website in enumerate(candidate_websites, 1):
                categories_str = ", ".join(website.get("categories", []))
                websites_info_lines.append(
                    f"{i}. Domain: {website['domain']}\n"
                    f"   Entry URL: {website['entry_url']}\n"
                    f"   Title: {website['title']}\n"
                    f"   Description: {website['description']}\n"
                    f"   Categories: {categories_str}\n"
                )
            websites_info = "\n".join(websites_info_lines)
            
            # Extract location/keywords from query for better context
            query_lower = query.lower()
            
            prompt = f"""You are an expert Dutch government information specialist. Your task is to carefully analyze a user's question and select the most relevant government WEBSITES (domains) that will contain information to answer it.

CRITICAL INSTRUCTIONS:
1. Read the user's question VERY CAREFULLY, paying special attention to:
   - Location names (cities, municipalities, regions)
   - Specific topics or services mentioned
   - Context and intent of the question

2. For location-specific questions (e.g., questions about Haarlem, Amsterdam, Rotterdam, etc.), you MUST prioritize websites that are relevant to THAT SPECIFIC LOCATION. Do NOT select generic national websites if the question is about a specific city or municipality.

3. Match the question's topic, location, and intent precisely with the available websites.

Available candidate websites (each website can be crawled for multiple pages):
{websites_info}

User's question: "{query}"

ANALYSIS REQUIRED:
- What is the main topic of this question?
- Is there a specific location mentioned? (e.g., Haarlem, Amsterdam, Rotterdam, Utrecht, etc.)
- What type of information is the user seeking?

Based on your careful analysis, select the MOST RELEVANT WEBSITES (up to {max_websites}) from the candidate list above that are guaranteed to contain information to answer this SPECIFIC question.

IMPORTANT: 
- You are selecting WEBSITES (domains), not individual pages
- The crawler will automatically discover and crawl multiple relevant pages from each selected website
- Select websites that directly match the question's location, topic, and intent
- If the question mentions a specific city/municipality, prioritize that city's website over generic national sites

Respond with ONLY a JSON array of domain strings (e.g., ["rijksoverheid.nl", "ind.nl"]), nothing else. Example format:
["rijksoverheid.nl", "ind.nl"]

Selected websites (domains only):"""

            messages = [
                {
                    "role": "system",
                    "content": """You are an expert Dutch government information specialist with deep knowledge of Dutch government websites, municipalities, and public services. You excel at matching user questions to the most relevant government websites, especially when questions involve specific locations or municipalities. You always respond with valid JSON arrays only."""
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]
            
            # Use ChatService (GPT-4o-mini) for better reasoning instead of fast Groq model
            # This provides better understanding of context, locations, and nuanced queries
            logger.info(f"Using intelligent agent (ChatService) to select websites for query: {query[:100]}...")
            
            # Check if OpenAI API key is available (ChatService uses OpenAI)
            if not self.chat_service.api_key:
                # Fallback to Groq if ChatService not available
                logger.warning("OpenAI API key not available, falling back to Groq for website selection")
                if not self.groq_service.api_key:
                    error_msg = "Neither OPENAI_API_KEY nor GROQ_API_KEY is set. Please set at least one API key in your .env file."
                    logger.error(error_msg)
                    raise ValueError(error_msg)
                response = self.groq_service.chat(messages, temperature=0.4, max_tokens=1024)
            else:
                # Use ChatService for better reasoning
                response = self.chat_service.chat(messages)
            
            # Parse JSON response
            response = response.strip()
            
            # Remove markdown code blocks if present
            if response.startswith("```"):
                lines = response.split("\n")
                response = "\n".join(lines[1:-1]) if len(lines) > 2 else response
            
            # Parse JSON
            try:
                selected_domains = json.loads(response)
                if not isinstance(selected_domains, list):
                    logger.warning(f"Agent returned non-list response: {response}")
                    selected_domains = []
            except json.JSONDecodeError:
                # Try to extract domains manually if JSON parsing fails
                logger.warning(f"Failed to parse JSON from agent response: {response}")
                selected_domains = self._extract_domains_from_text(response)
            
            # Map domains back to website dictionaries
            domain_to_website = {w["domain"]: w for w in self._unique_websites}
            valid_websites = []
            
            for domain in selected_domains:
                # Normalize domain (remove www. if present)
                domain = domain.lower().strip()
                if domain.startswith("www."):
                    domain = domain[4:]
                
                if domain in domain_to_website:
                    valid_websites.append(domain_to_website[domain])
                else:
                    # Try to find closest match
                    matched = self._find_closest_domain(domain, domain_to_website.keys())
                    if matched:
                        valid_websites.append(domain_to_website[matched])
            
            # Remove duplicates while preserving order
            seen = set()
            unique_websites = []
            for website in valid_websites:
                if website["domain"] not in seen:
                    seen.add(website["domain"])
                    unique_websites.append(website)
            
            # Limit to max_websites
            unique_websites = unique_websites[:max_websites]
            
            # If no websites selected, raise error
            if not unique_websites:
                error_msg = f"Agent website selection returned no valid websites. Agent response: {response[:200]}"
                logger.error(error_msg)
                raise ValueError(f"No valid websites selected by agent. Response was: {response[:200]}")
            
            logger.info(f"Agent selected {len(unique_websites)} websites for query: {query[:50]}...")
            for website in unique_websites:
                logger.info(f"  - {website['domain']} (entry: {website['entry_url']})")
            
            return unique_websites
            
        except Exception as e:
            logger.error(f"Error in website selection: {str(e)}")
            raise
    
    def _prefilter_websites(self, query: str, max_candidates: int = 15) -> List[Dict[str, Any]]:
        """
        Pre-filter websites based on keyword matching before sending to agent.
        This reduces the number of websites passed to the LLM.
        
        Args:
            query: User's query
            max_candidates: Maximum number of candidate websites to return
            
        Returns:
            Filtered list of website dictionaries
        """
        query_lower = query.lower()
        scored_websites = []
        
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
        
        # Extract location names from query (common Dutch cities and municipalities)
        dutch_cities = [
            "haarlem", "amsterdam", "rotterdam", "den haag", "utrecht", "eindhoven",
            "groningen", "tilburg", "almere", "breda", "nijmegen", "enschede",
            "arnhem", "zaanstad", "amersfoort", "apeldoorn", "hoofddorp",
            "haarlemmermeer", "leiden", "delft", "gouda", "schiedam", "dordrecht",
            "alkmaar", "heerlen", "venlo", "zoetermeer", "maastricht", "deventer",
            "sittard-geleen", "leeuwarden", "helmond", "almelo", "zaandam", "hoorn",
            "katwijk", "roosendaal", "vlaardingen", "capelle", "ede", "middelburg"
        ]
        
        query_location = None
        for city in dutch_cities:
            if city in query_lower:
                query_location = city
                break
        
        # Score each website based on keyword matches
        for website in self._unique_websites:
            score = 0
            title_desc = f"{website['title']} {website['description']}".lower()
            domain_lower = website['domain'].lower()
            categories = website.get("categories", [])
            
            # PRIORITY: Location-specific matching (very high weight)
            if query_location:
                # Check if website title/domain/description mentions the location
                if query_location in title_desc:
                    score += 50  # Very high priority for exact location match
                elif query_location in domain_lower:
                    score += 40  # High priority for location in domain
                elif any(query_location in word for word in title_desc.split()):
                    score += 30  # Good match for location in title/description
            
            # Check direct query matches in title/description/domain
            query_words = query_lower.split()
            for word in query_words:
                if len(word) > 3:  # Only match meaningful words
                    if word in title_desc:
                        score += 3
                    if word in domain_lower:
                        score += 2
            
            # Check category keyword matches
            for category in categories:
                if category in category_keywords:
                    for keyword in category_keywords[category]:
                        if keyword in query_lower:
                            score += 5  # Strong match for category
            
            # Special handling for WOO queries
            if any(woo_kw in query_lower for woo_kw in ["woo", "wob", "wet openbaarheid"]):
                if "woo" in categories:
                    score += 10  # Very high priority for WOO category
            
            # Penalty: If query mentions specific location but website mentions different location
            if query_location:
                other_cities = [c for c in dutch_cities if c != query_location]
                for other_city in other_cities:
                    if other_city in title_desc or other_city in domain_lower:
                        score -= 20  # Penalty for mismatched location
            
            if score > 0:
                scored_websites.append((score, website))
        
        # Sort by score (highest first) and return top candidates
        scored_websites.sort(reverse=True, key=lambda x: x[0])
        return [website for _, website in scored_websites[:max_candidates]]
    
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
    
    def _extract_domains_from_text(self, text: str) -> List[str]:
        """Extract domain names from text using pattern matching."""
        import re
        # Match domain patterns like "rijksoverheid.nl" or "www.ind.nl"
        domains = re.findall(r'(?:www\.)?([a-z0-9](?:[a-z0-9\-]{0,61}[a-z0-9])?\.(?:nl|com|org|net|gov|eu))', text.lower())
        # Remove duplicates while preserving order
        seen = set()
        unique_domains = []
        for domain in domains:
            if domain not in seen:
                seen.add(domain)
                unique_domains.append(domain)
        return unique_domains[:5]
    
    def _find_closest_domain(self, domain: str, valid_domains: set) -> str:
        """Find closest matching domain from valid set."""
        # Normalize
        domain = domain.lower().strip()
        if domain.startswith("www."):
            domain = domain[4:]
        
        # Try exact match first
        if domain in valid_domains:
            return domain
        
        # Try substring matching
        for valid_domain in valid_domains:
            if domain in valid_domain or valid_domain in domain:
                return valid_domain
        
        return None
    
    def _keyword_based_website_selection(self, query: str, max_websites: int) -> List[Dict[str, Any]]:
        """
        Fallback keyword-based website selection.
        Uses simple keyword matching when agent selection fails.
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
        
        # Score websites based on keyword matches
        scored_websites = []
        for website in self._unique_websites:
            score = 0
            title_desc = f"{website['title']} {website['description']}".lower()
            categories = website.get("categories", [])
            
            # Check category keywords
            for category in categories:
                if category in category_keywords:
                    for keyword in category_keywords[category]:
                        if keyword in query_lower:
                            score += 2
            
            # Check direct matches in title/description
            for word in query_lower.split():
                if len(word) > 3 and word in title_desc:
                    score += 1
            
            if score > 0:
                scored_websites.append((score, website))
        
        # Sort by score and return top websites
        scored_websites.sort(reverse=True, key=lambda x: x[0])
        return [website for _, website in scored_websites[:max_websites]]
    
    # Keep the old select_urls method for backwards compatibility, but mark as deprecated
    def select_urls(self, query: str, max_urls: int = 5) -> List[str]:
        """
        DEPRECATED: Use select_websites() instead.
        Select relevant URLs from government sources based on the query.
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

