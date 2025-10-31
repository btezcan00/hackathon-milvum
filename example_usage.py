import openai
from sentence_transformers import SentenceTransformer
from client_qdrant import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
import os
from typing import List, Dict, Any
import uuid

class RAGPipeline:
    """Complete RAG pipeline with Qdrant"""
    
    def __init__(self, 
                 qdrant_host: str = "localhost",
                 qdrant_port: int = 6333,
                 embedding_model: str = "all-MiniLM-L6-v2"):
        """
        Initialize RAG pipeline
        
        Args:
            qdrant_host: Qdrant server host
            qdrant_port: Qdrant server port
            embedding_model: Sentence transformer model name
        """
        self.qdrant_client = QdrantClient(host=qdrant_host, port=qdrant_port)
        self.embedding_model = SentenceTransformer(embedding_model)
        self.collection_name = "rag_documents"
        self.vector_size = self.embedding_model.get_sentence_embedding_dimension()
        
    def setup_collection(self):
        """Create Qdrant collection if it doesn't exist"""
        try:
            self.qdrant_client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.vector_size,
                    distance=Distance.COSINE
                )
            )
            print(f"Collection created with vector size: {self.vector_size}")
        except Exception as e:
            print(f"Collection setup: {e}")
    
    def chunk_text(self, text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
        """Split text into chunks with overlap"""
        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]
            chunks.append(chunk)
            start += chunk_size - overlap
        return chunks
    
    def index_documents(self, documents: List[Dict[str, Any]]):
        """
        Index documents into Qdrant
        
        Args:
            documents: List of dicts with 'text' and optional metadata
            
        Example:
        [
            {
                'text': 'Long document text...',
                'source': 'doc.pdf',
                'category': 'research',
                'date': '2024-01-01'
            }
        ]
        """
        points = []
        
        for doc in documents:
            text = doc.get('text', '')
            chunks = self.chunk_text(text)
            
            for i, chunk in enumerate(chunks):
                # Generate embedding
                embedding = self.embedding_model.encode(chunk).tolist()
                
                # Prepare metadata
                payload = {
                    'text': chunk,
                    'chunk_index': i,
                    **{k: v for k, v in doc.items() if k != 'text'}
                }
                
                point = PointStruct(
                    id=str(uuid.uuid4()),
                    vector=embedding,
                    payload=payload
                )
                points.append(point)
        
        # Batch upsert
        batch_size = 100
        for i in range(0, len(points), batch_size):
            batch = points[i:i + batch_size]
            self.qdrant_client.upsert(
                collection_name=self.collection_name,
                points=batch
            )
        
        print(f"Indexed {len(points)} chunks from {len(documents)} documents")
    
    def retrieve(self,
                 query: str,
                 filters: Dict[str, Any] = None,
                 top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Retrieve relevant documents for a query
        
        Args:
            query: Search query
            filters: Metadata filters (e.g., {'category': 'research'})
            top_k: Number of results
            
        Returns:
            List of relevant chunks with metadata
        """
        # Generate query embedding
        query_vector = self.embedding_model.encode(query).tolist()
        
        # Build filters
        filter_conditions = None
        if filters:
            must_conditions = []
            for key, value in filters.items():
                must_conditions.append(
                    FieldCondition(key=key, match=MatchValue(value=value))
                )
            filter_conditions = Filter(must=must_conditions)
        
        # Search
        results = self.qdrant_client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            query_filter=filter_conditions,
            limit=top_k
        )
        
        return [
            {
                'text': hit.payload.get('text'),
                'score': hit.score,
                'metadata': {k: v for k, v in hit.payload.items() if k != 'text'}
            }
            for hit in results
        ]
    
    def generate_answer(self, query: str, context_docs: List[Dict[str, Any]]) -> str:
        """
        Generate answer using retrieved context (placeholder for LLM)
        
        Args:
            query: User question
            context_docs: Retrieved documents
            
        Returns:
            Generated answer
        """
        # Combine context
        context = "\n\n".join([doc['text'] for doc in context_docs])
        
        # This is a placeholder - integrate with your LLM (OpenAI, Anthropic, etc.)
        prompt = f"""Answer the question based on the context below.

Context:
{context}

Question: {query}

Answer:"""
        
        # Example with OpenAI (uncomment and add API key)
        # openai.api_key = os.getenv("OPENAI_API_KEY")
        # response = openai.ChatCompletion.create(
        #     model="gpt-4",
        #     messages=[{"role": "user", "content": prompt}]
        # )
        # return response.choices[0].message.content
        
        return f"[Placeholder answer - integrate your LLM here]\nContext retrieved from {len(context_docs)} sources"
    
    def rag_query(self,
                  query: str,
                  filters: Dict[str, Any] = None,
                  top_k: int = 5) -> Dict[str, Any]:
        """
        Complete RAG query: retrieve + generate
        
        Args:
            query: User question
            filters: Metadata filters
            top_k: Number of documents to retrieve
            
        Returns:
            Dict with answer and sources
        """
        # Retrieve relevant documents
        context_docs = self.retrieve(query, filters, top_k)
        
        # Generate answer
        answer = self.generate_answer(query, context_docs)
        
        return {
            'answer': answer,
            'sources': context_docs
        }


# Example usage for hackathon
if __name__ == "__main__":
    # Initialize RAG pipeline
    rag = RAGPipeline(qdrant_host="localhost", qdrant_port=6333)
    
    # Setup collection
    rag.setup_collection()
    
    # Example documents
    docs = [
        {
            'text': 'Machine learning is a subset of artificial intelligence that focuses on training algorithms to learn from data. It includes supervised learning, unsupervised learning, and reinforcement learning.',
            'source': 'ml_intro.pdf',
            'category': 'ML',
            'date': '2024-01-15'
        },
        {
            'text': 'Deep learning uses neural networks with multiple layers to process data. Popular frameworks include TensorFlow and PyTorch. It has revolutionized computer vision and natural language processing.',
            'source': 'dl_guide.pdf',
            'category': 'DL',
            'date': '2024-02-20'
        }
    ]
    
    # Index documents
    rag.index_documents(docs)
    
    # Query with metadata filter
    result = rag.rag_query(
        query="What is machine learning?",
        filters={'category': 'ML'},
        top_k=3
    )
    
    print("\nAnswer:", result['answer'])
    print("\nSources:")
    for i, source in enumerate(result['sources'], 1):
        print(f"{i}. Score: {source['score']:.3f}")
        print(f"   Text: {source['text'][:100]}...")
        print(f"   Metadata: {source['metadata']}\n")