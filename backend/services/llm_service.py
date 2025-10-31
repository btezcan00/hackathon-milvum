import requests
from typing import List, Optional, Dict, Any, Iterator
import os
import json

SILICONFLOW_API_URL = "https://api.siliconflow.com/v1/embeddings"
SILICONFLOW_MODEL = "Qwen/Qwen3-Embedding-8B"
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "openai/gpt-oss-safeguard-20b"

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
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        self.model = model or GROQ_MODEL
        self.api_url = GROQ_API_URL
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def chat(self, messages: List[Dict[str, str]]) -> str:
        """Non-streaming chat response"""
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.6,
            "max_tokens": 4096,
            "top_p": 0.95
        }
        response = requests.post(self.api_url, headers=self.headers, json=payload)
        response.raise_for_status()
        data = response.json()
        return data['choices'][0]['message']['content']
    
    def chat_stream(self, messages: List[Dict[str, str]]) -> Iterator[str]:
        """Streaming chat response"""
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.6,
            "max_tokens": 4096,
            "top_p": 0.95,
            "stream": True
        }
        
        response = requests.post(self.api_url, headers=self.headers, json=payload, stream=True)
        response.raise_for_status()
        
        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                if line_str.startswith('data: '):
                    data_str = line_str[6:]  # Remove 'data: ' prefix
                    if data_str.strip() == '[DONE]':
                        break
                    try:
                        data = json.loads(data_str)
                        if 'choices' in data and len(data['choices']) > 0:
                            delta = data['choices'][0].get('delta', {})
                            if 'content' in delta:
                                yield delta['content']
                    except json.JSONDecodeError:
                        continue