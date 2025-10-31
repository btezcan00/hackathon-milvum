import requests
from typing import List, Optional, Dict, Any
import os

SILICONFLOW_API_URL = "https://api.siliconflow.com/v1/embeddings"
SILICONFLOW_MODEL = "Qwen/Qwen3-Embedding-8B"
SILICONFLOW_CHAT_URL = "https://api.siliconflow.com/v1/chat/completions"
SILICONFLOW_CHAT_MODEL = "Qwen/QwQ-32B"

class EmbeddingService:
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or os.getenv("SILICONFLOW_API_KEY")
        self.model = model or SILICONFLOW_MODEL
        self.api_url = SILICONFLOW_API_URL
        self.dimension = 1024  # Qwen3-Embedding-8B dimension
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def get_dimension(self) -> int:
        """Get embedding dimension"""
        return self.dimension

    def embed_text(self, text: str) -> List[float]:
        """Get embedding for a single string (alias for get_embedding)"""
        return self.get_embedding(text)

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings for a list of strings (alias for get_embeddings)"""
        return self.get_embeddings(texts)

    def get_embedding(self, text: str) -> List[float]:
        """Get embedding for a single string."""
        payload = {
            "model": self.model,
            "input": text,
            "dimensions": self.dimension
        }
        response = requests.post(self.api_url, headers=self.headers, json=payload)
        response.raise_for_status()
        data = response.json()
        return data['data'][0]['embedding']

    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings for a list of strings (batch)."""
        payload = {
            "model": self.model,
            "input": texts,
            "dimensions": self.dimension
        }
        response = requests.post(self.api_url, headers=self.headers, json=payload)
        response.raise_for_status()
        data = response.json()
        return [item['embedding'] for item in data['data']]


class ChatService:
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or os.getenv("SILICONFLOW_API_KEY")
        self.model = model or SILICONFLOW_CHAT_MODEL
        self.api_url = SILICONFLOW_CHAT_URL
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def chat(self, messages: List[Dict[str, str]]) -> str:
        payload = {
            "model": self.model,
            "messages": messages
        }
        response = requests.post(self.api_url, headers=self.headers, json=payload)
        response.raise_for_status()
        data = response.json()
        return data['choices'][0]['message']['content']