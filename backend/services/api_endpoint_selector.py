"""
API Endpoint Selector

Intelligent agent that analyzes user queries and determines:
- Which API endpoint to call
- What search parameters to use
- What filters to apply
"""

import json
import logging
from typing import Dict, Any, Optional
from services.groq_service import GroqService

logger = logging.getLogger(__name__)


class APIEndpointSelector:
    """AI agent for intelligently selecting API parameters based on user queries"""
    
    def __init__(self, groq_service: GroqService):
        """
        Initialize API endpoint selector
        
        Args:
            groq_service: GroqService instance for LLM queries
        """
        self.groq_service = groq_service
    
    def select_api_parameters(self, user_query: str) -> Dict[str, Any]:
        """
        Analyze user query and return optimal API parameters
        
        Args:
            user_query: User's search query
            
        Returns:
            Dict with keys: search_query, rows, filters, sort
        """
        
        system_prompt = """Je bent een expert in het analyseren van gebruikersvragen over Nederlandse overheidsinformatie.

Je taak is om de gebruikersvraag te analyseren en te bepalen welke zoekparameters het beste zijn voor de data.overheid.nl CKAN API.

**Beschikbare parameters:**
1. **search_query** (verplicht): De zoektermen voor de API (extracteer kernwoorden uit de vraag)
2. **rows** (optioneel): Aantal resultaten (standaard 10, max 20 voor complexe vragen)
3. **filters** (optioneel): Filters zoals organisatie, tags, etc.
   - Mogelijke organisaties: "rijksoverheid", "cbs", "ministerie-van-*", "uwv", etc.
   - Gebruik alleen als expliciet genoemd
4. **sort** (optioneel): Sorteeroptie
   - "metadata_modified desc" voor recent
   - "score desc" voor relevantie (standaard)

**Voorbeelden:**

Vraag: "Zoek WOO documenten over klimaatbeleid"
→ search_query: "WOO klimaat beleid"
→ rows: 10
→ filters: null
→ sort: null

Vraag: "Geef me recente datasets van CBS over bevolking"
→ search_query: "bevolking"
→ rows: 10
→ filters: {"organization": "cbs"}
→ sort: "metadata_modified desc"

Vraag: "Informatie over gezondheidszorg van het ministerie"
→ search_query: "gezondheidszorg ministerie"
→ rows: 10
→ filters: null
→ sort: null

Vraag: "Laatste 15 publicaties over onderwijs"
→ search_query: "onderwijs"
→ rows: 15
→ sort: "metadata_modified desc"

**BELANGRIJK:**
- Haal alleen kernwoorden uit de vraag (geen stopwoorden zoals "geef me", "zoek", "het", etc.)
- Gebruik Nederlandse termen zoals in de vraag
- Voeg "WOO" toe aan search_query als het om WOO-documenten gaat
- filters alleen gebruiken als organisatie expliciet genoemd wordt
- Maximaal 20 rows

**OUTPUT FORMAAT:**
Antwoord ALLEEN met een JSON object, geen extra tekst:

{
  "search_query": "kernwoorden hier",
  "rows": 10,
  "filters": null,
  "sort": null
}"""

        try:
            # Build prompt
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Analyseer deze vraag en geef de API parameters:\n\n{user_query}"}
            ]
            
            # Get LLM response
            logger.info(f"Analyzing query with AI agent: {user_query}")
            response = self.groq_service.chat(messages)
            
            # Parse JSON response
            # Try to extract JSON from response (handle cases where LLM adds extra text)
            response_clean = response.strip()
            
            # Find JSON object in response
            start_idx = response_clean.find('{')
            end_idx = response_clean.rfind('}')
            
            if start_idx == -1 or end_idx == -1:
                logger.error(f"No JSON found in response: {response}")
                return self._fallback_parameters(user_query)
            
            json_str = response_clean[start_idx:end_idx + 1]
            parameters = json.loads(json_str)
            
            # Validate and sanitize parameters
            search_query = parameters.get('search_query', user_query)
            rows = min(max(int(parameters.get('rows', 10)), 1), 20)  # Clamp between 1-20
            filters = parameters.get('filters')
            sort = parameters.get('sort')
            
            # Build result
            result = {
                'search_query': search_query,
                'rows': rows,
                'filters': filters if filters else None,
                'sort': sort if sort else None
            }
            
            logger.info(f"AI agent selected parameters: {result}")
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from LLM response: {response}, error: {str(e)}")
            return self._fallback_parameters(user_query)
        except Exception as e:
            logger.error(f"Error in select_api_parameters: {str(e)}")
            return self._fallback_parameters(user_query)
    
    def _fallback_parameters(self, user_query: str) -> Dict[str, Any]:
        """
        Fallback parameters when AI agent fails
        
        Args:
            user_query: User query
            
        Returns:
            Simple parameter dict
        """
        logger.warning(f"Using fallback parameters for query: {user_query}")
        
        # Simple keyword extraction (remove common Dutch stopwords)
        stopwords = {'de', 'het', 'een', 'is', 'zijn', 'van', 'in', 'op', 'voor', 'met', 
                     'aan', 'over', 'uit', 'bij', 'zoek', 'geef', 'vind', 'laat', 'zien',
                     'me', 'mij', 'naar', 'en', 'of', 'als', 'dan'}
        
        words = user_query.lower().split()
        keywords = [w for w in words if w not in stopwords and len(w) > 2]
        search_query = ' '.join(keywords) if keywords else user_query
        
        return {
            'search_query': search_query,
            'rows': 10,
            'filters': None,
            'sort': None
        }

