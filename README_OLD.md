# Qdrant Vector Database for RAG with Metadata Filtering

This project provides a complete setup for using Qdrant vector database for Retrieval-Augmented Generation (RAG) with advanced metadata filtering capabilities.

## Features

- ✅ Docker-based Qdrant deployment
- ✅ Vector search with cosine similarity
- ✅ Metadata filtering (exact match, range, multiple values)
- ✅ Easy-to-use Python client wrapper
- ✅ Sentence transformer embeddings
- ✅ Complete examples

## Quick Start

### 1. Start Qdrant with Docker

```bash
docker-compose up -d
```

This will:
- Start Qdrant on ports 6333 (REST API) and 6334 (gRPC)
- Create persistent storage in `./qdrant_storage`
- Enable auto-restart

Check if Qdrant is running:
```bash
curl http://localhost:6333/
```

### 2. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 3. Run Examples

```bash
python example_usage.py
```

## Project Structure

```
.
├── docker-compose.yml          # Docker configuration for Qdrant
├── .env                        # Environment variables
├── requirements.txt            # Python dependencies
├── qdrant_client.py           # Main Qdrant client wrapper
├── qdrant_client_wrapper.py   # Re-export module
├── example_usage.py           # Usage examples
└── README.md                  # This file
```

## Usage

### Initialize Client

```python
from qdrant_client_wrapper import QdrantRAGClient

# Initialize with default settings from .env
rag_client = QdrantRAGClient()

# Or with custom settings
rag_client = QdrantRAGClient(
    host="localhost",
    port=6333,
    collection_name="my_collection",
    vector_size=384
)
```

### Create Collection

```python
from qdrant_client.models import Distance

rag_client.create_collection(
    collection_name="documents",
    vector_size=384,
    distance=Distance.COSINE,
    recreate=True  # Delete if exists
)
```

### Insert Documents

```python
documents = [
    {
        "id": 1,
        "vector": [0.1, 0.2, ...],  # 384-dimensional vector
        "metadata": {
            "text": "Document text",
            "source": "pdf",
            "page": 1,
            "category": "technical",
            "author": "John Doe",
            "year": 2023
        }
    },
    # More documents...
]

rag_client.insert_documents(documents)
```

### Search with Metadata Filtering

#### Basic Search (No Filter)
```python
results = rag_client.search(
    query_vector=query_vector,
    limit=10
)
```

#### Exact Match Filter
```python
results = rag_client.search(
    query_vector=query_vector,
    limit=10,
    metadata_filter={
        "category": "technical",
        "author": "John Doe"
    }
)
```

#### Range Filter
```python
results = rag_client.search(
    query_vector=query_vector,
    limit=10,
    metadata_filter={
        "year": {"gte": 2020, "lte": 2023},
        "page": {"gt": 5, "lt": 50}
    }
)
```

#### Multiple Values (OR condition)
```python
results = rag_client.search(
    query_vector=query_vector,
    limit=10,
    metadata_filter={
        "source": ["pdf", "docx", "txt"]
    }
)
```

#### Combined Filters
```python
results = rag_client.search(
    query_vector=query_vector,
    limit=10,
    metadata_filter={
        "category": "technical",
        "year": {"gte": 2022},
        "source": ["pdf", "docx"]
    }
)
```

### Generate Embeddings

```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("all-MiniLM-L6-v2")
texts = ["Your document text here"]
embeddings = model.encode(texts)
```

## Metadata Filter Operations

| Operation | Syntax | Example |
|-----------|--------|---------|
| Exact Match | `{"field": "value"}` | `{"category": "technical"}` |
| Greater Than or Equal | `{"field": {"gte": value}}` | `{"year": {"gte": 2020}}` |
| Less Than or Equal | `{"field": {"lte": value}}` | `{"year": {"lte": 2023}}` |
| Greater Than | `{"field": {"gt": value}}` | `{"citations": {"gt": 100}}` |
| Less Than | `{"field": {"lt": value}}` | `{"page": {"lt": 50}}` |
| Range | `{"field": {"gte": v1, "lte": v2}}` | `{"year": {"gte": 2020, "lte": 2023}}` |
| Multiple Values | `{"field": [v1, v2, v3]}` | `{"source": ["pdf", "docx"]}` |

## API Reference

### QdrantRAGClient

#### Methods

- `create_collection(collection_name, vector_size, distance, recreate)` - Create a new collection
- `insert_documents(documents, collection_name)` - Insert documents with vectors and metadata
- `search(query_vector, collection_name, limit, score_threshold, metadata_filter)` - Search with optional filtering
- `scroll_documents(collection_name, limit, offset, metadata_filter)` - Scroll through documents
- `get_collection_info(collection_name)` - Get collection information
- `delete_collection(collection_name)` - Delete a collection
- `delete_documents(document_ids, collection_name)` - Delete specific documents

## Docker Management

### Start Qdrant
```bash
docker-compose up -d
```

### Stop Qdrant
```bash
docker-compose down
```

### View Logs
```bash
docker-compose logs -f
```

### Restart Qdrant
```bash
docker-compose restart
```

### Remove Data (Reset)
```bash
docker-compose down -v
rm -rf qdrant_storage
```

## Qdrant Dashboard

Access the Qdrant web UI at: http://localhost:6333/dashboard

## Configuration

Edit `.env` file to customize:

```env
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_GRPC_PORT=6334
COLLECTION_NAME=documents
VECTOR_SIZE=384
```

## Common Vector Sizes

| Model | Vector Size |
|-------|-------------|
| all-MiniLM-L6-v2 | 384 |
| all-mpnet-base-v2 | 768 |
| text-embedding-ada-002 (OpenAI) | 1536 |
| BERT-base | 768 |

## Troubleshooting

### Port Already in Use
```bash
# Check what's using port 6333
lsof -i :6333

# Kill the process or change port in docker-compose.yml
```

### Connection Refused
```bash
# Check if Qdrant is running
docker ps | grep qdrant

# Check logs
docker-compose logs qdrant
```

### Permission Denied (Storage)
```bash
# Fix permissions
sudo chown -R $USER:$USER ./qdrant_storage
```

## Advanced Features

### Custom Distance Metrics

```python
from qdrant_client.models import Distance

# Cosine similarity (default, good for normalized vectors)
rag_client.create_collection(distance=Distance.COSINE)

# Euclidean distance
rag_client.create_collection(distance=Distance.EUCLID)

# Dot product
rag_client.create_collection(distance=Distance.DOT)
```

### Score Threshold

```python
# Only return results above similarity threshold
results = rag_client.search(
    query_vector=query_vector,
    score_threshold=0.8,  # 0-1 for cosine
    limit=10
)
```

## Resources

- [Qdrant Documentation](https://qdrant.tech/documentation/)
- [Qdrant Python Client](https://github.com/qdrant/qdrant-client)
- [Sentence Transformers](https://www.sbert.net/)

## License

MIT
