import cohere
import os
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class CohereReranker:
    def __init__(self, api_key: str = None, model: str = "rerank-english-v3.0"):
        """
        Initialize Cohere Reranker
        
        Args:
            api_key: Cohere API key
            model: Rerank model to use (rerank-english-v3.0, rerank-multilingual-v3.0)
        """
        self.api_key = api_key or os.getenv("COHERE_API_KEY")
        self.client = cohere.Client(self.api_key)
        self.model = model
        
    def rerank(
        self, 
        query: str, 
        documents: List[Dict[str, Any]], 
        top_n: int = 5,
        return_documents: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Rerank documents using Cohere's rerank API
        
        Args:
            query: The search query
            documents: List of document dicts with 'text' field
            top_n: Number of top documents to return after reranking
            return_documents: Whether to return full document content
            
        Returns:
            List of reranked documents with relevance scores
        """
        try:
            # Extract text from documents for reranking
            texts = [doc.get('text', '') for doc in documents]
            
            # Call Cohere rerank API
            results = self.client.rerank(
                model=self.model,
                query=query,
                documents=texts,
                top_n=top_n,
                return_documents=return_documents
            )
            
            # Combine reranked results with original metadata
            reranked_docs = []
            for result in results.results:
                original_doc = documents[result.index]
                reranked_docs.append({
                    'score': result.relevance_score,
                    'metadata': original_doc.get('metadata', {}),
                    'index': result.index
                })
            
            logger.info(f"Reranked {len(documents)} documents to top {top_n}")
            return reranked_docs
            
        except Exception as e:
            logger.error(f"Error reranking documents: {str(e)}")
            # Fallback: return original documents if reranking fails
            return documents[:top_n]