from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
from typing import List, Dict, Any
import uuid

class QdrantRAGClient:
    def __init__(self, host: str = "localhost", port: int = 6333):
        """Initialize Qdrant client for RAG operations"""
        self.client = QdrantClient(host=host, port=port)
        self.collection_name = "all_documents"
        
    def create_collection(self, vector_size: int = 1024, distance: Distance = Distance.COSINE):
        """
        Create a collection for storing document embeddings

        Args:
            vector_size: Dimension of embedding vectors (default 1024)
            distance: Distance metric (COSINE, EUCLID, DOT)
        """
        try:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=vector_size, distance=distance)
            )
            print(f"Collection '{self.collection_name}' created successfully")
        except Exception as e:
            print(f"Collection might already exist: {e}")
    
    def upsert_documents(self, documents: List[Dict[str, Any]], vectors: List[List[float]]):
        """
        Insert or update documents with their embeddings and metadata
        
        Args:
            documents: List of document metadata dicts
            vectors: List of embedding vectors
        
        Example document structure:
        {
            'text': 'Document content...',
            'source': 'file.pdf',
            'page': 1,
            'category': 'research',
            'date': '2024-01-01',
            'author': 'John Doe'
        }
        """
        points = []
        for i, (doc, vector) in enumerate(zip(documents, vectors)):
            point = PointStruct(
                id=str(uuid.uuid4()),
                vector=vector,
                payload=doc
            )
            points.append(point)
        
        self.client.upsert(
            collection_name=self.collection_name,
            points=points
        )
        print(f"Upserted {len(points)} documents")
    
    def search_with_metadata(
        self,
        query_vector: List[float],
        filters: Dict[str, Any] = None,
        limit: int = 5,
        score_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Search for similar vectors with metadata filtering
        
        Args:
            query_vector: Query embedding vector
            filters: Metadata filters (e.g., {'category': 'research', 'page': 1})
            limit: Number of results to return
            score_threshold: Minimum similarity score
        
        Returns:
            List of matching documents with scores
        """
        # Build filter conditions
        filter_conditions = None
        if filters:
            must_conditions = []
            for key, value in filters.items():
                must_conditions.append(
                    FieldCondition(key=key, match=MatchValue(value=value))
                )
            filter_conditions = Filter(must=must_conditions)
        
        # Perform search
        search_result = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            query_filter=filter_conditions,
            limit=limit,
            score_threshold=score_threshold
        )
        
        # Format results
        results = []
        for hit in search_result:
            results.append({
                'id': hit.id,
                'score': hit.score,
                'payload': hit.payload
            })
        
        return results
    
    def delete_by_filter(self, filters: Dict[str, Any]):
        """Delete documents matching metadata filters"""
        must_conditions = []
        for key, value in filters.items():
            must_conditions.append(
                FieldCondition(key=key, match=MatchValue(value=value))
            )
        
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=Filter(must=must_conditions)
        )
        print(f"Deleted documents matching filters: {filters}")
    
    def get_collection_info(self):
        """Get information about the collection"""
        info = self.client.get_collection(collection_name=self.collection_name)
        return info
