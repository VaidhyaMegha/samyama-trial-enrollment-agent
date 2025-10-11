"""
Section Classifier Lambda Function

Processes Textract output to extract and classify inclusion/exclusion criteria.
Uses Amazon Comprehend Medical for entity detection and section classification.

Features:
- Multi-strategy extraction (queries, tables, pattern matching)
- Intelligent criteria splitting (atomic units)
- Text cleaning and normalization
- Confidence scoring
- Handles edge cases (split sentences, references, nested lists)
"""

import json
import os
import re
from typing import Dict, List, Any, Optional, Tuple
import boto3
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext

logger = Logger()
tracer = Tracer()

# Initialize AWS clients
comprehend_medical = boto3.client('comprehendmedical', region_name=os.environ.get('AWS_REGION', 'us-east-1'))

# Configuration
MIN_CRITERION_LENGTH = int(os.environ.get('MIN_CRITERION_LENGTH', '10'))
MAX_CRITERION_LENGTH = int(os.environ.get('MAX_CRITERION_LENGTH', '500'))
USE_COMPREHEND_MEDICAL = os.environ.get('USE_COMPREHEND_MEDICAL', 'true').lower() == 'true'


@tracer.capture_method
def extract_criteria_from_queries(query_answers: Dict[str, Dict]) -> Dict[str, str]:
    """
    Extract criteria from Textract Query results.

    This is the fastest and most reliable method when Textract Queries work well.
    Supports both direct query answers and pattern-based extraction.

    Args:
        query_answers: Query answers from Textract

    Returns:
        Dictionary with inclusion and exclusion criteria text
    """
    criteria = {
        'inclusion': '',
        'exclusion': ''
    }

    # Try multiple inclusion criteria aliases (order of preference)
    inclusion_aliases = [
        'INCLUSION_CRITERIA',           # Direct query answer
        'INCLUSION_CRITERIA_PATTERN',   # Pattern-based extraction
        'INCLUSION_CRITERIA_LIST',      # Alternative query
        'INCLUSION_REQUIREMENTS'        # Alternative query
    ]

    for alias in inclusion_aliases:
        if alias in query_answers:
            inclusion_data = query_answers[alias]
            if inclusion_data.get('confidence', 0) > 0.6:  # Only use if confidence > 60%
                criteria['inclusion'] = inclusion_data['text']
                logger.info(f"Extracted inclusion criteria from '{alias}' (confidence: {inclusion_data['confidence']:.2%})")
                break  # Use the first match

    # Try multiple exclusion criteria aliases (order of preference)
    exclusion_aliases = [
        'EXCLUSION_CRITERIA',           # Direct query answer
        'EXCLUSION_CRITERIA_PATTERN',   # Pattern-based extraction
        'EXCLUSION_CRITERIA_LIST',      # Alternative query
        'EXCLUSION_FACTORS'             # Alternative query
    ]

    for alias in exclusion_aliases:
        if alias in query_answers:
            exclusion_data = query_answers[alias]
            if exclusion_data.get('confidence', 0) > 0.6:
                criteria['exclusion'] = exclusion_data['text']
                logger.info(f"Extracted exclusion criteria from '{alias}' (confidence: {exclusion_data['confidence']:.2%})")
                break  # Use the first match

    return criteria


