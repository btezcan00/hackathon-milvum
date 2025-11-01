"""
Groq Service - Fast LLM service using Groq API for classification tasks
"""

import requests
from typing import List, Dict, Any, Optional
import os
import json
import logging

logger = logging.getLogger(__name__)

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.1-8b-instant"  # Fast, small model for classification

class GroqService:
    """Fast LLM service using Groq API for quick classification tasks"""
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize Groq service
        
        Args:
            api_key: Groq API key (defaults to GROQ_API_KEY env var)
            model: Model to use (defaults to llama-3.1-8b-instant)
        """
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        self.model = model or GROQ_MODEL
        self.api_url = GROQ_API_URL
        
        if not self.api_key:
            logger.error("GROQ_API_KEY not found in environment variables. Web search requires Groq API key.")
            logger.error("Please set GROQ_API_KEY in your .env file. Get your key from: https://console.groq.com/keys")
        
        self.headers = {
            "Authorization": f"Bearer {self.api_key}" if self.api_key else None,
            "Content-Type": "application/json"
        }
    
    def chat(self, messages: List[Dict[str, str]], temperature: float = 0.3, max_tokens: int = 1024) -> str:
        """
        Fast chat completion using Groq
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Temperature for generation (lower = more deterministic)
            max_tokens: Maximum tokens in response
            
        Returns:
            Response text
        """
        if not self.api_key:
            error_msg = "GROQ_API_KEY is required but not set. Please set it in your .env file. Get your key from: https://console.groq.com/keys"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        try:
            response = requests.post(self.api_url, headers=self.headers, json=payload, timeout=10)
            response.raise_for_status()
            data = response.json()
            return data['choices'][0]['message']['content']
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                error_msg = "Groq API returned 403 Forbidden. This usually means:\n1. GROQ_API_KEY is incorrect or expired\n2. Your API key doesn't have proper permissions\n3. Check https://console.groq.com/keys to verify your key"
                logger.error(error_msg)
                if hasattr(e.response, 'text'):
                    logger.error(f"Groq API response: {e.response.text}")
                raise ValueError(error_msg) from e
            else:
                logger.error(f"Groq API HTTP error {e.response.status_code}: {str(e)}")
                if hasattr(e.response, 'text'):
                    logger.error(f"Response: {e.response.text}")
                raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Groq API request error: {str(e)}")
            raise ValueError(f"Failed to connect to Groq API: {str(e)}. Check your network connection and API key.") from e
        except (KeyError, IndexError) as e:
            logger.error(f"Unexpected Groq API response format: {str(e)}")
            raise ValueError(f"Unexpected response from Groq API: {str(e)}") from e

