#!/usr/bin/env python3
"""
Script to test questions from questions.json against the chat API
and calculate success rate based on matching sources.
"""

import requests
import json
import re
from typing import List, Dict, Tuple
import time


def load_questions(file_path: str) -> List[Dict[str, str]]:
    """Load questions from JSON file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        questions = json.load(f)
    return questions


def extract_document_names(sources_list: List[str]) -> List[str]:
    """Extract document names from the sources list, filtering out .md files."""
    # Filter out .md files, only keep .pdf and other non-.md sources
    return [s.strip() for s in sources_list if s.strip() and not s.strip().endswith('.md')]


def query_api(question: str, api_url: str = "http://localhost:5001/api/chat") -> Dict:
    """Send a question to the API and return the response."""
    try:
        payload = {
            "query": question
        }

        response = requests.post(api_url, json=payload, timeout=30)
        response.raise_for_status()

        return response.json()
    except Exception as e:
        print(f"Error querying API: {e}")
        return None


def check_source_match(expected_sources: List[str], api_response: Dict) -> Tuple[bool, List[str], List[str], List[str], List[str]]:
    """
    Check which of the API returned sources match the expected sources.
    Returns: (overall_matched, expected_docs, found_docs, matched_expected, not_matched_expected)
    """
    if not api_response or 'sources' not in api_response:
        return False, [], [], [], []

    # Extract expected document names
    expected_docs = extract_document_names(expected_sources)

    # Extract API returned document names
    found_docs = []
    for source in api_response.get('sources', []):
        metadata = source.get('metadata', {})
        doc_name = metadata.get('document_name', '')
        if doc_name and doc_name not in found_docs:
            found_docs.append(doc_name)

    # Track which expected sources were found and which weren't
    matched_expected = []
    not_matched_expected = []

    # Check for matches for each expected source
    for expected in expected_docs:
        expected_clean = expected.replace('.md', '').replace('.pdf', '').replace('(geanonimiseerd)', '').strip()
        found_match = False

        for found in found_docs:
            found_clean = found.replace('(geanonimiseerd)', '').strip()
            # Check if there's significant overlap
            if expected_clean.lower() in found_clean.lower() or found_clean.lower() in expected_clean.lower():
                found_match = True
                break

        if found_match:
            matched_expected.append(expected)
        else:
            not_matched_expected.append(expected)

    # Overall match is true if at least one expected source was found
    overall_matched = len(matched_expected) > 0

    return overall_matched, expected_docs, found_docs, matched_expected, not_matched_expected


def main():
    """Main function to run the test."""
    print("=" * 80)
    print("Testing Questions from questions.json")
    print("=" * 80)
    print()

    # Load questions from JSON file
    json_file = '/Users/buraktezcan/Burak/hackathon-milvum/questions.json'
    questions = load_questions(json_file)

    print(f"Found {len(questions)} questions to test")
    print()

    # Test each question
    results = []
    total_questions = 0
    successful_matches = 0

    for i, q_data in enumerate(questions, 1):
        question = q_data['question']
        expected_sources = q_data['expected_sources']

        print(f"\n[{i}/{len(questions)}] Testing question:")
        print(f"Q: {question[:100]}..." if len(question) > 100 else f"Q: {question}")
        print(f"Category: {q_data['category']}")

        # Query the API
        print("Querying API...")
        response = query_api(question)

        # Small delay to avoid overwhelming the API
        time.sleep(0.5)

        # Check if sources match
        matched, expected_docs, found_docs, matched_expected, not_matched_expected = check_source_match(expected_sources, response)

        total_questions += 1
        if matched:
            successful_matches += 1
            print("✓ MATCH FOUND")
        else:
            print("✗ NO MATCH")

        print(f"Expected sources: {expected_docs}")
        print(f"  ✓ Matched: {matched_expected}")
        print(f"  ✗ Not matched: {not_matched_expected}")
        print(f"API returned sources: {found_docs}")

        results.append({
            'question': question,
            'category': q_data['category'],
            'matched': matched,
            'expected_sources': expected_docs,
            'matched_sources': matched_expected,
            'not_matched_sources': not_matched_expected,
            'api_returned_sources': found_docs
        })

    # Calculate and display results
    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)
    print(f"Total questions tested: {total_questions}")
    print(f"Successful matches: {successful_matches}")
    print(f"Failed matches: {total_questions - successful_matches}")

    if total_questions > 0:
        success_rate = (successful_matches / total_questions) * 100
        print(f"Success Rate: {success_rate:.2f}%")
    else:
        print("No questions to test!")

    # Save detailed results to a JSON file
    output_file = 'test_results.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'total_questions': total_questions,
            'successful_matches': successful_matches,
            'success_rate': f"{success_rate:.2f}%" if total_questions > 0 else "N/A",
            'results': results
        }, f, indent=2, ensure_ascii=False)

    print(f"\nDetailed results saved to: {output_file}")

    # Show detailed breakdown
    print("\n" + "=" * 80)
    print("DETAILED BREAKDOWN")
    print("=" * 80)
    for i, result in enumerate(results, 1):
        status = "✓ PASS" if result['matched'] else "✗ FAIL"
        print(f"\n{i}. [{status}] {result['question'][:80]}...")
        print(f"   Expected sources: {result['expected_sources']}")
        print(f"   ✓ Matched: {result['matched_sources']}")
        print(f"   ✗ Not matched: {result['not_matched_sources']}")
        print(f"   API returned: {result['api_returned_sources']}")


if __name__ == '__main__':
    main()
