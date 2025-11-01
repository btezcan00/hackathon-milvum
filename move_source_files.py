#!/usr/bin/env python3
"""
Move files from source folder to destination folder based on api_returned_sources.json
"""

import json
import os
import shutil
from pathlib import Path


def load_sources(json_file: str = "api_returned_sources.json") -> list:
    """
    Load unique sources from JSON file.

    Args:
        json_file: Path to the api_returned_sources.json file

    Returns:
        List of unique source filenames
    """
    print(f"Loading sources from {json_file}...")

    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Use unique_sources to avoid duplicates
    sources = data.get('unique_sources', [])
    print(f"✓ Found {len(sources)} unique sources")

    return sources


def find_matching_files(source_folder: str, source_names: list) -> dict:
    """
    Find files in source folder that match the source names.

    Args:
        source_folder: Path to folder containing source files
        source_names: List of source document names

    Returns:
        Dictionary mapping source name to file path
    """
    print(f"\nSearching for files in {source_folder}...")

    source_path = Path(source_folder)
    if not source_path.exists():
        raise FileNotFoundError(f"Source folder not found: {source_folder}")

    # Get all files in source folder
    all_files = list(source_path.glob("**/*"))
    all_files = [f for f in all_files if f.is_file()]

    print(f"Found {len(all_files)} files in source folder")

    # Match source names to files
    matched_files = {}
    not_found = []

    for source_name in source_names:
        # Clean source name for comparison
        source_clean = source_name.strip()

        # Try to find exact match first
        found = False
        for file_path in all_files:
            file_name = file_path.name

            # Check if source name matches file name (with or without extension)
            if source_clean == file_name or source_clean == file_path.stem:
                matched_files[source_name] = file_path
                found = True
                break

        # If no exact match, try partial match
        if not found:
            for file_path in all_files:
                file_name = file_path.name.lower()
                source_lower = source_clean.lower()

                # Remove common suffixes for matching
                source_base = source_lower.replace('(geanonimiseerd)', '').strip()

                if source_base in file_name or file_name.replace('.pdf', '').replace('.docx', '') in source_lower:
                    matched_files[source_name] = file_path
                    found = True
                    break

        if not found:
            not_found.append(source_name)

    print(f"\n✓ Matched {len(matched_files)} files")
    if not_found:
        print(f"✗ Could not find {len(not_found)} files:")
        for name in not_found:
            print(f"  - {name}")

    return matched_files


def copy_files(matched_files: dict, dest_folder: str):
    """
    Copy files to destination folder (originals remain in source).

    Args:
        matched_files: Dictionary mapping source name to file path
        dest_folder: Destination folder path
    """
    dest_path = Path(dest_folder)
    dest_path.mkdir(parents=True, exist_ok=True)

    print(f"\nCopying {len(matched_files)} files to {dest_folder}...")

    copied_count = 0
    failed = []

    for source_name, file_path in matched_files.items():
        try:
            dest_file = dest_path / file_path.name

            # Check if file already exists
            if dest_file.exists():
                print(f"  ⚠ Skipping (already exists): {file_path.name}")
                continue

            # Copy file (original remains in source folder)
            shutil.copy2(file_path, dest_file)

            copied_count += 1
            print(f"  ✓ {file_path.name}")

        except Exception as e:
            failed.append((source_name, str(e)))
            print(f"  ✗ Failed to copy {file_path.name}: {e}")

    print(f"\n✓ Copied {copied_count} files successfully")

    if failed:
        print(f"✗ Failed to copy {len(failed)} files")


def main():
    """Main function."""
    print("=" * 80)
    print("Copy Source Files Based on API Results")
    print("=" * 80)
    print()

    # Configuration
    JSON_FILE = "api_returned_sources.json"
    SOURCE_FOLDER = "sprekers-info/Output Gemeente"  # Change this to your actual folder name
    DEST_FOLDER = "unique files"

    # Check if JSON file exists
    if not os.path.exists(JSON_FILE):
        print(f"✗ Error: {JSON_FILE} not found!")
        print("Please run extract_api_sources.py first to generate this file.")
        return

    # Load sources from JSON
    sources = load_sources(JSON_FILE)

    if not sources:
        print("No sources found in JSON file!")
        return

    # Find matching files
    try:
        matched_files = find_matching_files(SOURCE_FOLDER, sources)
    except FileNotFoundError as e:
        print(f"\n✗ Error: {e}")
        print(f"\nPlease update SOURCE_FOLDER in the script to the correct path.")
        return

    if not matched_files:
        print("\nNo matching files found!")
        return

    # Copy files (originals will remain in source folder)
    print(f"\nReady to copy {len(matched_files)} files (duplicates will be created)")
    print(f"From: {SOURCE_FOLDER}")
    print(f"To:   {DEST_FOLDER}")

    response = input(f"\nProceed with copy? (y/n): ")
    if response.lower() != 'y':
        print("Cancelled.")
        return

    copy_files(matched_files, DEST_FOLDER)

    print("\n" + "=" * 80)
    print("✓ Complete! Original files remain in source folder.")
    print("=" * 80)


if __name__ == '__main__':
    main()