@tracer.capture_method
def extract_criteria_from_tables(tables: List[Dict]) -> Dict[str, List[str]]:
    """
    Extract criteria from structured tables.

    Common in modern protocols where criteria are presented in table format.

    Args:
        tables: List of extracted tables from Textract

    Returns:
        Dictionary with lists of inclusion and exclusion criteria
    """
    inclusion_criteria = []
    exclusion_criteria = []

    # Only process eligibility tables
    eligibility_tables = [t for t in tables if t.get('is_eligibility', False)]

    logger.info(f"Processing {len(eligibility_tables)} eligibility tables")

    for table in eligibility_tables:
        headers = [h.lower() for h in table.get('headers', [])]
        rows = table.get('rows', [])

        # Find inclusion/exclusion column indices
        inclusion_col = None
        exclusion_col = None

        for i, header in enumerate(headers):
            if any(kw in header for kw in ['inclusion', 'include', 'eligible']):
                inclusion_col = i
            elif any(kw in header for kw in ['exclusion', 'exclude', 'ineligible']):
                exclusion_col = i

        # Extract criteria from rows
        # Use lower threshold for tables (more structured, reliable)
        table_min_length = max(5, MIN_CRITERION_LENGTH // 2)

        for row in rows:
            if inclusion_col is not None and inclusion_col < len(row):
                cell_text = row[inclusion_col].strip()
                if cell_text and len(cell_text) >= table_min_length:
                    inclusion_criteria.append(cell_text)

            if exclusion_col is not None and exclusion_col < len(row):
                cell_text = row[exclusion_col].strip()
                if cell_text and len(cell_text) >= table_min_length:
                    exclusion_criteria.append(cell_text)

    logger.info(f"Extracted {len(inclusion_criteria)} inclusion + {len(exclusion_criteria)} exclusion criteria from tables")

    return {
        'inclusion': inclusion_criteria,
        'exclusion': exclusion_criteria
    }


@tracer.capture_method
def split_into_atomic_criteria(text: str) -> List[str]:
    """
    Split text into atomic criteria (individual items).

    Handles various formats:
    - Numbered lists: "1. Age >= 18", "2. Type 2 Diabetes"
    - Bullet points: "• Lab test", "- Diagnosis"
    - Letter lists: "A. Criterion", "B. Criterion"
    - Sentence boundaries

    Args:
        text: Raw criteria text

    Returns:
        List of individual criteria
    """
    if not text:
        return []

    criteria = []

    # Split by common list delimiters
    # Pattern: newline followed by number/letter/bullet + period/space
    split_patterns = [
        r'\n\d+\.\s+',          # "1. ", "2. "
        r'\n[a-zA-Z]\.\s+',     # "A. ", "B. "
        r'\n[•\-\*]\s+',        # "• ", "- ", "* "
        r'\n\(\d+\)\s+',        # "(1) ", "(2) "
        r'\n[ivxIVX]+\.\s+',    # Roman numerals "i. ", "ii. "
    ]

    # Try each pattern
    for pattern in split_patterns:
        if re.search(pattern, text):
            # Split by pattern
            parts = re.split(pattern, text)

            # Clean and filter parts
            for part in parts:
                cleaned = part.strip()

                # Remove leading numbers/bullets that weren't caught
                cleaned = re.sub(r'^[\d\.\)\-\•\*\s]+', '', cleaned)

                if MIN_CRITERION_LENGTH <= len(cleaned) <= MAX_CRITERION_LENGTH:
                    criteria.append(cleaned)

            if criteria:
                logger.info(f"Split criteria using pattern: {pattern} -> {len(criteria)} items")
                return criteria

    # Fallback: Split by sentence boundaries if no patterns matched
    sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)

    for sentence in sentences:
        cleaned = sentence.strip()
        if MIN_CRITERION_LENGTH <= len(cleaned) <= MAX_CRITERION_LENGTH:
            criteria.append(cleaned)

    # If still empty, return the whole text as one criterion
    if not criteria and len(text) >= MIN_CRITERION_LENGTH:
        criteria.append(text.strip())

    logger.info(f"Split into {len(criteria)} atomic criteria")

    return criteria


@tracer.capture_method
def clean_criterion_text(text: str) -> str:
    """
    Clean and normalize criterion text.

    Removes:
    - Extra whitespace
    - Line breaks within criterion
    - Special characters (non-breaking spaces, etc.)
    - Leading/trailing punctuation artifacts

    Args:
        text: Raw criterion text

    Returns:
        Cleaned criterion text
    """
    if not text:
        return ""

    # Replace multiple spaces/tabs with single space
    cleaned = re.sub(r'\s+', ' ', text)

    # Remove non-breaking spaces and other unicode whitespace
    cleaned = re.sub(r'[\u00A0\u2000-\u200B\u202F\u205F\u3000]', ' ', cleaned)

    # Remove leading/trailing dashes, bullets, etc.
    cleaned = re.sub(r'^[\-\•\*\s]+|[\-\•\*\s]+$', '', cleaned)

    # Fix common OCR errors
    cleaned = cleaned.replace('≥', '>=')
    cleaned = cleaned.replace('≤', '<=')
    cleaned = cleaned.replace('−', '-')  # Minus sign to hyphen

    # Trim
    cleaned = cleaned.strip()

    return cleaned


