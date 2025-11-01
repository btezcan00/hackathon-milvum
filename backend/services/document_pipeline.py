import os
import uuid
import logging
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from pypdf import PdfReader
import nltk

from services.llm_service import EmbeddingService
from services.pinecone_service import PineconeRAGClient
from repository.google_storeage import GCSHelper

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
    1. Upload original file to GCS
    2. Extract text from PDF/DOCX/TXT
    3. Chunk text with sentence awareness and page tracking
    4. Generate embeddings
    5. Upload to Pinecone with GCS metadata
    """
    
    def __init__(self, embedding_service: EmbeddingService, pinecone_client: PineconeRAGClient):
        self.embedding_service = embedding_service
        self.pinecone_client = pinecone_client
        self.gcs_helper = GCSHelper()
        
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
        upload_to_gcs: bool = True
    ) -> Dict[str, Any]:
        """
        Process a single file: upload to GCS, extract, chunk, embed, upload to Pinecone.
        
        Returns:
            Dict with processing results including GCS URL
        """
        try:
            logger.info(f"Processing file: {filename}")
            
            # Step 1: Upload original file to GCS
            gcs_metadata = None
            if upload_to_gcs:
                try:
                    gcs_metadata = self.gcs_helper.upload_file(
                        local_filepath=filepath,
                        destination_blob_name=None,  # Auto-generate with timestamp
                        make_public=False  # Use signed URLs instead
                    )
                    logger.info(f"✓ Uploaded to GCS: {gcs_metadata['blob_name']}")
                except Exception as e:
                    logger.error(f"Failed to upload to GCS: {e}")
                    # Continue processing even if GCS upload fails
            
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
                        'error': 'No text extracted from PDF',
                        'gcs_metadata': gcs_metadata
                    }
                
                chunks = self.create_chunks_with_pages(
                    sentences_with_pages,
                    document_name,
                    split_length,
                    split_overlap
                )
            else:
                text = self.extract_text_from_file(filepath)
                
                if not text:
                    return {
                        'success': False,
                        'filename': filename,
                        'error': 'No text extracted',
                        'gcs_metadata': gcs_metadata
                    }
                
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
                    'error': 'No chunks created',
                    'gcs_metadata': gcs_metadata
                }
            
            logger.info(f"Created {len(chunks)} chunks for {filename}")
            
            # Generate embeddings
            texts = [chunk['text'] for chunk in chunks]
            embeddings = self.embedding_service.get_embeddings(texts)
            
            # Prepare documents for Pinecone with GCS metadata
            documents = []
            vectors = []
            
            for chunk, embedding in zip(chunks, embeddings):
                doc = {
                    'text': chunk['text'],
                    'document_name': chunk['metadata']['document_name'],
                    'page_numbers': [str(p) for p in chunk['metadata']['page_numbers']]
                }
                
                # Add GCS metadata if available
                if gcs_metadata:
                    doc['gcs_url'] = gcs_metadata['url']
                    doc['gcs_blob_name'] = gcs_metadata['blob_name']
                    doc['gcs_bucket'] = gcs_metadata['bucket']
                
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
                'vectors_uploaded': len(vectors),
                'gcs_metadata': gcs_metadata
            }
            
        except Exception as e:
            logger.error(f"Error processing {filename}: {e}")
            return {
                'success': False,
                'filename': filename,
                'error': str(e),
                'gcs_metadata': gcs_metadata
            }
    
    def download_and_process_from_gcs(
        self,
        blob_name: str,
        split_length: int = 10,
        split_overlap: int = 2,
        batch_size: int = 100
    ) -> Dict[str, Any]:
        """
        Download a file from GCS and process it.
        
        Args:
            blob_name: Path to file in GCS bucket
            
        Returns:
            Processing results
        """
        temp_dir = '/tmp/gcs_downloads'
        os.makedirs(temp_dir, exist_ok=True)
        
        filename = os.path.basename(blob_name)
        local_path = os.path.join(temp_dir, filename)
        
        try:
            # Download from GCS
            self.gcs_helper.download_file(blob_name, local_path)
            
            # Process the file (don't re-upload to GCS since it's already there)
            result = self.process_single_file(
                filepath=local_path,
                filename=filename,
                split_length=split_length,
                split_overlap=split_overlap,
                batch_size=batch_size,
                upload_to_gcs=False  # Already in GCS
            )
            
            # Add GCS metadata manually
            if result['success']:
                result['gcs_metadata'] = {
                    'blob_name': blob_name,
                    'url': self.gcs_helper.get_signed_url(blob_name)
                }
            
            return result
            
        finally:
            # Clean up downloaded file
            if os.path.exists(local_path):
                os.remove(local_path)
    
    def process_files_parallel(
        self,
        filepaths: List[str],
        filenames: List[str],
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
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all files for processing
            future_to_file = {
                executor.submit(
                    self.process_single_file,
                    filepath,
                    filename,
                    split_length,
                    split_overlap,
                    batch_size
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