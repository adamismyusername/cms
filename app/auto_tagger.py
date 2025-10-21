"""
Auto-Tagging Module for Quotes System

This module provides functionality to automatically tag quotes based on keyword matching.
Keywords and their associated tags are loaded from a CSV file and cached in memory.
"""

import csv
import re
import os
from typing import List, Dict, Set

# Global cache for keyword mappings
_keyword_mappings: Dict[str, List[str]] = {}
_csv_path = os.path.join(os.path.dirname(__file__), 'data', 'auto-tag-keywords.csv')


def load_keyword_mappings(csv_path: str = None) -> Dict[str, List[str]]:
    """
    Load keyword-to-tags mappings from CSV file.

    CSV format:
    keyword,tags
    gold,"gold, precious metals"
    inflation,"inflation, economy"

    Args:
        csv_path: Path to CSV file (defaults to app/data/auto-tag-keywords.csv)

    Returns:
        Dictionary mapping keywords to list of tags
    """
    global _keyword_mappings, _csv_path

    if csv_path:
        _csv_path = csv_path

    mappings = {}

    try:
        if not os.path.exists(_csv_path):
            print(f"Warning: Auto-tag keywords CSV not found at {_csv_path}")
            print("Auto-tagging will be disabled. Place your CSV file at this location.")
            return mappings

        with open(_csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)

            for row in reader:
                keyword = row.get('keyword', '').strip().lower()
                tags_str = row.get('tags', '').strip()

                if keyword and tags_str:
                    # Parse comma-separated tags and normalize them
                    tags = [tag.strip().lower() for tag in tags_str.split(',') if tag.strip()]
                    mappings[keyword] = tags

        _keyword_mappings = mappings
        print(f"Loaded {len(mappings)} keyword mappings from {_csv_path}")

    except Exception as e:
        print(f"Error loading keyword mappings: {e}")
        _keyword_mappings = {}

    return _keyword_mappings


def reload_keyword_mappings() -> int:
    """
    Reload keyword mappings from CSV file without restarting the app.

    Returns:
        Number of keyword mappings loaded
    """
    load_keyword_mappings()
    return len(_keyword_mappings)


def get_keyword_mappings() -> Dict[str, List[str]]:
    """
    Get cached keyword mappings. Loads from CSV if not already loaded.

    Returns:
        Dictionary mapping keywords to list of tags
    """
    global _keyword_mappings

    if not _keyword_mappings:
        load_keyword_mappings()

    return _keyword_mappings


def extract_keywords(text: str) -> Set[str]:
    """
    Extract matching keywords from text using whole-word, case-insensitive matching.

    Args:
        text: The text to search for keywords

    Returns:
        Set of matched keywords (lowercase)
    """
    if not text:
        return set()

    mappings = get_keyword_mappings()
    if not mappings:
        return set()

    matched_keywords = set()
    text_lower = text.lower()

    for keyword in mappings.keys():
        # Escape special regex characters in keyword
        escaped_keyword = re.escape(keyword)

        # Use word boundaries for whole-word matching
        # \b doesn't work well with some special chars, so we use a more robust pattern
        pattern = r'(?<![a-zA-Z])' + escaped_keyword + r'(?![a-zA-Z])'

        if re.search(pattern, text_lower):
            matched_keywords.add(keyword)

    return matched_keywords


def generate_auto_tags(quote_text: str, removed_tags: List[str] = None) -> List[str]:
    """
    Generate auto-tags for a quote based on keyword matching.

    Args:
        quote_text: The quote text to analyze
        removed_tags: List of tags that user manually removed (won't be reapplied)

    Returns:
        List of unique auto-tags to apply (lowercase, deduplicated)
    """
    if not quote_text:
        return []

    # Get keyword mappings
    mappings = get_keyword_mappings()
    if not mappings:
        return []

    # Extract matching keywords
    matched_keywords = extract_keywords(quote_text)

    # Collect all tags from matched keywords
    all_tags = set()
    for keyword in matched_keywords:
        tags = mappings.get(keyword, [])
        all_tags.update(tags)

    # Remove any tags that user explicitly removed
    if removed_tags:
        removed_tags_lower = {tag.lower() for tag in removed_tags}
        all_tags = all_tags - removed_tags_lower

    # Return sorted list for consistency
    return sorted(list(all_tags))


def get_tag_statistics(all_quotes_data: List[Dict]) -> Dict:
    """
    Generate statistics about auto-tag usage across all quotes.

    Args:
        all_quotes_data: List of quote dictionaries with 'auto_tags' field

    Returns:
        Dictionary with statistics:
        - total_quotes: Total number of quotes
        - quotes_with_auto_tags: Number of quotes with at least one auto-tag
        - coverage_percentage: Percentage of quotes with auto-tags
        - tag_frequency: Dict mapping tags to their frequency count
        - top_tags: List of (tag, count) tuples for most common tags
    """
    total_quotes = len(all_quotes_data)
    quotes_with_auto_tags = 0
    tag_frequency = {}

    for quote in all_quotes_data:
        auto_tags = quote.get('auto_tags', [])

        if auto_tags:
            quotes_with_auto_tags += 1

            for tag in auto_tags:
                tag_lower = tag.lower()
                tag_frequency[tag_lower] = tag_frequency.get(tag_lower, 0) + 1

    # Calculate coverage percentage
    coverage_percentage = (quotes_with_auto_tags / total_quotes * 100) if total_quotes > 0 else 0

    # Get top tags (sorted by frequency)
    top_tags = sorted(tag_frequency.items(), key=lambda x: x[1], reverse=True)[:20]

    return {
        'total_quotes': total_quotes,
        'quotes_with_auto_tags': quotes_with_auto_tags,
        'coverage_percentage': round(coverage_percentage, 1),
        'tag_frequency': tag_frequency,
        'top_tags': top_tags,
        'total_unique_auto_tags': len(tag_frequency),
        'total_keyword_mappings': len(get_keyword_mappings())
    }


# Load keywords on module import
load_keyword_mappings()