@tracer.capture_method
def merge_split_sentences(criteria: List[str]) -> List[str]:
    """
    Merge criteria that were split mid-sentence across pages.

    Detects incomplete sentences by looking for mid-phrase endings.

    Args:
        criteria: List of individual criteria

    Returns:
        List with merged criteria
    """
    merged = []
    pending = None

    # Words that suggest sentence ends mid-phrase (incomplete)
    incomplete_endings = [
        'have', 'has', 'had', 'be', 'been', 'being',  # Auxiliary verbs
        'must', 'shall', 'should', 'will', 'would', 'can', 'could',  # Modals
        'with', 'without', 'of', 'to', 'from', 'in', 'on', 'at', 'by',  # Prepositions
        'a', 'an', 'the',  # Articles
        'and', 'or', 'but',  # Conjunctions
        'documented', 'confirmed', 'including'  # Common incomplete endings
    ]

    for criterion in criteria:
        if pending:
            # Merge with previous incomplete criterion
            merged_text = pending + ' ' + criterion
            pending = None

            # Check if merged result is still incomplete
            last_word = merged_text.rstrip('.,!?;:').split()[-1].lower() if merged_text.split() else ''
            still_incomplete = (
                last_word in incomplete_endings and
                not merged_text.rstrip().endswith(('.', '!', '?', ';', ':'))
            )

            if still_incomplete:
                pending = merged_text
            else:
                merged.append(merged_text)
        else:
            # Check if this criterion ends mid-phrase
            last_word = criterion.rstrip('.,!?;:').split()[-1].lower() if criterion.split() else ''
            ends_with_punctuation = criterion.rstrip().endswith(('.', '!', '?', ';', ':'))

            # Incomplete if ends with incomplete word and no punctuation
            is_incomplete = (
                last_word in incomplete_endings and
                not ends_with_punctuation
            )

            if is_incomplete:
                pending = criterion
            else:
                merged.append(criterion)

    # Add any remaining pending criterion
    if pending:
        merged.append(pending)

    if len(merged) < len(criteria):
        logger.info(f"Merged {len(criteria) - len(merged)} split sentences")

    return merged


@tracer.capture_method
def classify_criterion_type(criterion: str) -> str:
    """
    Classify if a criterion is inclusion or exclusion based on keywords.

    Used as fallback when section headers aren't clear.

    Args:
        criterion: Criterion text

    Returns:
        'inclusion' or 'exclusion'
    """
    criterion_lower = criterion.lower()

    # Exclusion keywords
    exclusion_keywords = [
        'no ', 'not ', 'must not', 'cannot', 'prohibited',
        'exclude', 'exclusion', 'ineligible',
        'absence of', 'without', 'except',
        'contraindication', 'history of'
    ]

    # Count exclusion signals
    exclusion_score = sum(1 for kw in exclusion_keywords if kw in criterion_lower)

    if exclusion_score > 0:
        return 'exclusion'

    return 'inclusion'


