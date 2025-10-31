#!/usr/bin/env python3
"""
Add embeddings to parsed chunks using OpenAI API.

Reads parsed_chunks.json and adds embeddings for each chunk.
"""

import json
import os
import time
import requests
from typing import List, Dict
from pathlib import Path


def get_embedding(text: str, api_key: str, model: str = "text-embedding-3-small") -> List[float]:
    """
    Get embedding for a text using OpenAI API.

    Args:
        text: Text to embed
        api_key: OpenAI API key
        model: Embedding model to use

    Returns:
        List of embedding values
    """
    url = "https://api.openai.com/v1/embeddings"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    data = {
        "model": model,
        "input": text,
        "encoding_format": "float"
    }

    max_retries = 3
    retry_delay = 2

    for attempt in range(max_retries):
        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)
            response.raise_for_status()

            result = response.json()

            # Extract embedding from response
            if 'data' in result and len(result['data']) > 0:
                return result['data'][0]['embedding']
            else:
                print(f"    Warning: Unexpected response format: {result}")
                return []

        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                print(f"    Retry {attempt + 1}/{max_retries} after error: {e}")
                time.sleep(retry_delay * (attempt + 1))
            else:
                print(f"    Failed after {max_retries} attempts: {e}")
                return []

    return []


def add_embeddings_to_chunks(
    input_file: str = "parsed_chunks.json",
    output_file: str = "parsed_chunks_with_embeddings.json",
    api_key: str = None,
    model: str = "text-embedding-3-small",
    max_chunks: int = None
):
    """
    Add embeddings to all chunks in the input file.

    Args:
        input_file: Input JSON file with chunks
        output_file: Output JSON file with embeddings
        api_key: OpenAI API key
        model: Embedding model to use
        max_chunks: Maximum number of chunks to process (None for all)
    """

    # Load chunks
    print(f"Loading chunks from {input_file}...")
    with open(input_file, 'r', encoding='utf-8') as f:
        chunks = json.load(f)

    total_chunks = len(chunks)
    if max_chunks:
        chunks = chunks[:max_chunks]
        print(f"Processing {len(chunks)} of {total_chunks} chunks")
    else:
        print(f"Processing all {total_chunks} chunks")

    print(f"Using model: {model}")
    print()

    # Process chunks
    chunks_with_embeddings = []
    successful = 0
    failed = 0

    start_time = time.time()

    for idx, chunk in enumerate(chunks, 1):
        doc_name = chunk['metadata']['document_name']
        print(f"[{idx}/{len(chunks)}] Processing chunk from '{doc_name[:50]}'...")

        # Combine document name with text for embedding
        # Format: "Document: [name]\n\n[text]"
        text_with_title = f"Document: {doc_name}\n\n{chunk['text']}"

        # Get embedding
        embedding = get_embedding(text_with_title, api_key, model)

        if embedding:
            # Add embedding to chunk
            chunk_with_embedding = {
                'text': chunk['text'],
                'metadata': chunk['metadata'],
                'embedding': embedding
            }
            chunks_with_embeddings.append(chunk_with_embedding)
            successful += 1
            print(f"  ✓ Embedded ({len(embedding)} dimensions)")
        else:
            # Keep chunk without embedding
            chunks_with_embeddings.append(chunk)
            failed += 1
            print(f"  ✗ Failed to get embedding")

        # Rate limiting - small delay between requests
        if idx % 10 == 0:
            time.sleep(0.5)

    # Save results
    print()
    print(f"Saving results to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(chunks_with_embeddings, f, ensure_ascii=False, indent=2)

    # Print statistics
    elapsed_time = time.time() - start_time
    file_size = os.path.getsize(output_file) / (1024 * 1024)  # MB

    print()
    print("="*80)
    print("Summary:")
    print("="*80)
    print(f"Total chunks processed: {len(chunks)}")
    print(f"Successful embeddings: {successful}")
    print(f"Failed embeddings: {failed}")
    print(f"Elapsed time: {elapsed_time:.2f} seconds")
    print(f"Output file size: {file_size:.2f} MB")
    print(f"Output file: {output_file}")
    print("="*80)


def main():
    """Main function."""

    # Configuration
    INPUT_FILE = "parsed_chunks.json"
    OUTPUT_FILE = "parsed_chunks_with_embeddings.json"

    # OpenAI Embedding model options:
    # - "text-embedding-3-small" (1536 dimensions, cost-effective, multilingual)
    # - "text-embedding-3-large" (3072 dimensions, higher quality, multilingual)
    # - "text-embedding-ada-002" (1536 dimensions, previous generation)
    MODEL = "text-embedding-3-small"  # Cost-effective OpenAI embedding for Dutch documents

    # Set to a number to test with limited chunks, or None to process all

    # Get API key from environment variable
    API_KEY = os.getenv('OPENAI_API_KEY')
    if not API_KEY:
        print("Error: OPENAI_API_KEY not found in environment")
        print("Set it with: export OPENAI_API_KEY='your-key-here'")
        return

    print("="*80)
    print("Add Embeddings to Parsed Chunks (OpenAI)")
    print("="*80)
    print()

    add_embeddings_to_chunks(
        input_file=INPUT_FILE,
        output_file=OUTPUT_FILE,
        model=MODEL,
        api_key=API_KEY
    )


if __name__ == "__main__":
    main()
