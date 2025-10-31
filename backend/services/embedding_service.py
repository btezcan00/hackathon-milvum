from typing import List
import logging

logger = logging.getLogger(__name__)

class EmbeddingService:
    """Service for generating text embeddings using sentence-transformers"""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize embedding service
        
        Args:
            model_name: Name of the sentence-transformer model to use
        """
        self.model_name = model_name
        self._model = None
        self._dimension = None
    
    def _load_model(self):
        """Lazy load the embedding model"""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                logger.info(f"Loading embedding model: {self.model_name}")
                self._model = SentenceTransformer(self.model_name)
                # Get dimension from model
                test_embedding = self._model.encode("test", show_progress_bar=False)
                self._dimension = len(test_embedding)
                logger.info(f"Model loaded with dimension: {self._dimension}")
            except ImportError as e:
                logger.error(f"Failed to import sentence-transformers: {str(e)}")
                raise ImportError(f"sentence-transformers is required for embeddings. Error: {str(e)}")
            except Exception as e:
                logger.error(f"Failed to load embedding model: {str(e)}")
                raise
    
    def get_dimension(self) -> int:
        """
        Get the dimension of the embedding vectors
        
        Returns:
            Embedding dimension
        """
        if self._dimension is None:
            self._load_model()
        return self._dimension
    
    def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for a single text
        
        Args:
            text: Input text to embed
            
        Returns:
            Embedding vector as list of floats
        """
        self._load_model()
        embedding = self._model.encode(text, show_progress_bar=False)
        return embedding.tolist()
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a batch of texts
        
        Args:
            texts: List of input texts to embed
            
        Returns:
            List of embedding vectors
        """
        self._load_model()
        embeddings = self._model.encode(texts, show_progress_bar=False, batch_size=32)
        return embeddings.tolist()

