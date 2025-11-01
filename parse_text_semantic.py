#!/usr/bin/env python3
"""
Text Parser with LangChain Semantic Chunking

Chunks documents with:
- Semantic chunking (groups semantically similar content)
- Metadata: document_name, page_numbers
"""

import os
from pathlib import Path
from typing import List, Dict, Tuple
import json
from pypdf import PdfReader
from dotenv import load_dotenv

from langchain_experimental.text_splitter import SemanticChunker
from langchain_openai import OpenAIEmbeddings

# Load environment variables from backend/.env
load_dotenv("backend/.env")


def extract_text_with_pages(pdf_path: str) -> Tuple[str, Dict[int, Tuple[int, int]]]:
    """
    Extract text from PDF with page tracking.

    Args:
        pdf_path: Path to PDF file

    Returns:
        Tuple of (full_text, page_map) where page_map maps char position ranges to page numbers
    """
    reader = PdfReader(pdf_path)
    full_text = ""
    page_map = {}  # Maps character ranges to page numbers
    current_pos = 0

    for page_num, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text()
            # Remove anonymization markers
            text = text.replace('(geanonimiseerd)', '')
            text = text.replace(' (geanonimiseerd)', '')

            if text.strip():
                start_pos = current_pos
                full_text += text + "\n\n"
                end_pos = len(full_text)
                page_map[page_num] = (start_pos, end_pos)
                current_pos = end_pos

        except Exception as e:
            print(f"    Warning: Error extracting from page {page_num}: {e}")
            continue

    return full_text, page_map


def normalize_text(text: str) -> str:
    """Normalize text for comparison by collapsing whitespace."""
    import re
    return re.sub(r'\s+', ' ', text).strip()


def get_pages_for_chunk(chunk_text: str, full_text: str, page_map: Dict[int, Tuple[int, int]]) -> List[int]:
    """
    Determine which pages a chunk spans based on its position in the full text.

    Args:
        chunk_text: The text of the chunk
        full_text: The full document text
        page_map: Mapping of page numbers to character positions

    Returns:
        List of page numbers this chunk appears on
    """
    # Try exact match first
    chunk_start = full_text.find(chunk_text)

    # If exact match fails, try with normalized whitespace
    if chunk_start == -1:
        normalized_chunk = normalize_text(chunk_text)
        normalized_full = normalize_text(full_text)

        # Find the first 50 characters of the chunk as a signature
        chunk_signature = normalized_chunk[:min(100, len(normalized_chunk))]
        sig_pos = normalized_full.find(chunk_signature)

        if sig_pos == -1:
            # Fallback: return all pages if we can't locate the chunk
            print(f"    Warning: Could not locate chunk in full text, using all pages as fallback")
            return sorted(list(page_map.keys()))

        # Estimate position based on normalized text ratio
        ratio = sig_pos / len(normalized_full) if len(normalized_full) > 0 else 0
        chunk_start = int(ratio * len(full_text))

    chunk_end = chunk_start + len(chunk_text)

    # Determine which pages this chunk spans
    pages = []
    for page_num, (page_start, page_end) in page_map.items():
        # Check if chunk overlaps with this page
        if not (chunk_end <= page_start or chunk_start >= page_end):
            pages.append(page_num)

    return sorted(pages) if pages else sorted(list(page_map.keys()))


def create_semantic_chunks(
    full_text: str,
    page_map: Dict[int, Tuple[int, int]],
    document_name: str,
    embeddings: OpenAIEmbeddings,
    breakpoint_threshold_type: str = "percentile"
) -> List[Dict]:
    """
    Create semantic chunks from full text using LangChain's SemanticChunker.

    Args:
        full_text: Full document text
        page_map: Mapping of page numbers to character positions
        document_name: Name of the document
        embeddings: OpenAI embeddings instance
        breakpoint_threshold_type: Type of breakpoint threshold ("percentile", "standard_deviation", "interquartile")

    Returns:
        List of chunk dictionaries with text and metadata
    """
    # Initialize semantic chunker
    text_splitter = SemanticChunker(
        embeddings=embeddings,
        breakpoint_threshold_type=breakpoint_threshold_type
    )

    # Split text semantically
    docs = text_splitter.create_documents([full_text])

    # Convert to our chunk format with page tracking
    chunks = []
    for doc in docs:
        chunk_text = doc.page_content

        # Get pages for this chunk
        pages = get_pages_for_chunk(chunk_text, full_text, page_map)

        chunk = {
            'text': chunk_text,
            'metadata': {
                'document_name': document_name,
                'page_numbers': pages
            }
        }
        chunks.append(chunk)

    return chunks


