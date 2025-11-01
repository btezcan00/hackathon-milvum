import uuid
import logging
from typing import List, Dict, Any
from datetime import datetime
from urllib.parse import urlparse
import numpy as np

logger = logging.getLogger(__name__)

class CitationService:
    """Service for processing, scoring, and formatting citations"""
    
    def __init__(self, embedding_service):
        """
        Initialize citation service
        
        Args:
            embedding_service: EmbeddingService instance for relevance scoring
        """
        self.embedding_service = embedding_service
    
    def _calculate_cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """
        Calculate cosine similarity between two vectors
        
        Args:
            vec1: First vector
            vec2: Second vector
            
        Returns:
            Cosine similarity score (0-1)
        """
        try:
            vec1 = np.array(vec1)
            vec2 = np.array(vec2)
            
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            similarity = dot_product / (norm1 * norm2)
            # Normalize to 0-1 range (cosine similarity is -1 to 1, but embeddings are typically 0-1)
            return max(0.0, min(1.0, (similarity + 1) / 2))
        except Exception as e:
            logger.error(f"Error calculating cosine similarity: {str(e)}")
            return 0.0
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL"""
        try:
            parsed = urlparse(url)
            return parsed.netloc.lower()
        except Exception:
            return ""
    
    def _extract_snippet(self, text: str, max_length: int = 300) -> str:
        """
        Extract a snippet from text
        
        Args:
            text: Full text
            max_length: Maximum snippet length
            
        Returns:
            Snippet text
        """
        if not text:
            return ""
        
        text = text.strip()
        if len(text) <= max_length:
            return text
        
        # Try to break at word boundary
        snippet = text[:max_length]
        last_space = snippet.rfind(' ')
        if last_space > max_length * 0.7:  # If we have a good break point
            snippet = snippet[:last_space] + "..."
        else:
            snippet = snippet + "..."
        
        return snippet
    
    def score_citations(
        self,
        query: str,
        crawled_content: List[Dict[str, Any]],
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Score crawled content by relevance to query
        
        Args:
            query: User query
            crawled_content: List of crawled content dictionaries
            top_k: Number of top results to return
            
        Returns:
            List of scored content sorted by relevance (descending)
        """
        if not crawled_content:
            return []
        
        logger.info(f"Scoring {len(crawled_content)} citations for query: {query}")
        
        try:
            # Generate query embedding
            query_embedding = self.embedding_service.embed_text(query)
            
            # Score each piece of content
            scored_content = []
            for content in crawled_content:
                try:
                    # Generate embedding for content text
                    content_text = content.get('text', '')
                    if not content_text:
                        continue
                    
                    # Use first 1000 chars for embedding (to stay within token limits)
                    embedding_text = content_text[:1000]
                    content_embedding = self.embedding_service.embed_text(embedding_text)
                    
                    # Calculate similarity score
                    score = self._calculate_cosine_similarity(query_embedding, content_embedding)
                    
                    scored_content.append({
                        **content,
                        'relevance_score': score
                    })
                    
                except Exception as e:
                    logger.error(f"Error scoring citation {content.get('url', 'unknown')}: {str(e)}")
                    continue
            
            # Sort by relevance score (descending)
            scored_content.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
            
            # Return top_k results
            top_results = scored_content[:top_k]
            logger.info(f"Scored {len(top_results)} top citations (scores: {[r.get('relevance_score', 0) for r in top_results]})")
            
            return top_results
            
        except Exception as e:
            logger.error(f"Error scoring citations: {str(e)}")
            return []
    
    def format_citations(
        self,
        scored_content: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Format scored content into citation objects
        
        Args:
            scored_content: List of scored content dictionaries
            
        Returns:
            List of formatted citation dictionaries
        """
        citations = []
        
        for content in scored_content:
            try:
                citation = {
                    'id': str(uuid.uuid4()),
                    'url': content.get('url', ''),
                    'title': content.get('title', 'Untitled'),
                    'snippet': self._extract_snippet(content.get('text', ''), max_length=300),
                    'relevanceScore': content.get('relevance_score', 0),
                    'domain': content.get('domain', self._extract_domain(content.get('url', ''))),
                    'crawledAt': content.get('extracted_at', datetime.now().isoformat()),
                    'highlightText': content.get('text', '')  # Full text for PDF highlighting
                }
                
                # Add optional downloadUrl field for government datasets
                if 'downloadUrl' in content and content['downloadUrl']:
                    citation['downloadUrl'] = content['downloadUrl']
                
                # Add optional publisher/organization field
                if 'publisher' in content and content['publisher']:
                    citation['publisher'] = content['publisher']
                
                # Add optional format field
                if 'format' in content and content['format']:
                    citation['format'] = content['format']
                
                # Add optional type field (e.g., 'government_dataset', 'web_page')
                if 'type' in content and content['type']:
                    citation['type'] = content['type']
                
                # Add optional published/modified dates
                if 'publishedDate' in content and content['publishedDate']:
                    citation['publishedDate'] = content['publishedDate']
                if 'modifiedDate' in content and content['modifiedDate']:
                    citation['modifiedDate'] = content['modifiedDate']
                
                citations.append(citation)
            except Exception as e:
                logger.error(f"Error formatting citation: {str(e)}")
                continue
        
        return citations
    
    def deduplicate_citations(self, citations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Remove duplicate citations based on URL
        
        Args:
            citations: List of citation dictionaries
            
        Returns:
            Deduplicated list of citations
        """
        seen_urls = set()
        unique_citations = []
        
        for citation in citations:
            url = citation.get('url', '').lower()
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_citations.append(citation)
        
        logger.info(f"Deduplicated {len(citations)} citations to {len(unique_citations)} unique")
        return unique_citations
    
    def process_citations(
        self,
        query: str,
        crawled_content: List[Dict[str, Any]],
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Complete citation processing pipeline: score, format, and deduplicate
        
        Args:
            query: User query
            crawled_content: List of crawled content dictionaries
            top_k: Number of top citations to return
            
        Returns:
            List of processed citation dictionaries
        """
        # Score citations
        scored = self.score_citations(query, crawled_content, top_k=top_k)
        
        # Format citations
        formatted = self.format_citations(scored)
        
        # Deduplicate
        unique = self.deduplicate_citations(formatted)
        
        return unique

