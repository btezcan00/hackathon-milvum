#!/usr/bin/env python3
"""
Extract all API returned sources from test_results.json
"""

import json


def extract_api_sources(test_results_file: str = "test_results.json") -> dict:
    """
    Extract all API returned sources from test results.

    Returns:
        Dictionary with all sources and unique sources
    """
    print(f"Reading {test_results_file}...")

    with open(test_results_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    all_sources = []
    unique_sources = set()

    # Extract sources from each result
    for result in data.get('results', []):
        api_sources = result.get('api_returned_sources', [])

        for source in api_sources:
            all_sources.append(source)
            unique_sources.add(source)

    return {
        'total_sources_count': len(all_sources),
        'unique_sources_count': len(unique_sources),
        'all_sources': all_sources,
        'unique_sources': sorted(list(unique_sources))
    }


def main():
    """Main function."""
    print("=" * 80)
    print("Extract API Returned Sources")
    print("=" * 80)
    print()

    # Extract sources
    sources_data = extract_api_sources()

    # Display summary
    print(f"Total sources returned (with duplicates): {sources_data['total_sources_count']}")
    print(f"Unique sources: {sources_data['unique_sources_count']}")
    print()

    # Save to JSON
    output_file = "api_returned_sources.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(sources_data, f, indent=2, ensure_ascii=False)

    print(f"✓ Saved to {output_file}")
    print()

    # Display unique sources
    print("Unique sources returned by API:")
    print("-" * 80)
    for i, source in enumerate(sources_data['unique_sources'], 1):
        print(f"{i:2d}. {source}")

    print()
    print("=" * 80)


if __name__ == '__main__':
    main()