def parse_documents(
    input_dir: str = "unique files",
    breakpoint_threshold_type: str = "percentile",
    max_files: int = None,
    output_format: str = "json"
) -> List[Dict]:
    """
    Parse all PDF documents and create semantic chunks.

    Args:
        input_dir: Directory containing PDF files
        breakpoint_threshold_type: Type of breakpoint threshold for semantic chunking
        max_files: Limit number of files (None for all)
        output_format: Output format ('json' or 'text')

    Returns:
        List of chunks with metadata
    """
    # Get PDF files
    pdf_dir = Path(input_dir)
    pdf_files = list(pdf_dir.glob("*.pdf"))

    if max_files:
        pdf_files = pdf_files[:max_files]

    print(f"Found {len(pdf_files)} PDF files to process")
    print()

    # Initialize embeddings (only once for all files)
    print("Initializing OpenAI embeddings...")
    embeddings = OpenAIEmbeddings()
    print("✓ Embeddings initialized")
    print()

    all_chunks = []

    # Process each file
    for idx, pdf_file in enumerate(pdf_files, 1):
        print(f"Processing [{idx}/{len(pdf_files)}]: {pdf_file.name}")

        try:
            # Extract document name and remove anonymization markers
            document_name = pdf_file.stem
            document_name = document_name.replace(' (geanonimiseerd)', '').replace('(geanonimiseerd)', '')

            # Extract text with page tracking
            full_text, page_map = extract_text_with_pages(str(pdf_file))

            if not full_text.strip():
                print(f"  ✗ No text extracted")
                continue

            # Create semantic chunks
            chunks = create_semantic_chunks(
                full_text,
                page_map,
                document_name,
                embeddings,
                breakpoint_threshold_type
            )

            all_chunks.extend(chunks)
            print(f"  → Created {len(chunks)} semantic chunks")

        except Exception as e:
            print(f"  ✗ Error: {e}")
            import traceback
            traceback.print_exc()
            continue

    # Filter out chunks with meaningless text
    filtered_chunks = [
        chunk for chunk in all_chunks
        if chunk['text'].strip() != ". . . . . . . . . . . . . . . . . . . . . . . . . . . . . ."
    ]

    removed_count = len(all_chunks) - len(filtered_chunks)
    if removed_count > 0:
        print(f"\n✓ Filtered out {removed_count} chunks with meaningless text")

    print(f"\n✓ Processing complete!")
    print(f"Total chunks: {len(filtered_chunks)}")
    print(f"Documents processed: {len(pdf_files)}")

    return filtered_chunks


def save_chunks(chunks: List[Dict], output_file: str = "parsed_chunks.json"):
    """
    Save chunks to file.

    Args:
        chunks: List of chunk dictionaries
        output_file: Output filename
    """
    # Determine format from extension
    if output_file.endswith('.json'):
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(chunks, f, ensure_ascii=False, indent=2)
        print(f"✓ Saved {len(chunks)} chunks to {output_file}")

    elif output_file.endswith('.txt'):
        with open(output_file, 'w', encoding='utf-8') as f:
            for idx, chunk in enumerate(chunks, 1):
                f.write(f"{'='*80}\n")
                f.write(f"CHUNK {idx}\n")
                f.write(f"Document: {chunk['metadata']['document_name']}\n")
                f.write(f"Pages: {chunk['metadata']['page_numbers']}\n")
                f.write(f"{'='*80}\n")
                f.write(chunk['text'])
                f.write(f"\n\n")
        print(f"✓ Saved {len(chunks)} chunks to {output_file}")

    # Print file size
    file_size = os.path.getsize(output_file)
    file_size_kb = file_size / 1024
    print(f"  File size: {file_size_kb:.2f} KB")


def main():
    """Main function."""

    # Configuration
    INPUT_DIR = "unique files"
    BREAKPOINT_TYPE = "percentile"  # Options: "percentile", "standard_deviation", "interquartile"
    MAX_FILES = None       # Process all files (set to number for testing)
    OUTPUT_JSON = "parsed_chunks.json"
    OUTPUT_TXT = "parsed_chunks.txt"

    print("="*80)
    print("Text Parser with LangChain Semantic Chunking")
    print("="*80)
    print(f"Input directory: {INPUT_DIR}")
    print(f"Chunking method: Semantic (using embeddings)")
    print(f"Breakpoint threshold: {BREAKPOINT_TYPE}")
    print(f"Metadata: document_name, page_numbers")
    print("="*80)
    print()

    # Parse documents
    chunks = parse_documents(
        input_dir=INPUT_DIR,
        breakpoint_threshold_type=BREAKPOINT_TYPE,
        max_files=MAX_FILES
    )

    if not chunks:
        print("No chunks created!")
        return

    # Save outputs
    print()
    save_chunks(chunks, OUTPUT_JSON)
    save_chunks(chunks, OUTPUT_TXT)

    # Show example
    print()
    print("="*80)
    print("Example chunk:")
    print("="*80)
    example = chunks[0]
    print(f"Document name: {example['metadata']['document_name']}")
    print(f"Page numbers: {example['metadata']['page_numbers']}")
    print(f"Text preview: {example['text'][:200]}...")
    print("="*80)

    return chunks


if __name__ == "__main__":
    main()
