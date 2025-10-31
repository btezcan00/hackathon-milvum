#!/usr/bin/env python3
"""
Upload embeddings to Pinecone

Reads parsed_chunks_with_embeddings.json and uploads vectors to Pinecone index.
"""

import json
import os
from pinecone import Pinecone, ServerlessSpec
from typing import List, Dict
from tqdm import tqdm

def load_embeddings(file_path: str = "parsed_chunks_with_embeddings.json") -> List[Dict]:
    """
    Load embeddings from JSON file.

    Args:
        file_path: Path to the embeddings JSON file

    Returns:
        List of chunks with embeddings
    """
    print(f"Loading embeddings from {file_path}...")
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    print(f"✓ Loaded {len(data)} chunks with embeddings")
    return data


def upload_to_pinecone(
    chunks: List[Dict],
    index_name: str = "hackathon-milvum",
    batch_size: int = 100,
    namespace: str = ""
):
    """
    Upload chunks with embeddings to Pinecone.

    Args:
        chunks: List of chunks with text, metadata, and embeddings
        index_name: Name of the Pinecone index
        batch_size: Number of vectors to upload per batch
        namespace: Optional namespace for the vectors
    """
    # Get API key from environment
    api_key = os.getenv("PINECONE_API_KEY")
    if not api_key:
        raise ValueError("PINECONE_API_KEY environment variable not set")

    # Initialize Pinecone
    print("\nInitializing Pinecone...")
    pc = Pinecone(api_key=api_key)

    # Check if index exists
    existing_indexes = [index.name for index in pc.list_indexes()]

    if index_name not in existing_indexes:
        print(f"Index '{index_name}' not found. Creating new index...")

        # Get dimension from first embedding
        dimension = len(chunks[0]['embedding'])

        # Create index with serverless spec
        pc.create_index(
            name=index_name,
            dimension=dimension,
            metric="cosine",
            spec=ServerlessSpec(
                cloud="aws",
                region="us-east-1"
            )
        )
        print(f"✓ Created index '{index_name}' with dimension {dimension}")
    else:
        print(f"✓ Using existing index '{index_name}'")

    # Connect to index
    index = pc.Index(index_name)

    # Get index stats before upload
    stats = index.describe_index_stats()
    print(f"\nIndex stats before upload:")
    print(f"  Total vectors: {stats['total_vector_count']}")

    # Prepare vectors for upload
    print(f"\nPreparing {len(chunks)} vectors for upload...")
    vectors = []

    for idx, chunk in enumerate(chunks):
        vector_id = f"chunk_{idx}"

        # Prepare metadata (Pinecone has limits on metadata size)
        # Convert page_numbers to list of strings (Pinecone requirement)
        metadata = {
            "text": chunk["text"][:1000],  # Limit text to 1000 chars for metadata
            "document_name": chunk["metadata"]["document_name"],
            "page_numbers": [str(p) for p in chunk["metadata"]["page_numbers"]]
        }

        # Create vector tuple (id, values, metadata)
        vectors.append({
            "id": vector_id,
            "values": chunk["embedding"],
            "metadata": metadata
        })

    # Upload in batches
    print(f"\nUploading vectors in batches of {batch_size}...")

    for i in tqdm(range(0, len(vectors), batch_size)):
        batch = vectors[i:i + batch_size]
        index.upsert(vectors=batch, namespace=namespace)

    print(f"✓ Uploaded {len(vectors)} vectors to Pinecone")

    # Get index stats after upload
    stats = index.describe_index_stats()
    print(f"\nIndex stats after upload:")
    print(f"  Total vectors: {stats['total_vector_count']}")

    return index


def main():
    """Main function."""

    print("="*80)
    print("Upload Embeddings to Pinecone")
    print("="*80)

    # Configuration
    EMBEDDINGS_FILE = "parsed_chunks_with_embeddings.json"
    INDEX_NAME = "hackathon-milvum"
    BATCH_SIZE = 100
    NAMESPACE = ""  # Use default namespace (empty string)

    # Load embeddings
    chunks = load_embeddings(EMBEDDINGS_FILE)

    if not chunks:
        print("No chunks to upload!")
        return

    # Upload to Pinecone
    index = upload_to_pinecone(
        chunks=chunks,
        index_name=INDEX_NAME,
        batch_size=BATCH_SIZE,
        namespace=NAMESPACE
    )

    print("\n" + "="*80)
    print("✓ Upload complete!")
    print("="*80)

    # Test query (optional)
    print("\nTesting with a sample query...")
    try:
        results = index.query(
            vector=chunks[0]["embedding"],
            top_k=3,
            include_metadata=True,
            namespace=NAMESPACE
        )

        print(f"\nTop 3 results for first chunk:")
        for match in results['matches']:
            print(f"\n  ID: {match['id']}")
            print(f"  Score: {match['score']:.4f}")
            print(f"  Document: {match['metadata']['document_name']}")
            print(f"  Text preview: {match['metadata']['text'][:100]}...")
    except Exception as e:
        print(f"Could not run test query: {e}")


if __name__ == "__main__":
    main()
