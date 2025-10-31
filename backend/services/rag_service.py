import json
import os
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
from typing import List, Dict, Any
import uuid
import logging
import time
logger = logging.getLogger(__name__)

class RAGService:
    """RAG service integrating Qdrant and embeddings"""
    
    def __init__(self, embedding_service, qdrant_host: str = "qdrant", qdrant_port: int = 6333):
        """
        Initialize RAG service
        
        Args:
            embedding_service: EmbeddingService instance
            qdrant_host: Qdrant server host
            qdrant_port: Qdrant server port
        """
        self.embedding_service = embedding_service
        self.qdrant_host = qdrant_host
        self.qdrant_port = qdrant_port
        self.qdrant_client = QdrantClient(host=qdrant_host, port=qdrant_port)
        self.collection_name = "all_documents"
        self.vector_size = embedding_service.get_dimension()
        self._connect_with_retry()
        self.initialize()
        self._migrate_sample_data()  # Add migration here
        
    def _connect_with_retry(self, max_retries: int = 10, delay: int = 2):
        """Connect to Qdrant with retry logic"""
        for attempt in range(max_retries):
            try:
                logger.info(f"Attempting to connect to Qdrant at {self.qdrant_host}:{self.qdrant_port} (attempt {attempt + 1}/{max_retries})")
                self.qdrant_client = QdrantClient(host=self.qdrant_host, port=self.qdrant_port, timeout=10)
                # Test connection
                self.qdrant_client.get_collections()
                logger.info("Successfully connected to Qdrant")
                return
            except Exception as e:
                logger.warning(f"Connection attempt {attempt + 1} failed: {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(delay)
                else:
                    logger.error("Failed to connect to Qdrant after all retries")
                    raise
    
    def initialize(self):
        """Initialize Qdrant collection"""
        try:
            self.qdrant_client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.vector_size,
                    distance=Distance.COSINE
                )
            )
            logger.info(f"Collection '{self.collection_name}' created with dimension {self.vector_size}")
        except Exception as e:
            logger.info(f"Collection might already exist: {e}")
    
    def _migrate_sample_data(self):
        """Migrate sample data from JSON if available"""
        try:
            # Path to sample data
            script_dir = os.path.dirname(os.path.abspath(__file__))
            json_path = os.path.join(script_dir, "..", "migration", "sample_data.json")
            
            if not os.path.exists(json_path):
                logger.info("No sample data file found, skipping migration")
                return
            
            logger.info(f"Loading sample data from {json_path}")
            with open(json_path, "r") as f:
                data = json.load(f)
            
            # Check if collection already has data
            collection_info = self.qdrant_client.get_collection(self.collection_name)
            if collection_info.points_count > 0:
                logger.info(f"Collection already has {collection_info.points_count} points, skipping migration")
                return
            
            # Prepare points
            points = []
            for item in data:
                doc = item.copy()
                vector = doc.pop("embedding")  # Changed from "vector" to "embedding"
                
                point = PointStruct(
                    id=str(uuid.uuid4()),
                    vector=vector,
                    payload=doc
                )
                points.append(point)
            
            # Upsert to Qdrant
            self.qdrant_client.upsert(
                collection_name=self.collection_name,
                points=points
            )
            
            logger.info(f"Successfully migrated {len(points)} documents from sample data")
            
        except Exception as e:
            logger.warning(f"Migration failed (this is OK if no sample data): {str(e)}")
    
    def index_document(self, chunks: List[str], metadata: Dict[str, Any]) -> str:
        """
        Index document chunks into Qdrant
        
        Args:
            chunks: List of text chunks
            metadata: Document metadata (filename, source, etc.)
            
        Returns:
            Document ID
        """
        doc_id = str(uuid.uuid4())
        points = []
        
        # Generate embeddings for all chunks
        logger.info(f"Generating embeddings for {len(chunks)} chunks")
        embeddings = self.embedding_service.embed_batch(chunks)
        
        # Create points
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            point = PointStruct(
                id=str(uuid.uuid4()),
                vector=embedding,
                payload={
                    'text': chunk,
                    'doc_id': doc_id,
                    'chunk_index': i,
                    **metadata
                }
            )
            points.append(point)
        
        # Upsert to Qdrant
        self.qdrant_client.upsert(
            collection_name=self.collection_name,
            points=points
        )
        
        logger.info(f"Indexed document {doc_id} with {len(chunks)} chunks")
        return doc_id
    
    def query(self, query: str, top_k: int = 5, filters: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Query the RAG system
        
        Args:
            query: User query
            top_k: Number of chunks to retrieve
            filters: Optional metadata filters
            
        Returns:
            Dict with answer and sources
        """
        # Generate query embedding
        query_embedding = self.embedding_service.embed_text(query)
        
        # Build filters
        filter_conditions = None
        if filters:
            must_conditions = []
            for key, value in filters.items():
                must_conditions.append(
                    FieldCondition(key=key, match=MatchValue(value=value))
                )
            filter_conditions = Filter(must=must_conditions)
        
        # Search Qdrant
        results = self.qdrant_client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            query_filter=filter_conditions,
            limit=top_k
        )
        
        # Format sources
        sources = []
        context_texts = []
        
        for hit in results:
            sources.append({
                'text': hit.payload.get('text', ''),
                'score': hit.score,
                'filename': hit.payload.get('filename', 'Unknown'),
                'chunk_index': hit.payload.get('chunk_index', 0)
            })
            context_texts.append(hit.payload.get('text', ''))
        
        # Generate answer (simple context-based for demo)
        answer = self._generate_answer(query, context_texts)
        
        return {
            'answer': answer,
            'sources': sources
        }
    
    def _generate_answer(self, query: str, context_texts: List[str]) -> str:
        """
        Generate answer from context
        For hackathon demo, this is a simple implementation.
        In production, integrate with LLM (OpenAI, Anthropic, etc.)
        """
        if not context_texts:
            return "I couldn't find relevant information to answer your question. Please try rephrasing or upload more documents."
        
        # Simple demo response
        context = "\n\n".join(context_texts[:3])
        answer = f"""Based on the documents, here's what I found:

{context[:500]}...

This information comes from {len(context_texts)} relevant sections of your uploaded documents."""
        
        return answer
    
    def list_documents(self) -> List[Dict[str, Any]]:
        """List all indexed documents"""
        try:
            # Get collection info
            collection_info = self.qdrant_client.get_collection(self.collection_name)
            
            # For demo, return collection stats
            return [{
                'collection_name': self.collection_name,
                'points_count': collection_info.points_count,
                'status': 'active'
            }]
        except Exception as e:
            logger.error(f"Error listing documents: {str(e)}")
            return []
    
    def delete_document(self, doc_id: str):
        """Delete document by ID"""
        self.qdrant_client.delete(
            collection_name=self.collection_name,
            points_selector=Filter(
                must=[FieldCondition(key="doc_id", match=MatchValue(value=doc_id))]
            )
        )
        logger.info(f"Deleted document {doc_id}")
