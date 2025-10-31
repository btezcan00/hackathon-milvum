#!/usr/bin/env python3
"""
Text Parser with Haystack - Clean Version

Chunks documents with:
- Max 10 sentences per chunk
- Metadata: document_name, page_numbers
"""

import os
from pathlib import Path
from typing import List, Dict
import json
import nltk
from pypdf import PdfReader

from haystack import Pipeline, Document, component
from haystack.components.converters import PyPDFToDocument
from haystack.components.preprocessors import DocumentCleaner, DocumentSplitter
from haystack.document_stores.in_memory import InMemoryDocumentStore

# Download NLTK data if needed
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    import ssl
    ssl._create_default_https_context = ssl._create_unverified_context
    nltk.download('punkt')
    nltk.download('punkt_tab')


def extract_text_with_pages(pdf_path: str) -> List[Dict]:
    """
    Extract text from PDF with page and line number tracking.

    Args:
        pdf_path: Path to PDF file

    Returns:
        List of dicts with 'text', 'page_number', and 'line_in_page' for each sentence
    """
    reader = PdfReader(pdf_path)
    sentences_with_pages = []

    for page_num, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text()
            # Remove anonymization markers
            text = text.replace('(geanonimiseerd)', '')
            text = text.replace(' (geanonimiseerd)', '')
            if text.strip():
                # Split into sentences
                sentences = nltk.sent_tokenize(text)
                # Track line number within this page
                line_in_page = 1
                for sentence in sentences:
                    if sentence.strip():
                        sentences_with_pages.append({
                            'text': sentence.strip(),
                            'page_number': page_num,
                            'line_in_page': line_in_page
                        })
                        line_in_page += 1
        except Exception as e:
            print(f"    Warning: Error extracting from page {page_num}: {e}")
            continue

    return sentences_with_pages


def create_chunks_with_pages(sentences_with_pages: List[Dict],
                             document_name: str,
                             split_length: int = 10,
                             split_overlap: int = 2) -> List[Dict]:
    """
    Create chunks from sentences with page tracking.

    Args:
        sentences_with_pages: List of sentences with page and line numbers
        document_name: Name of the document
        split_length: Maximum sentences per chunk
        split_overlap: Sentence overlap between chunks

    Returns:
        List of chunk dictionaries with text and metadata (document_name, page_numbers)
    """
    chunks = []
    i = 0

    while i < len(sentences_with_pages):
        # Get chunk of sentences
        chunk_sentences = sentences_with_pages[i:i + split_length]

        if not chunk_sentences:
            break

        # Extract text and page numbers
        chunk_text = ' '.join([s['text'] for s in chunk_sentences])
        page_numbers = sorted(list(set([s['page_number'] for s in chunk_sentences])))

        # Get starting page and line number within that page
        page_start = chunk_sentences[0]['page_number']
        line_start = chunk_sentences[0]['line_in_page']

        # Get ending page and line number within that page
        page_end = chunk_sentences[-1]['page_number']
        line_end = chunk_sentences[-1]['line_in_page']

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




def parse_documents(
    input_dir: str = "sprekers-info/Output Gemeente",
    split_length: int = 10,
    split_overlap: int = 2,
    max_files: int = None,
    output_format: str = "json"
) -> List[Dict]:
    """
    Parse all PDF documents and create chunks with accurate page numbers.

    Args:
        input_dir: Directory containing PDF files
        split_length: Maximum sentences per chunk
        split_overlap: Sentence overlap
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

    all_chunks = []

    # Process each file
    for idx, pdf_file in enumerate(pdf_files, 1):
        print(f"Processing [{idx}/{len(pdf_files)}]: {pdf_file.name}")

        try:
            # Extract document name and remove anonymization markers
            document_name = pdf_file.stem
            document_name = document_name.replace(' (geanonimiseerd)', '').replace('(geanonimiseerd)', '')

            # Extract sentences with page numbers
            sentences_with_pages = extract_text_with_pages(str(pdf_file))

            if not sentences_with_pages:
                print(f"  ✗ No text extracted")
                continue

            # Create chunks with accurate page tracking
            chunks = create_chunks_with_pages(
                sentences_with_pages,
                document_name,
                split_length,
                split_overlap
            )

            all_chunks.extend(chunks)
            print(f"  → Created {len(chunks)} chunks")

        except Exception as e:
            print(f"  ✗ Error: {e}")
            continue

    # Filter out chunks with meaningless text
    filtered_chunks = [
        chunk for chunk in all_chunks
        if chunk['text'].strip() != ". . . . . . . . . ."
    ]

    removed_count = len(all_chunks) - len(filtered_chunks)
    if removed_count > 0:
        print(f"\n✓ Filtered out {removed_count} chunks with text '. . . . . . . . . .'")

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
    INPUT_DIR = "sprekers-info/Output Gemeente"
    SPLIT_LENGTH = 10      # Max 10 sentences per chunk
    SPLIT_OVERLAP = 2      # 2 sentence overlap
    MAX_FILES = None       # Process all files (set to number for testing)
    OUTPUT_JSON = "parsed_chunks.json"
    OUTPUT_TXT = "parsed_chunks.txt"

    print("="*80)
    print("Text Parser with Haystack")
    print("="*80)
    print(f"Input directory: {INPUT_DIR}")
    print(f"Max sentences per chunk: {SPLIT_LENGTH}")
    print(f"Sentence overlap: {SPLIT_OVERLAP}")
    print(f"Metadata: document_name, page_numbers")
    print("="*80)
    print()

    # Parse documents
    chunks = parse_documents(
        input_dir=INPUT_DIR,
        split_length=SPLIT_LENGTH,
        split_overlap=SPLIT_OVERLAP,
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
