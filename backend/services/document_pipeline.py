import os
import uuid
import logging
from typing import List, Dict, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from pypdf import PdfReader
import nltk
import numpy as np

from services.llm_service import EmbeddingService
from services.pinecone_service import PineconeRAGClient

logger = logging.getLogger(__name__)

# Download NLTK data if needed
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')
    nltk.download('punkt_tab')


class DocumentPipeline:
    """
    Complete pipeline for document processing:
    1. Extract text from PDF/DOCX/TXT
    2. Chunk text with sentence awareness and page tracking
    3. Generate embeddings
    4. Upload to Pinecone
    """
    
    def __init__(self, embedding_service: EmbeddingService, pinecone_client: PineconeRAGClient):
        self.embedding_service = embedding_service
        self.pinecone_client = pinecone_client
        
    def extract_text_with_pages(self, pdf_path: str) -> List[Dict]:
        """
        Extract text from PDF with page number tracking.
        
        Returns:
            List of dicts with 'text', 'page_number' for each sentence
        """
        reader = PdfReader(pdf_path)
        sentences_with_pages = []
        
        for page_num, page in enumerate(reader.pages, start=1):
            try:
                text = page.extract_text()
                # Remove anonymization markers
                text = text.replace('(geanonimiseerd)', '').replace(' (geanonimiseerd)', '')
                
                if text.strip():
                    # Split into sentences using NLTK
                    sentences = nltk.sent_tokenize(text)
                    for sentence in sentences:
                        if sentence.strip():
                            sentences_with_pages.append({
                                'text': sentence.strip(),
                                'page_number': page_num
                            })
            except Exception as e:
                logger.warning(f"Error extracting from page {page_num}: {e}")
                continue
        
        return sentences_with_pages
    
    def extract_text_from_file(self, filepath: str) -> str:
        """Extract text from various file formats"""
        _, ext = os.path.splitext(filepath.lower())
        
        try:
            if ext == '.pdf':
                # For PDF, we'll use the sentence-based extraction
                sentences = self.extract_text_with_pages(filepath)
                return ' '.join([s['text'] for s in sentences])
            elif ext == '.docx':
                from docx import Document
                doc = Document(filepath)
                return "\n".join([paragraph.text for paragraph in doc.paragraphs])
            elif ext in ['.txt', '.md']:
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as file:
                    return file.read().strip()
            else:
                raise ValueError(f"Unsupported file type: {ext}")
        except Exception as e:
            logger.error(f"Error extracting text from {filepath}: {e}")
            raise
    
    def cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        vec1 = np.array(vec1)
        vec2 = np.array(vec2)
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot_product / (norm1 * norm2)

    def create_semantic_chunks_with_pages(
        self,
        sentences_with_pages: List[Dict],
        document_name: str,
        filename: Optional[str] = None,
        file_extension: Optional[str] = None,
        similarity_threshold: float = 0.76,
        min_chunk_size: int = 3,
        max_chunk_size: int = 50,
        buffer_size: int = 5,
        precomputed_embeddings: Optional[List[List[float]]] = None
    ) -> Tuple[List[Dict], List[List[float]]]:
        """
        Create chunks using semantic similarity (following Pinecone's approach).
        Groups sentences with similar meaning together, respecting natural topic boundaries.
        
        Args:
            sentences_with_pages: List of sentences with page numbers
            document_name: Name of the document
            similarity_threshold: Minimum cosine similarity to keep sentences together (0.76 is a good default)
            min_chunk_size: Minimum sentences per chunk
            max_chunk_size: Maximum sentences per chunk
            buffer_size: Number of sentences to compare against for splitting
            precomputed_embeddings: Optional pre-computed embeddings (avoids regenerating)
            
        Returns:
            Tuple of (chunks, chunk_embeddings) - embeddings are for the chunks, not sentences
        """
        if not sentences_with_pages:
            return [], []
        
        # Generate embeddings for all sentences (or use precomputed)
        if precomputed_embeddings is None:
            logger.info(f"Generating embeddings for {len(sentences_with_pages)} sentences for semantic chunking...")
            sentence_texts = [s['text'] for s in sentences_with_pages]
            
            # Batch embeddings to avoid overwhelming the API
            batch_size = 100
            all_embeddings = []
            for i in range(0, len(sentence_texts), batch_size):
                batch = sentence_texts[i:i + batch_size]
                batch_embeddings = self.embedding_service.get_embeddings(batch)
                all_embeddings.extend(batch_embeddings)
        else:
            all_embeddings = precomputed_embeddings
        
        chunks = []
        current_chunk_start = 0
        
        for i in range(1, len(sentences_with_pages)):
            # Calculate similarity between current sentence and sentences in the buffer
            current_embedding = all_embeddings[i]
            
            # Compare with the last few sentences in the current chunk (buffer)
            buffer_start = max(current_chunk_start, i - buffer_size)
            buffer_similarities = []
            
            for j in range(buffer_start, i):
                similarity = self.cosine_similarity(all_embeddings[j], current_embedding)
                buffer_similarities.append(similarity)
            
            # Average similarity with buffer
            avg_similarity = np.mean(buffer_similarities) if buffer_similarities else 1.0
            chunk_size = i - current_chunk_start
            
            # Decide whether to split based on similarity and chunk size
            should_split = False
            
            if chunk_size >= max_chunk_size:
                # Force split if chunk is too large
                should_split = True
            elif chunk_size >= min_chunk_size and avg_similarity < similarity_threshold:
                # Split if similarity drops below threshold
                should_split = True
            
            if should_split:
                # Create chunk from current_chunk_start to i-1
                chunk_sentences = sentences_with_pages[current_chunk_start:i]
                chunk_text = ' '.join([s['text'] for s in chunk_sentences])
                page_numbers = sorted(list(set([s['page_number'] for s in chunk_sentences])))
                chunk_index = len(chunks)
                
                chunk = {
                    'text': chunk_text,
                    'metadata': {
                        'document_name': document_name,
                        'page_numbers': page_numbers,
                        'page_start': min(page_numbers) if page_numbers else None,
                        'page_end': max(page_numbers) if page_numbers else None,
                        'chunk_index': chunk_index,
                        'num_sentences': len(chunk_sentences),
                        'filename': filename or document_name,
                        'file_extension': file_extension or ''
                    }
                }
                chunks.append(chunk)
                current_chunk_start = i
        
        # Add remaining sentences as final chunk
        if current_chunk_start < len(sentences_with_pages):
            chunk_sentences = sentences_with_pages[current_chunk_start:]
            chunk_text = ' '.join([s['text'] for s in chunk_sentences])
            page_numbers = sorted(list(set([s['page_number'] for s in chunk_sentences])))
            chunk_index = len(chunks)
            
            chunk = {
                'text': chunk_text,
                'metadata': {
                    'document_name': document_name,
                    'page_numbers': page_numbers,
                    'page_start': min(page_numbers) if page_numbers else None,
                    'page_end': max(page_numbers) if page_numbers else None,
                    'chunk_index': chunk_index,
                    'num_sentences': len(chunk_sentences),
                    'filename': filename or document_name,
                    'file_extension': file_extension or ''
                }
            }
            chunks.append(chunk)
        
        logger.info(f"Created {len(chunks)} semantic chunks (avg size: {len(sentences_with_pages) / len(chunks) if chunks else 0:.1f} sentences)")
        
        # Generate embeddings for the chunks (not sentences)
        chunk_texts = [chunk['text'] for chunk in chunks]
        logger.info(f"Generating embeddings for {len(chunk_texts)} chunks...")
        chunk_embeddings = []
        batch_size = 100
        for i in range(0, len(chunk_texts), batch_size):
            batch = chunk_texts[i:i + batch_size]
            batch_embeddings = self.embedding_service.get_embeddings(batch)
            chunk_embeddings.extend(batch_embeddings)
        
        return chunks, chunk_embeddings

    def create_chunks_with_pages(
        self,
        sentences_with_pages: List[Dict],
        document_name: str,
        filename: Optional[str] = None,
        file_extension: Optional[str] = None,
        split_length: int = 10,
        split_overlap: int = 2,
        use_semantic: bool = True,
        similarity_threshold: float = 0.76
    ) -> Tuple[List[Dict], Optional[List[List[float]]]]:
        """
        Create chunks from sentences with page tracking.
        Can use either fixed-size or semantic chunking.
        
        Args:
            sentences_with_pages: List of sentences with page numbers
            document_name: Name of the document
            split_length: Maximum sentences per chunk (for fixed-size chunking)
            split_overlap: Sentence overlap between chunks (for fixed-size chunking)
            use_semantic: If True, use semantic chunking; otherwise use fixed-size
            similarity_threshold: Similarity threshold for semantic chunking
            
        Returns:
            Tuple of (chunks, embeddings) - embeddings are None for fixed-size, precomputed for semantic
        """
        if use_semantic:
            chunks, chunk_embeddings = self.create_semantic_chunks_with_pages(
                sentences_with_pages,
                document_name,
                filename=filename,
                file_extension=file_extension,
                similarity_threshold=similarity_threshold
            )
            return chunks, chunk_embeddings
        else:
            # Original fixed-size chunking
            chunks = []
            i = 0
            chunk_index = 0
            
            while i < len(sentences_with_pages):
                chunk_sentences = sentences_with_pages[i:i + split_length]
                
                if not chunk_sentences:
                    break
                
                # Extract text and page numbers
                chunk_text = ' '.join([s['text'] for s in chunk_sentences])
                page_numbers = sorted(list(set([s['page_number'] for s in chunk_sentences])))
                
                # Create chunk with comprehensive metadata
                chunk = {
                    'text': chunk_text,
                    'metadata': {
                        'document_name': document_name,
                        'page_numbers': page_numbers,
                        'page_start': min(page_numbers) if page_numbers else None,
                        'page_end': max(page_numbers) if page_numbers else None,
                        'chunk_index': chunk_index,
                        'num_sentences': len(chunk_sentences),
                        'filename': filename or document_name,
                        'file_extension': file_extension or ''
                    }
                }
                chunks.append(chunk)
                chunk_index += 1
                
                # Move to next chunk with overlap
                i += split_length - split_overlap
            
            return chunks, None  # No precomputed embeddings for fixed-size chunking
    
    def process_single_file(
        self,
        filepath: str,
        filename: str,
        split_length: int = 10,
        split_overlap: int = 2,
        batch_size: int = 100,
        use_semantic_chunking: bool = True,
        similarity_threshold: float = 0.76
    ) -> Dict[str, Any]:
        """
        Process a single file: extract, chunk, embed, upload to Pinecone.
        
        Returns:
            Dict with processing results
        """
        try:
            logger.info(f"Processing file: {filename}")
            
            # Remove anonymization markers from filename
            document_name = os.path.splitext(filename)[0]
            document_name = document_name.replace(' (geanonimiseerd)', '').replace('(geanonimiseerd)', '')
            
            # Extract text with page tracking (for PDFs)
            _, ext = os.path.splitext(filepath.lower())
            
            if ext == '.pdf':
                sentences_with_pages = self.extract_text_with_pages(filepath)
                
                if not sentences_with_pages:
                    return {
                        'success': False,
                        'filename': filename,
                        'error': 'No text extracted from PDF'
                    }
                
                # Create chunks with page tracking (semantic or fixed-size)
                chunks, precomputed_chunk_embeddings = self.create_chunks_with_pages(
                    sentences_with_pages,
                    document_name,
                    filename=filename,
                    file_extension=ext.lstrip('.') if ext else None,
                    split_length=split_length,
                    split_overlap=split_overlap,
                    use_semantic=use_semantic_chunking,
                    similarity_threshold=similarity_threshold
                )
            else:
                # For non-PDF files, use simple text extraction
                text = self.extract_text_from_file(filepath)
                
                if not text:
                    return {
                        'success': False,
                        'filename': filename,
                        'error': 'No text extracted'
                    }
                
                # Simple sentence-based chunking
                sentences = nltk.sent_tokenize(text)
                sentences_with_pages = [{'text': s, 'page_number': 1} for s in sentences]
                
                chunks, precomputed_chunk_embeddings = self.create_chunks_with_pages(
                    sentences_with_pages,
                    document_name,
                    filename=filename,
                    file_extension=ext.lstrip('.') if ext else None,
                    split_length=split_length,
                    split_overlap=split_overlap,
                    use_semantic=use_semantic_chunking,
                    similarity_threshold=similarity_threshold
                )
            
            if not chunks:
                return {
                    'success': False,
                    'filename': filename,
                    'error': 'No chunks created'
                }
            
            logger.info(f"Created {len(chunks)} chunks for {filename}")
            
            # Generate embeddings for all chunks (or use precomputed from semantic chunking)
            if precomputed_chunk_embeddings is not None:
                logger.info(f"Using precomputed embeddings from semantic chunking")
                embeddings = precomputed_chunk_embeddings
            else:
                logger.info(f"Generating embeddings for {len(chunks)} chunks...")
                texts = [chunk['text'] for chunk in chunks]
                embeddings = self.embedding_service.get_embeddings(texts)
            
            # Prepare documents for Pinecone
            documents = []
            vectors = []
            
            for chunk, embedding in zip(chunks, embeddings):
                # Pass through all metadata to Pinecone
                metadata = chunk['metadata'].copy()
                
                # Convert page_numbers to list of strings (Pinecone requirement)
                if 'page_numbers' in metadata and metadata['page_numbers']:
                    metadata['page_numbers'] = [str(p) for p in metadata['page_numbers']]
                else:
                    metadata['page_numbers'] = []
                
                # Ensure all values are Pinecone-compatible
                # Pinecone doesn't accept None values, so we'll convert None to appropriate defaults
                clean_metadata = {}
                for key, value in metadata.items():
                    if value is None:
                        # Convert None to appropriate defaults based on field type
                        if key in ['page_start', 'page_end']:
                            clean_metadata[key] = 0  # Use 0 as default for page numbers
                        elif key == 'file_extension':
                            clean_metadata[key] = ''  # Empty string for file extension
                        else:
                            continue  # Skip other None values
                    elif isinstance(value, list):
                        # Keep lists (including empty ones) - Pinecone supports them
                        clean_metadata[key] = value
                    elif isinstance(value, (int, float, str, bool)):
                        # All primitive types are fine
                        clean_metadata[key] = value
                    else:
                        # Convert other types to string
                        clean_metadata[key] = str(value)
                
                doc = {
                    'text': chunk['text'],
                    **clean_metadata  # Include all metadata fields
                }
                documents.append(doc)
                vectors.append(embedding)
            
            # Upload to Pinecone in batches
            logger.info(f"Uploading {len(documents)} vectors to Pinecone...")
            for i in range(0, len(documents), batch_size):
                batch_docs = documents[i:i + batch_size]
                batch_vectors = vectors[i:i + batch_size]
                self.pinecone_client.upsert_documents(batch_docs, batch_vectors)
            
            logger.info(f"✓ Successfully processed {filename}")
            
            return {
                'success': True,
                'filename': filename,
                'document_name': document_name,
                'chunks_count': len(chunks),
                'vectors_uploaded': len(vectors)
            }
            
        except Exception as e:
            logger.error(f"Error processing {filename}: {e}")
            return {
                'success': False,
                'filename': filename,
                'error': str(e)
            }
    
    def process_files_parallel(
        self,
        filepaths: List[str],
        filenames: List[str],
        max_workers: int = 4,
        split_length: int = 10,
        split_overlap: int = 2,
        batch_size: int = 100,
        use_semantic_chunking: bool = True,
        similarity_threshold: float = 0.76
    ) -> List[Dict[str, Any]]:
        """
        Process multiple files in parallel.
        
        Args:
            filepaths: List of file paths
            filenames: List of filenames
            max_workers: Maximum number of parallel workers
            split_length: Max sentences per chunk
            split_overlap: Sentence overlap
            batch_size: Batch size for Pinecone upload
            
        Returns:
            List of processing results for each file
        """
        results = []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all files for processing
            future_to_file = {
                executor.submit(
                    self.process_single_file,
                    filepath,
                    filename,
                    split_length,
                    split_overlap,
                    batch_size,
                    use_semantic_chunking,
                    similarity_threshold
                ): filename
                for filepath, filename in zip(filepaths, filenames)
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_file):
                filename = future_to_file[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    logger.error(f"Error processing {filename}: {e}")
                    results.append({
                        'success': False,
                        'filename': filename,
                        'error': str(e)
                    })
        
        return results