@tracer.capture_method
def analyze_with_comprehend_medical(text: str) -> Dict[str, Any]:
    """
    Analyze text with Amazon Comprehend Medical to detect medical entities.

    Used for:
    - Validating criteria contain medical content
    - Calculating entity density (medical terms per 100 words)
    - Filtering non-criteria text

    Args:
        text: Text to analyze

    Returns:
        Dictionary with entities and metrics
    """
    if not USE_COMPREHEND_MEDICAL or not text or len(text) < 20:
        return {'entities': [], 'entity_density': 0}

    try:
        # Truncate if too long (API limit is 20,000 UTF-8 bytes)
        if len(text.encode('utf-8')) > 20000:
            text = text[:5000]  # Take first ~5000 characters

        response = comprehend_medical.detect_entities_v2(Text=text)

        entities = response.get('Entities', [])
        word_count = len(text.split())
        entity_density = (len(entities) / word_count * 100) if word_count > 0 else 0

        logger.info(f"Comprehend Medical: {len(entities)} entities, density={entity_density:.1f}%")

        return {
            'entities': entities,
            'entity_density': entity_density,
            'entity_types': [e['Type'] for e in entities]
        }

    except Exception as e:
        logger.warning(f"Comprehend Medical error: {str(e)}")
        return {'entities': [], 'entity_density': 0}


@tracer.capture_method
def filter_non_criteria_text(criteria: List[str]) -> List[str]:
    """
    Filter out non-criteria text (references, notes, instructions).

    Removes:
    - Very short items (< 5 chars - too generic)
    - Very long items (> MAX_CRITERION_LENGTH)
    - References ("See Section X.Y")
    - Administrative text ("Complete informed consent")

    Args:
        criteria: List of criteria

    Returns:
        Filtered list
    """
    filtered = []

    # Patterns to exclude (administrative text, not medical criteria)
    exclude_patterns = [
        r'^see section',
        r'^refer to',
        r'^as defined in',
        r'^per protocol',
        r'^complete.*informed consent',  # "Complete informed consent" (instruction)
        r'^sign.*informed consent',      # "Sign informed consent" (instruction)
        r'^provide.*informed consent',   # "Provide informed consent" (instruction)
        r'institutional review board',
        r'^note:',
        r'^example:',
    ]

    # Use more lenient minimum (5 chars) to allow short but valid criteria
    # like "Pregnant", "Age >= 18", etc.
    filter_min_length = 5

    for criterion in criteria:
        criterion_lower = criterion.lower()

        # Check length (use lenient minimum, strict maximum)
        if not (filter_min_length <= len(criterion) <= MAX_CRITERION_LENGTH):
            continue

        # Check exclusion patterns
        if any(re.search(pattern, criterion_lower) for pattern in exclude_patterns):
            logger.debug(f"Filtered out: {criterion[:50]}...")
            continue

        filtered.append(criterion)

    if len(filtered) < len(criteria):
        logger.info(f"Filtered out {len(criteria) - len(filtered)} non-criteria items")

    return filtered


@tracer.capture_method
def format_criteria_for_parse_api(
    inclusion_criteria: List[str],
    exclusion_criteria: List[str]
) -> str:
    """
    Format criteria in the format expected by parse-criteria API.

    Output format:
    Inclusion Criteria:
    - Criterion 1
    - Criterion 2

    Exclusion Criteria:
    - Criterion 1
    - Criterion 2

    Args:
        inclusion_criteria: List of inclusion criteria
        exclusion_criteria: List of exclusion criteria

    Returns:
        Formatted criteria text
    """
    output = ""

    if inclusion_criteria:
        output += "Inclusion Criteria:\n"
        for criterion in inclusion_criteria:
            output += f"- {criterion}\n"

    if exclusion_criteria:
        if output:
            output += "\n"
        output += "Exclusion Criteria:\n"
        for criterion in exclusion_criteria:
            output += f"- {criterion}\n"

    return output.strip()


