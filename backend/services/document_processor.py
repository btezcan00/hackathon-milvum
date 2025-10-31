import os
from datetime import datetime
from typing import List
import logging

logger = logging.getLogger(__name__)

class DocumentProcessor:
    """Processes documents (PDF, DOCX, TXT, MD) and chunks text"""
    
    def __init__(self, chunk_size: int = 500, overlap: int = 50):
        """
        Initialize document processor
        
        Args:
            chunk_size: Maximum characters per chunk
            overlap: Overlap characters between chunks
        """
        self.chunk_size = chunk_size
        self.overlap = overlap
    
    def extract_text(self, filepath: str) -> str:
        """
        Extract text from document file
        
        Args:
            filepath: Path to the document file
            
        Returns:
            Extracted text content
        """
        _, ext = os.path.splitext(filepath.lower())
        
        try:
            if ext == '.pdf':
                return self._extract_pdf(filepath)
            elif ext == '.docx':
                return self._extract_docx(filepath)
            elif ext in ['.txt', '.md']:
                return self._extract_text_file(filepath)
            else:
                raise ValueError(f"Unsupported file type: {ext}")
        except Exception as e:
            logger.error(f"Error extracting text from {filepath}: {str(e)}")
            raise
    
    def _extract_pdf(self, filepath: str) -> str:
        """Extract text from PDF file"""
        try:
            import PyPDF2
            text = ""
            with open(filepath, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
            return text.strip()
        except ImportError:
            raise ImportError("PyPDF2 is required for PDF processing")
    
    def _extract_docx(self, filepath: str) -> str:
        """Extract text from DOCX file"""
        try:
            from docx import Document
            doc = Document(filepath)
            text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
            return text.strip()
        except ImportError:
            raise ImportError("python-docx is required for DOCX processing")
    
    def _extract_text_file(self, filepath: str) -> str:
        """Extract text from plain text file"""
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as file:
            return file.read().strip()
    
    def chunk_text(self, text: str) -> List[str]:
        """
        Split text into overlapping chunks
        
        Args:
            text: Input text to chunk
            
        Returns:
            List of text chunks
        """
        if not text:
            return []
        
        chunks = []
        start = 0
        text_length = len(text)
        
        while start < text_length:
            end = start + self.chunk_size
            
            # If we're not at the end, try to break at a word boundary
            if end < text_length:
                # Look for space or newline near the chunk boundary
                boundary = text.rfind(' ', start, end)
                if boundary == -1:
                    boundary = text.rfind('\n', start, end)
                if boundary != -1 and boundary > start:
                    end = boundary + 1
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            # Move start position with overlap
            start = end - self.overlap
            if start <= 0:
                start = end
        
        return chunks
    
    def get_current_timestamp(self) -> str:
        """
        Get current timestamp as ISO format string
        
        Returns:
            ISO formatted timestamp string
        """
        return datetime.now().isoformat()

