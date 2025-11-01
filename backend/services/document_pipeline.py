import os
import uuid
import logging
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from pypdf import PdfReader
import nltk

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
    
    def create_chunks_with_pages(
        self,
        sentences_with_pages: List[Dict],
        document_name: str,
        split_length: int = 10,
        split_overlap: int = 2
    ) -> List[Dict]:
        """
        Create chunks from sentences with page tracking.
        
        Args:
            sentences_with_pages: List of sentences with page numbers
            document_name: Name of the document
            split_length: Maximum sentences per chunk
            split_overlap: Sentence overlap between chunks
            
        Returns:
            List of chunk dicts with text and metadata
        """
        chunks = []
        i = 0
        
        while i < len(sentences_with_pages):
            chunk_sentences = sentences_with_pages[i:i + split_length]
            
            if not chunk_sentences:
                break
            
            # Extract text and page numbers
            chunk_text = ' '.join([s['text'] for s in chunk_sentences])
            page_numbers = sorted(list(set([s['page_number'] for s in chunk_sentences])))
            
            # Create chunk
            chunk = {
                'text': chunk_text,
                'metadata': {
                    'document_name': document_name,
                    'page_numbers': page_numbers
                }
            }
            chunks.append(chunk)
            
            # Move to next chunk with overlap
            i += split_length - split_overlap
        
        return chunks
    
    def process_single_file(
        self,
        filepath: str,
        filename: str,
        split_length: int = 10,
        split_overlap: int = 2,
        batch_size: int = 100,
        drive_url: str = None
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
                
                # Create chunks with page tracking
                chunks = self.create_chunks_with_pages(
                    sentences_with_pages,
                    document_name,
                    split_length,
                    split_overlap
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
                
                chunks = self.create_chunks_with_pages(
                    sentences_with_pages,
                    document_name,
                    split_length,
                    split_overlap
                )
            
            if not chunks:
                return {
                    'success': False,
                    'filename': filename,
                    'error': 'No chunks created'
                }
            
            logger.info(f"Created {len(chunks)} chunks for {filename}")
            
            # Generate embeddings for all chunks
            logger.info(f"Generating embeddings for {len(chunks)} chunks...")
            texts = [chunk['text'] for chunk in chunks]
            embeddings = self.embedding_service.get_embeddings(texts)
            
            # Prepare documents for Pinecone
            documents = []
            vectors = []
            
            for chunk, embedding in zip(chunks, embeddings):
                # Flatten metadata
                doc = {
                    'text': chunk['text'],
                    'document_name': chunk['metadata']['document_name'],
                    'page_numbers': [str(p) for p in chunk['metadata']['page_numbers']]  # Convert to strings
                }
                # Add GCS/Google Drive URL if provided
                if drive_url:
                    doc['gcs_url'] = drive_url  # Store as gcs_url for consistency
                    logger.info(f"[DocumentPipeline] Storing GCS URL for {document_name}: {drive_url}")
                else:
                    logger.info(f"[DocumentPipeline] No GCS URL provided for {document_name}")
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
        drive_urls: List[str] = None,
        max_workers: int = 4,
        split_length: int = 10,
        split_overlap: int = 2,
        batch_size: int = 100
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
        
        # Match drive URLs to files by index
        if drive_urls is None:
            drive_urls = [None] * len(filepaths)
        else:
            # Ensure drive_urls list matches filepaths length
            while len(drive_urls) < len(filepaths):
                drive_urls.append(None)
            drive_urls = drive_urls[:len(filepaths)]  # Trim if too many
        
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
                    drive_url  # Pass Google Drive URL if available
                ): filename
                for filepath, filename, drive_url in zip(filepaths, filenames, drive_urls)
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