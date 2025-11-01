import json
import os
from services.pinecone_service import PineconeRAGClient
from services.cohere_rerank import CohereReranker
from typing import List, Dict, Any
import uuid
import logging
import time

logger = logging.getLogger(__name__)

class RAGService:
    """RAG service integrating Pinecone, embeddings, and Cohere reranking"""
    
    def __init__(self, embedding_service, api_key: str = None, use_reranking: bool = True):
        """
        Initialize RAG service
        
        Args:
            embedding_service: EmbeddingService instance
            api_key: Pinecone API key
            use_reranking: Whether to use Cohere reranking
        """
        self.embedding_service = embedding_service
        self.pinecone_client = PineconeRAGClient(api_key=api_key)
        self.vector_size = embedding_service.get_dimension()
        self.use_reranking = use_reranking
        
        # Initialize Cohere reranker if enabled
        if self.use_reranking:
            self.reranker = CohereReranker()
        
        self.initialize()
        self._migrate_sample_data()
        
    def initialize(self):
        """Initialize Pinecone index"""
        try:
            self.pinecone_client.create_index(dimension=self.vector_size, metric="cosine")
            logger.info(f"Pinecone index initialized with dimension {self.vector_size}")
        except Exception as e:
            logger.error(f"Error initializing Pinecone index: {e}")
    
    def _migrate_sample_data(self):
        """Migrate sample data from JSON if available"""
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            json_path = os.path.join(script_dir, "..", "migration", "first.json")
            
            if not os.path.exists(json_path):
                logger.info("No first.json file found, skipping migration")
                return
            
            logger.info(f"Loading sample data from {json_path}")
            with open(json_path, "r") as f:
                data = json.load(f)
            
            # Check if index already has data
            stats = self.pinecone_client.get_index_stats()
            if stats.total_vector_count > 0:
                logger.info(f"Index already has {stats.total_vector_count} vectors, skipping migration")
                return
            
            # Prepare documents and vectors
            documents = []
            vectors = []
            for item in data:
                doc = item.copy()
                vector = doc.pop("embedding")
                
                # Flatten metadata if present
                metadata = doc.pop("metadata", {})
                if isinstance(metadata, dict):
                    doc.update(metadata)
                
                documents.append(doc)
                vectors.append(vector)
            
            # Upsert to Pinecone
            self.pinecone_client.upsert_documents(documents, vectors)
            logger.info(f"Successfully migrated {len(documents)} documents from first.json")
            
        except Exception as e:
            logger.warning(f"Migration failed (this is OK if no sample data): {str(e)}")
    
    def index_document(self, chunks: List[str], metadata: Dict[str, Any]) -> str:
        """
        Index document chunks into Pinecone
        
        Args:
            chunks: List of text chunks
            metadata: Document metadata
            
        Returns:
            Document ID
        """
        doc_id = str(uuid.uuid4())
        documents = []
        
        # Generate embeddings for all chunks
        logger.info(f"Generating embeddings for {len(chunks)} chunks")
        embeddings = self.embedding_service.embed_batch(chunks)
        
        # Prepare documents
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            doc = {
                'text': chunk,
                'doc_id': doc_id,
                'chunk_index': i,
                **metadata
            }
            documents.append(doc)
        
        # Upsert to Pinecone
        self.pinecone_client.upsert_documents(documents, embeddings)
        logger.info(f"Indexed document {doc_id} with {len(chunks)} chunks")
        return doc_id
    
    def query(self, query: str, top_k: int = 5, initial_k: int = 30, filters: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Query the RAG system with optional reranking
        
        Args:
            query: User query
            top_k: Number of final chunks to return (after reranking)
            initial_k: Number of chunks to retrieve from Pinecone before reranking
            filters: Optional metadata filters
            
        Returns:
            Dict with answer and sources
        """
        # Generate query embedding
        query_embedding = self.embedding_service.embed_text(query)
        
        # Search Pinecone - get more results for reranking
        search_k = initial_k if self.use_reranking else top_k
        results = self.pinecone_client.search_with_metadata(
            query_vector=query_embedding,
            filters=filters,
            top_k=search_k
        )
        
        logger.info(f"Retrieved {len(results)} results from Pinecone for query: '{query}'")
        
        # Format sources
        sources = []
        for result in results:
            sources.append({
                'text': result['payload'].get('text', ''),
                'score': result['score'],
                'metadata': result['payload']
            })
        
        # Apply Cohere reranking if enabled
        if self.use_reranking and len(sources) > 0:
            logger.info(f"Reranking {len(sources)} documents with Cohere")
            sources = self.reranker.rerank(
                query=query,
                documents=sources,
                top_n=top_k
            )
            logger.info(f"Reranked to top {len(sources)} documents")
        
        # Generate answer
        if not sources:
            answer = "I couldn't find relevant information to answer your question. Please try rephrasing or upload more documents."
        else:
            answer = "Based on the retrieved documents, here's what I found..."  # Placeholder
        
        return {
            'answer': answer,
            'sources': sources
        }
    