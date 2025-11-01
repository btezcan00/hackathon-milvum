from pinecone import Pinecone, ServerlessSpec
from typing import List, Dict, Any
import uuid
import os

class PineconeRAGClient:
    def __init__(self, api_key: str = None):
        """Initialize Pinecone client for RAG operations"""
        self.api_key = api_key or os.getenv("PINECONE_API_KEY")
        self.pc = Pinecone(api_key=self.api_key)
        self.index_name = "hackathon-milvum"
        self.index = None
        
    def create_index(self, dimension: int = 1536, metric: str = "cosine"):
        """
        Create a Pinecone index for storing document embeddings
        
        Args:
            dimension: Dimension of embedding vectors (1536 for text-embedding-3-small)
            metric: Distance metric (cosine, euclidean, dotproduct)
        """
        try:
            if self.index_name not in self.pc.list_indexes().names():
                self.pc.create_index(
                    name=self.index_name,
                    dimension=dimension,
                    metric=metric,
                    spec=ServerlessSpec(
                        cloud='aws',
                    )
                )
                print(f"Index '{self.index_name}' created successfully")
            else:
                print(f"Index '{self.index_name}' already exists")
            
            self.index = self.pc.Index(self.index_name)
        except Exception as e:
            print(f"Error creating index: {e}")
    
    def upsert_documents(self, documents: List[Dict[str, Any]], vectors: List[List[float]]):
        """
        Insert or update documents with their embeddings and metadata
        
        Args:
            documents: List of document metadata dicts
            vectors: List of embedding vectors
        """
        if not self.index:
            self.index = self.pc.Index(self.index_name)
        
        vectors_to_upsert = []
        for doc, vector in zip(documents, vectors):
            vector_id = str(uuid.uuid4())
            vectors_to_upsert.append({
                "id": vector_id,
                "values": vector,
                "metadata": doc
            })
        
        self.index.upsert(vectors=vectors_to_upsert)
        print(f"Upserted {len(vectors_to_upsert)} documents")
    
    def search_with_metadata(
        self,
        query_vector: List[float],
        filters: Dict[str, Any] = None,
        top_k: int = 5,
        include_metadata: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Search for similar vectors with metadata filtering
        
        Args:
            query_vector: Query embedding vector
            filters: Metadata filters (e.g., {'category': 'research'})
            top_k: Number of results to return
            include_metadata: Whether to include metadata in results
        
        Returns:
            List of matching documents with scores
        """
        if not self.index:
            self.index = self.pc.Index(self.index_name)
        
        search_result = self.index.query(
            vector=query_vector,
            filter=filters,
            top_k=top_k,
            include_metadata=include_metadata
        )
        
        # Format results
        results = []
        for match in search_result['matches']:
            results.append({
                'id': match['id'],
                'score': match['score'],
                'payload': match.get('metadata', {})
            })
        
        return results
    
    def delete_by_filter(self, filters: Dict[str, Any]):
        """Delete documents matching metadata filters"""
        if not self.index:
            self.index = self.pc.Index(self.index_name)
        
        self.index.delete(filter=filters)
        print(f"Deleted documents matching filters: {filters}")
    
    def get_index_stats(self):
        """Get statistics about the index"""
        if not self.index:
            self.index = self.pc.Index(self.index_name)
        
        return self.index.describe_index_stats()