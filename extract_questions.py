#!/usr/bin/env python3
"""
Script to extract questions from Analyse_Woo_Vragen.md and save to JSON
"""

import json


def parse_markdown_table(file_path: str) -> list:
    """Parse the markdown table and extract questions with expected sources."""
    questions_data = []

    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Find table rows (skip header and separator rows)
    in_table = False
    for line in lines:
        line = line.strip()

        # Skip empty lines
        if not line:
            continue

        # Check if we're in the table
        if line.startswith('|') and '---' in line:
            in_table = True
            continue

        # Skip header row
        if 'Categorie' in line and 'Vraag' in line:
            continue

        # Parse data rows
        if in_table and line.startswith('|'):
            parts = [p.strip() for p in line.split('|')[1:-1]]  # Remove empty first/last elements

            if len(parts) >= 5:
                category = parts[0]
                question = parts[1]
                status = parts[2]
                answer = parts[3]
                sources = parts[4]

                # Only include questions that have sources (not "Onbeantwoord" or empty)
                if sources and sources != '' and status != 'Onbeantwoord':
                    # Split sources by comma and strip whitespace, filter out .md files
                    sources_list = [s.strip() for s in sources.split(',') if s.strip() and not s.strip().endswith('.md')]

                    # Only add if there are non-.md sources remaining
                    if sources_list:
                        questions_data.append({
                            'category': category,
                            'question': question,
                            'status': status,
                            'answer': answer,
                            'expected_sources': sources_list
                        })

    return questions_data


def main():
    """Extract questions and save to JSON."""
    md_file = '/Users/buraktezcan/Burak/hackathon-milvum/frontend/public/Analyse_Woo_Vragen.md'
    output_file = '/Users/buraktezcan/Burak/hackathon-milvum/questions.json'

    print("Extracting questions from markdown...")
    questions = parse_markdown_table(md_file)

    print(f"Found {len(questions)} questions with expected sources")

    # Save to JSON
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(questions, f, indent=2, ensure_ascii=False)

    print(f"Questions saved to: {output_file}")

    # Display summary
    print("\nQuestions by category:")
    categories = {}
    for q in questions:
        cat = q['category']
        if cat not in categories:
            categories[cat] = 0
        categories[cat] += 1

    for cat, count in categories.items():
        if cat:
            print(f"  {cat}: {count} questions")


if __name__ == '__main__':
    main()