@logger.inject_lambda_context(log_event=True)
@tracer.capture_lambda_handler
def lambda_handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    Lambda handler for section classification and criteria extraction.

    Expected event format:
    {
        "textract_output": {
            "query_answers": {...},
            "tables": [...],
            "confidence": 0.89
        },
        "trial_id": "NCT12345678"
    }

    Returns:
    {
        "statusCode": 200,
        "body": {
            "trial_id": "NCT12345678",
            "inclusion_criteria": [...],
            "exclusion_criteria": [...],
            "formatted_text": "Inclusion Criteria:\n- ...",
            "metadata": {...}
        }
    }
    """
    try:
        # Extract input
        textract_output = event.get('textract_output', {})
        trial_id = event.get('trial_id', 'unknown')

        if not textract_output:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Missing required field: textract_output'
                })
            }

        logger.info(f"Processing criteria for trial: {trial_id}")

        # Strategy 1: Extract from Textract queries (fastest, most reliable)
        query_answers = textract_output.get('query_answers', {})
        criteria_from_queries = extract_criteria_from_queries(query_answers)

        # Strategy 2: Extract from tables (for structured protocols)
        tables = textract_output.get('tables', [])
        criteria_from_tables = extract_criteria_from_tables(tables)

        # Combine strategies
        inclusion_text = criteria_from_queries.get('inclusion', '')
        exclusion_text = criteria_from_queries.get('exclusion', '')

        # Split into atomic criteria
        inclusion_criteria = split_into_atomic_criteria(inclusion_text)
        exclusion_criteria = split_into_atomic_criteria(exclusion_text)

        # Add criteria from tables
        inclusion_criteria.extend(criteria_from_tables.get('inclusion', []))
        exclusion_criteria.extend(criteria_from_tables.get('exclusion', []))

        # Clean all criteria
        inclusion_criteria = [clean_criterion_text(c) for c in inclusion_criteria]
        exclusion_criteria = [clean_criterion_text(c) for c in exclusion_criteria]

        # Merge split sentences
        inclusion_criteria = merge_split_sentences(inclusion_criteria)
        exclusion_criteria = merge_split_sentences(exclusion_criteria)

        # Filter non-criteria text
        inclusion_criteria = filter_non_criteria_text(inclusion_criteria)
        exclusion_criteria = filter_non_criteria_text(exclusion_criteria)

        # Remove duplicates while preserving order
        inclusion_criteria = list(dict.fromkeys(inclusion_criteria))
        exclusion_criteria = list(dict.fromkeys(exclusion_criteria))

        # Analyze with Comprehend Medical (optional)
        medical_analysis = {}
        if USE_COMPREHEND_MEDICAL:
            sample_text = ' '.join(inclusion_criteria[:5] + exclusion_criteria[:5])
            medical_analysis = analyze_with_comprehend_medical(sample_text)

        # Format for parse-criteria API
        formatted_text = format_criteria_for_parse_api(
            inclusion_criteria,
            exclusion_criteria
        )

        # Calculate confidence
        textract_confidence = textract_output.get('confidence', 0.5)
        extraction_confidence = 1.0 if (inclusion_criteria or exclusion_criteria) else 0.0
        overall_confidence = (textract_confidence + extraction_confidence) / 2

        # Prepare metadata
        metadata = {
            'total_criteria': len(inclusion_criteria) + len(exclusion_criteria),
            'inclusion_count': len(inclusion_criteria),
            'exclusion_count': len(exclusion_criteria),
            'textract_confidence': textract_confidence,
            'extraction_confidence': extraction_confidence,
            'overall_confidence': overall_confidence,
            'extraction_methods': {
                'queries': bool(criteria_from_queries.get('inclusion') or criteria_from_queries.get('exclusion')),
                'tables': bool(criteria_from_tables.get('inclusion') or criteria_from_tables.get('exclusion'))
            },
            'medical_entity_density': medical_analysis.get('entity_density', 0)
        }

        logger.info(
            f"Extracted {len(inclusion_criteria)} inclusion + "
            f"{len(exclusion_criteria)} exclusion criteria "
            f"(confidence: {overall_confidence:.2%})"
        )

        result = {
            'trial_id': trial_id,
            'inclusion_criteria': inclusion_criteria,
            'exclusion_criteria': exclusion_criteria,
            'formatted_text': formatted_text,
            'metadata': metadata,
            'status': 'success'
        }

        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json'
            },
            'body': json.dumps(result)
        }

    except Exception as e:
        logger.error(f"Error in section classification: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Section classification failed',
                'message': str(e)
            })
        }
