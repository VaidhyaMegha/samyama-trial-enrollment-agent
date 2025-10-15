"""
Textract Processor Lambda Function

Extracts text, tables, and structured data from protocol PDF documents using Amazon Textract.
Optimized for clinical trial protocol documents (100-200+ pages).

Features:
- Asynchronous processing for large documents
- Query-based extraction (targeted criteria extraction)
- Table extraction (structured inclusion/exclusion tables)
- Confidence scoring
- Production error handling
"""

import json
import os
import time
from typing import Dict, List, Any, Optional
import boto3
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext

logger = Logger()
tracer = Tracer()

# Initialize AWS clients
textract = boto3.client('textract', region_name=os.environ.get('AWS_REGION', 'us-east-1'))
s3 = boto3.client('s3', region_name=os.environ.get('AWS_REGION', 'us-east-1'))
lambda_client = boto3.client('lambda', region_name=os.environ.get('AWS_REGION', 'us-east-1'))

# Configuration
MAX_WAIT_TIME = int(os.environ.get('TEXTRACT_MAX_WAIT_TIME', '300'))  # 5 minutes
POLL_INTERVAL = int(os.environ.get('TEXTRACT_POLL_INTERVAL', '5'))  # 5 seconds
PROTOCOL_ORCHESTRATOR_FUNCTION = os.environ.get('PROTOCOL_ORCHESTRATOR_FUNCTION', 'TrialEnrollment-ProtocolOrchestrator')
AUTO_TRIGGER_ORCHESTRATOR = os.environ.get('AUTO_TRIGGER_ORCHESTRATOR', 'true').lower() == 'true'


@tracer.capture_method
def start_textract_job(s3_bucket: str, s3_key: str) -> str:
    """
    Start asynchronous Textract document analysis job.

    Uses Queries feature to directly extract inclusion/exclusion criteria.

    Args:
        s3_bucket: S3 bucket containing the protocol PDF
        s3_key: S3 key of the protocol PDF

    Returns:
        Textract job ID
    """
    try:
        logger.info(f"Starting Textract job for s3://{s3_bucket}/{s3_key}")

        response = textract.start_document_analysis(
            DocumentLocation={
                'S3Object': {
                    'Bucket': s3_bucket,
                    'Name': s3_key
                }
            },
            FeatureTypes=[
                'TABLES',      # Extract tables (often contain criteria)
                'LAYOUT',      # Understand document structure
                'QUERIES'      # Ask specific questions
            ],
            QueriesConfig={
                'Queries': [
                    # === PRIMARY INCLUSION CRITERIA QUERIES ===
                    {
                        'Text': 'What are the inclusion criteria for patient enrollment?',
                        'Alias': 'INCLUSION_CRITERIA'
                    },
                    {
                        'Text': 'List all inclusion criteria for study participants.',
                        'Alias': 'INCLUSION_CRITERIA_LIST'
                    },
                    {
                        'Text': 'What requirements must patients meet to be included in this study?',
                        'Alias': 'INCLUSION_REQUIREMENTS'
                    },
                    # === PRIMARY EXCLUSION CRITERIA QUERIES ===
                    {
                        'Text': 'What are the exclusion criteria for patient enrollment?',
                        'Alias': 'EXCLUSION_CRITERIA'
                    },
                    {
                        'Text': 'List all exclusion criteria for study participants.',
                        'Alias': 'EXCLUSION_CRITERIA_LIST'
                    },
                    {
                        'Text': 'What conditions or factors exclude patients from this study?',
                        'Alias': 'EXCLUSION_FACTORS'
                    },
                    # === ALTERNATIVE TERMINOLOGY ===
                    {
                        'Text': 'What are the eligibility criteria for this clinical trial?',
                        'Alias': 'ELIGIBILITY_CRITERIA'
                    },
                    {
                        'Text': 'What are the key patient selection criteria?',
                        'Alias': 'SELECTION_CRITERIA'
                    },
                    {
                        'Text': 'What are the subject enrollment criteria?',
                        'Alias': 'ENROLLMENT_CRITERIA'
                    },
                    # === METADATA QUERIES ===
                    {
                        'Text': 'What is the study phase?',
                        'Alias': 'STUDY_PHASE'
                    },
                    {
                        'Text': 'What is the primary indication or disease being studied?',
                        'Alias': 'INDICATION'
                    },
                    {
                        'Text': 'What is the trial title?',
                        'Alias': 'TRIAL_TITLE'
                    }
                ]
            },
            # Optional: Add notification SNS topic for long-running jobs
            # NotificationChannel={
            #     'SNSTopicArn': os.environ.get('TEXTRACT_SNS_TOPIC_ARN'),
            #     'RoleArn': os.environ.get('TEXTRACT_ROLE_ARN')
            # }
        )

        job_id = response['JobId']
        logger.info(f"Textract job started: {job_id}")

        return job_id

    except Exception as e:
        logger.error(f"Failed to start Textract job: {str(e)}", exc_info=True)
        raise


@tracer.capture_method
def wait_for_textract_completion(job_id: str) -> Dict[str, Any]:
    """
    Poll Textract job until completion.

    Args:
        job_id: Textract job ID

    Returns:
        Complete Textract response

    Raises:
        TimeoutError: If job doesn't complete within MAX_WAIT_TIME
        RuntimeError: If job fails
    """
    start_time = time.time()

    while True:
        elapsed = time.time() - start_time

        if elapsed > MAX_WAIT_TIME:
            raise TimeoutError(f"Textract job {job_id} exceeded max wait time ({MAX_WAIT_TIME}s)")

        response = textract.get_document_analysis(JobId=job_id)
        status = response['JobStatus']

        logger.info(f"Textract job {job_id} status: {status} (elapsed: {elapsed:.1f}s)")

        if status == 'SUCCEEDED':
            # Get all pages if pagination is needed
            all_blocks = response.get('Blocks', [])
            next_token = response.get('NextToken')

            while next_token:
                logger.info(f"Fetching next page of results for job {job_id}")
                response = textract.get_document_analysis(
                    JobId=job_id,
                    NextToken=next_token
                )
                all_blocks.extend(response.get('Blocks', []))
                next_token = response.get('NextToken')

            response['Blocks'] = all_blocks
            logger.info(f"Textract job {job_id} completed successfully ({len(all_blocks)} blocks)")

            return response

        elif status == 'FAILED':
            error_msg = response.get('StatusMessage', 'Unknown error')
            raise RuntimeError(f"Textract job {job_id} failed: {error_msg}")

        elif status == 'PARTIAL_SUCCESS':
            logger.warning(f"Textract job {job_id} completed with partial success")
            return response

        # Job still in progress
        time.sleep(POLL_INTERVAL)


@tracer.capture_method
def extract_query_answers(textract_response: Dict[str, Any]) -> Dict[str, str]:
    """
    Extract answers from Textract Query results.

    Args:
        textract_response: Complete Textract response

    Returns:
        Dictionary mapping query aliases to answers
    """
    query_answers = {}

    blocks = textract_response.get('Blocks', [])

    # Build relationship map
    block_map = {block['Id']: block for block in blocks}

    # Find QUERY_RESULT blocks
    for block in blocks:
        if block['BlockType'] == 'QUERY_RESULT':
            query_alias = block.get('Query', {}).get('Alias', '')

            # Get the answer text
            answer = block.get('Text', '')
            confidence = block.get('Confidence', 0.0)

            if answer and confidence > 50:  # Only include if confidence > 50%
                query_answers[query_alias] = {
                    'text': answer,
                    'confidence': confidence / 100.0  # Normalize to 0-1
                }

                logger.info(f"Query '{query_alias}': {answer[:100]}... (confidence: {confidence:.1f}%)")

    return query_answers


@tracer.capture_method
def extract_tables(textract_response: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract table data from Textract response.

    Args:
        textract_response: Complete Textract response

    Returns:
        List of extracted tables with metadata
    """
    tables = []
    blocks = textract_response.get('Blocks', [])

    # Build block map
    block_map = {block['Id']: block for block in blocks}

    # Find TABLE blocks
    for block in blocks:
        if block['BlockType'] == 'TABLE':
            table_data = extract_table_structure(block, block_map)

            # Calculate table confidence
            confidence = block.get('Confidence', 0.0) / 100.0

            # Check if this looks like an eligibility table
            is_eligibility = is_eligibility_table(table_data)

            tables.append({
                'table_id': block['Id'],
                'rows': table_data['rows'],
                'headers': table_data['headers'],
                'confidence': confidence,
                'is_eligibility': is_eligibility,
                'row_count': len(table_data['rows']),
                'column_count': table_data['column_count']
            })

    logger.info(f"Extracted {len(tables)} tables, {sum(1 for t in tables if t['is_eligibility'])} eligibility tables")

    return tables


def extract_table_structure(table_block: Dict, block_map: Dict) -> Dict[str, Any]:
    """
    Extract structured data from a TABLE block.

    Args:
        table_block: TABLE block from Textract
        block_map: Mapping of block IDs to blocks

    Returns:
        Structured table data
    """
    rows = []
    headers = []
    column_count = 0

    # Get relationships
    relationships = table_block.get('Relationships', [])

    for relationship in relationships:
        if relationship['Type'] == 'CHILD':
            cell_ids = relationship['Ids']

            # Build cell grid
            cells = {}
            for cell_id in cell_ids:
                cell = block_map.get(cell_id, {})
                if cell.get('BlockType') == 'CELL':
                    row_index = cell.get('RowIndex', 0)
                    col_index = cell.get('ColumnIndex', 0)

                    # Extract cell text
                    cell_text = extract_cell_text(cell, block_map)

                    if row_index not in cells:
                        cells[row_index] = {}
                    cells[row_index][col_index] = cell_text

                    column_count = max(column_count, col_index)

            # Convert to row arrays
            for row_index in sorted(cells.keys()):
                row_data = []
                for col_index in range(1, column_count + 1):
                    row_data.append(cells[row_index].get(col_index, ''))

                if row_index == 1:
                    headers = row_data
                else:
                    rows.append(row_data)

    return {
        'headers': headers,
        'rows': rows,
        'column_count': column_count
    }


def extract_cell_text(cell: Dict, block_map: Dict) -> str:
    """
    Extract text from a CELL block.

    Args:
        cell: CELL block
        block_map: Mapping of block IDs to blocks

    Returns:
        Concatenated cell text
    """
    text_parts = []

    relationships = cell.get('Relationships', [])
    for relationship in relationships:
        if relationship['Type'] == 'CHILD':
            for word_id in relationship['Ids']:
                word = block_map.get(word_id, {})
                if word.get('BlockType') == 'WORD':
                    text_parts.append(word.get('Text', ''))

    return ' '.join(text_parts)


def is_eligibility_table(table_data: Dict) -> bool:
    """
    Heuristic to detect if a table contains eligibility criteria.

    Enhanced detection:
    1. Check headers for eligibility keywords
    2. Check cell content for medical/clinical terms
    3. Analyze table structure (columns, row count)

    Args:
        table_data: Structured table data

    Returns:
        True if likely an eligibility table
    """
    headers = table_data.get('headers', [])
    rows = table_data.get('rows', [])
    header_text = ' '.join(headers).lower()

    # Strategy 1: Check headers for eligibility keywords
    eligibility_keywords = [
        'inclusion', 'exclusion', 'eligible', 'ineligible',
        'entry criteria', 'enrollment', 'participation criteria',
        'selection criteria', 'patient criteria', 'subject criteria'
    ]

    if any(keyword in header_text for keyword in eligibility_keywords):
        return True

    # Strategy 2: Check table content for medical/clinical terms
    # Combine all cell text
    all_text = header_text + ' '
    for row in rows:
        all_text += ' '.join(row).lower() + ' '

    # Medical/clinical indicators
    medical_keywords = [
        'age', 'years', 'diagnosis', 'disease', 'condition',
        'medication', 'treatment', 'therapy', 'drug',
        'pregnant', 'breastfeeding', 'laboratory', 'test',
        'hba1c', 'glucose', 'cholesterol', 'creatinine',
        'ecog', 'performance status', 'bmi', 'weight',
        'blood pressure', 'liver', 'kidney', 'cardiac',
        'cancer', 'diabetes', 'hypertension', 'malignancy'
    ]

    # Count medical terms in table
    medical_term_count = sum(1 for keyword in medical_keywords if keyword in all_text)

    # Strategy 3: Table structure heuristics
    row_count = len(rows)
    column_count = table_data.get('column_count', 0)

    # Eligibility tables typically have:
    # - Multiple rows (3-50 criteria items)
    # - 1-3 columns (criteria, description, category)
    # - Medical terminology

    if medical_term_count >= 3 and row_count >= 3 and row_count <= 50:
        if column_count <= 3:
            logger.info(f"Table detected as eligibility based on content: {medical_term_count} medical terms, {row_count} rows")
            return True

    # Strategy 4: Look for numbered lists or bullet points in cells
    criteria_patterns = ['•', '-', '–', '1.', '2.', '3.']
    has_list_markers = any(pattern in all_text for pattern in criteria_patterns)

    if has_list_markers and medical_term_count >= 2:
        logger.info(f"Table detected as eligibility based on list structure")
        return True

    return False


@tracer.capture_method
def extract_criteria_by_pattern(textract_response: Dict) -> Dict[str, Any]:
    """
    Fallback pattern-based criteria extraction from raw text blocks.

    Used when query-based extraction returns no results.
    Searches for sections with headings like "Inclusion Criteria", "Exclusion Criteria",
    including numbered sections like "3.1 Inclusion criteria".

    Args:
        textract_response: Complete Textract response

    Returns:
        Dictionary with inclusion/exclusion criteria text
    """
    blocks = textract_response.get('Blocks', [])

    # Build sequential text with line breaks
    text_lines = []
    for block in blocks:
        if block['BlockType'] == 'LINE':
            text = block.get('Text', '')
            if text:
                text_lines.append(text)

    full_text = '\n'.join(text_lines)
    logger.info(f"Pattern extraction: analyzing {len(text_lines)} lines of text")

    # Pattern matching for criteria sections
    import re

    # COMPREHENSIVE patterns to handle ALL ClinicalTrials.gov protocol formats
    # Covers: numbered sections, standard headings, case variations, multi-level numbering,
    # alternative terminology, subsections, and page-spanning content

    inclusion_patterns = [
        # === NUMBERED SECTION FORMATS ===
        # "3.1 Inclusion criteria" or "3.1 Inclusion Criteria" with bulleted content
        # Fixed: Use [ \t:-]* instead of [:\s-]* to avoid matching newlines
        r'(?i)(?:^|\n)(\d+\.?\d*)\s+inclusion\s+criteria[ \t:-]*\n(.*?)(?=\n\d+\.\d+\s+[A-Za-z]|\Z)',

        # Multi-level numbering: "4.2.1 Inclusion Criteria"
        r'(?i)(?:^|\n)(\d+\.\d+\.\d+)\s+inclusion\s+criteria[ \t:-]*\n(.*?)(?=\n\d+\.\d+\.\d+\s+[A-Za-z]|\Z)',

        # "Section 3.1 Inclusion Criteria"
        r'(?i)(?:^|\n)section\s+(\d+\.?\d*)\s+inclusion\s+criteria[ \t:-]*\n(.*?)(?=\nsection\s+\d+\.?\d*|\Z)',

        # === STANDARD FORMATS ===
        # "Inclusion Criteria:" followed by content until exclusion or next major section
        r'(?i)(?:^|\n)inclusion\s+criteria[ \t:-]*\n(.*?)(?=exclusion\s+criteria|\n\d+\.\s+[A-Z][a-z]+\s+[A-Z]|\Z)',

        # "INCLUSION CRITERIA" (all caps)
        r'(?:^|\n)INCLUSION\s+CRITERIA[ \t:-]*\n(.*?)(?=EXCLUSION\s+CRITERIA|\n\d+\.\s+[A-Z]|\Z)',

        # "Inclusion Criteria -" or "Inclusion Criteria–" (with dash)
        r'(?i)(?:^|\n)inclusion\s+criteria\s*[–-][ \t]*\n(.*?)(?=exclusion\s+criteria|\n\d+\.\s+[A-Z]|\Z)',

        # === ALTERNATIVE TERMINOLOGY ===
        # "Key Inclusion Criteria"
        r'(?i)(?:^|\n)key\s+inclusion\s+criteria[ \t:-]*\n(.*?)(?=key\s+exclusion\s+criteria|exclusion\s+criteria|\Z)',

        # "Main Inclusion Criteria"
        r'(?i)(?:^|\n)main\s+inclusion\s+criteria[ \t:-]*\n(.*?)(?=main\s+exclusion\s+criteria|exclusion\s+criteria|\Z)',

        # "Entry Criteria - Inclusion"
        r'(?i)(?:^|\n)entry\s+criteria[ \t:-]*\n.*?inclusion[ \t:-]*\n(.*?)(?=exclusion|\Z)',

        # === PARTICIPANT/PATIENT/SUBJECT VARIATIONS ===
        # "Patient Inclusion Criteria"
        r'(?i)(?:^|\n)(?:patient|subject|participant)\s+inclusion\s+criteria[ \t:-]*\n(.*?)(?=(?:patient|subject|participant)\s+exclusion\s+criteria|exclusion\s+criteria|\Z)',

        # === ELIGIBILITY PARENT SECTIONS ===
        # "Eligibility Criteria" with "Inclusion" subsection
        r'(?i)eligibility\s+criteria[ \t:-]*\n.*?(?:\d+\.?\d*\s+)?inclusion[ \t:-]*\n(.*?)(?=(?:\d+\.?\d*\s+)?exclusion|\Z)',

        # "Subject Selection" with "Inclusion" subsection
        r'(?i)subject\s+selection[ \t:-]*\n.*?(?:\d+\.?\d*\s+)?inclusion[ \t:-]*\n(.*?)(?=(?:\d+\.?\d*\s+)?exclusion|\Z)',

        # "Patient Selection" with "Inclusion" subsection
        r'(?i)patient\s+selection[ \t:-]*\n.*?(?:\d+\.?\d*\s+)?inclusion[ \t:-]*\n(.*?)(?=(?:\d+\.?\d*\s+)?exclusion|\Z)',

        # "Enrollment Criteria" with "Inclusion" subsection
        r'(?i)enrollment\s+criteria[ \t:-]*\n.*?(?:\d+\.?\d*\s+)?inclusion[ \t:-]*\n(.*?)(?=(?:\d+\.?\d*\s+)?exclusion|\Z)',

        # === VARIATIONS WITH "WHO CAN" ===
        # "Who Can Participate" or "Who Can Enroll"
        r'(?i)(?:^|\n)who\s+can\s+(?:participate|enroll|join)[ \t:-]*\n(.*?)(?=who\s+cannot|exclusion\s+criteria|\Z)',

        # === SUBSECTION VARIATIONS ===
        # "3.1.1 Inclusion Criteria"
        r'(?i)(?:^|\n)(\d+\.\d+\.\d+)\s+inclusion[ \t:-]*\n(.*?)(?=\n\d+\.\d+\.\d+|\Z)',
    ]

    exclusion_patterns = [
        # === NUMBERED SECTION FORMATS ===
        # "3.2 Exclusion criteria" or "3.2 Exclusion Criteria"
        # Fixed: Use [ \t:-]* instead of [:\s-]* to avoid matching newlines
        r'(?i)(?:^|\n)(\d+\.?\d*)\s+exclusion\s+criteria[ \t:-]*\n(.*?)(?=\n\d+\.\d+\s+[A-Za-z]|Disposition|Sample\s+size|\Z)',

        # Multi-level numbering: "4.2.2 Exclusion Criteria"
        r'(?i)(?:^|\n)(\d+\.\d+\.\d+)\s+exclusion\s+criteria[ \t:-]*\n(.*?)(?=\n\d+\.\d+\.\d+\s+[A-Za-z]|\Z)',

        # "Section 3.2 Exclusion Criteria"
        r'(?i)(?:^|\n)section\s+(\d+\.?\d*)\s+exclusion\s+criteria[ \t:-]*\n(.*?)(?=\nsection\s+\d+\.?\d*|\Z)',

        # === STANDARD FORMATS ===
        # "Exclusion Criteria:" followed by content
        r'(?i)(?:^|\n)exclusion\s+criteria[ \t:-]*\n(.*?)(?=\n\d+\.\s+[A-Z][a-z]+\s+[A-Z]|Study\s+procedures|Disposition|\Z)',

        # "EXCLUSION CRITERIA" (all caps)
        r'(?:^|\n)EXCLUSION\s+CRITERIA[ \t:-]*\n(.*?)(?=\n\d+\.\s+[A-Z]|STUDY\s+PROCEDURES|\Z)',

        # "Exclusion Criteria -" or "Exclusion Criteria–" (with dash)
        r'(?i)(?:^|\n)exclusion\s+criteria\s*[–-][ \t]*\n(.*?)(?=\n\d+\.\s+[A-Z]|Study\s+procedures|\Z)',

        # === ALTERNATIVE TERMINOLOGY ===
        # "Key Exclusion Criteria"
        r'(?i)(?:^|\n)key\s+exclusion\s+criteria[ \t:-]*\n(.*?)(?=\n\d+\.\s+[A-Z]|\Z)',

        # "Main Exclusion Criteria"
        r'(?i)(?:^|\n)main\s+exclusion\s+criteria[ \t:-]*\n(.*?)(?=\n\d+\.\s+[A-Z]|\Z)',

        # "Entry Criteria - Exclusion"
        r'(?i)(?:^|\n)entry\s+criteria[ \t:-]*\n.*?exclusion[ \t:-]*\n(.*?)(?=\n\d+\.\s+[A-Z]|\Z)',

        # === PARTICIPANT/PATIENT/SUBJECT VARIATIONS ===
        # "Patient Exclusion Criteria"
        r'(?i)(?:^|\n)(?:patient|subject|participant)\s+exclusion\s+criteria[ \t:-]*\n(.*?)(?=\n\d+\.\s+[A-Z]|\Z)',

        # === ELIGIBILITY PARENT SECTIONS ===
        # "Eligibility Criteria" with "Exclusion" subsection
        r'(?i)eligibility\s+criteria[ \t:-]*\n.*?(?:\d+\.?\d*\s+)?exclusion[ \t:-]*\n(.*?)(?=\n\d+\.?\d*\s+[A-Z]|\Z)',

        # "Subject Selection" with "Exclusion" subsection
        r'(?i)subject\s+selection[ \t:-]*\n.*?(?:\d+\.?\d*\s+)?exclusion[ \t:-]*\n(.*?)(?=\n\d+\.?\d*\s+[A-Z]|\Z)',

        # "Patient Selection" with "Exclusion" subsection
        r'(?i)patient\s+selection[ \t:-]*\n.*?(?:\d+\.?\d*\s+)?exclusion[ \t:-]*\n(.*?)(?=\n\d+\.?\d*\s+[A-Z]|\Z)',

        # "Enrollment Criteria" with "Exclusion" subsection
        r'(?i)enrollment\s+criteria[ \t:-]*\n.*?(?:\d+\.?\d*\s+)?exclusion[ \t:-]*\n(.*?)(?=\n\d+\.?\d*\s+[A-Z]|\Z)',

        # === VARIATIONS WITH "WHO CANNOT" ===
        # "Who Cannot Participate" or "Who Cannot Enroll"
        r'(?i)(?:^|\n)who\s+cannot\s+(?:participate|enroll|join)[ \t:-]*\n(.*?)(?=\n\d+\.\s+[A-Z]|\Z)',

        # === SUBSECTION VARIATIONS ===
        # "3.2.1 Exclusion Criteria"
        r'(?i)(?:^|\n)(\d+\.\d+\.\d+)\s+exclusion[ \t:-]*\n(.*?)(?=\n\d+\.\d+\.\d+|\Z)',

        # === INELIGIBILITY VARIATIONS ===
        # "Ineligibility Criteria"
        r'(?i)(?:^|\n)ineligibility\s+criteria[ \t:-]*\n(.*?)(?=\n\d+\.\s+[A-Z]|\Z)',
    ]

    inclusion_text = None
    exclusion_text = None
    inclusion_pattern_matched = None
    exclusion_pattern_matched = None

    # Try inclusion patterns - find ALL matches and pick the longest one
    # (to handle cases where headings appear multiple times, e.g., in TOC and actual section)
    for i, pattern in enumerate(inclusion_patterns):
        # Find ALL matches for this pattern
        matches = list(re.finditer(pattern, full_text, re.DOTALL | re.MULTILINE))

        if matches:
            # Try each match and pick the one with longest content
            best_text = None
            best_match_info = None

            for match in matches:
                # Handle patterns with and without numbered capture groups
                if len(match.groups()) > 1:
                    text = match.group(2).strip()  # Content is in second group
                else:
                    text = match.group(1).strip()  # Content is in first group

                # Keep the longest match
                if text and (best_text is None or len(text) > len(best_text)):
                    best_text = text
                    best_match_info = (i + 1, match)

            # Use the best match if it's meaningful
            if best_text and len(best_text) > 20:
                inclusion_text = best_text
                inclusion_pattern_matched = best_match_info[0]
                logger.info(f"✓ Inclusion criteria found using pattern #{inclusion_pattern_matched} ({len(inclusion_text)} chars, {len(matches)} total matches)")
                logger.info(f"Preview: {inclusion_text[:200]}...")
                break

    # Try exclusion patterns - find ALL matches and pick the longest one
    # (to handle cases where headings appear multiple times, e.g., in TOC and actual section)
    for i, pattern in enumerate(exclusion_patterns):
        # Find ALL matches for this pattern
        matches = list(re.finditer(pattern, full_text, re.DOTALL | re.MULTILINE))

        if matches:
            # Try each match and pick the one with longest content
            best_text = None
            best_match_info = None

            for match in matches:
                # Handle patterns with and without numbered capture groups
                if len(match.groups()) > 1:
                    text = match.group(2).strip()
                else:
                    text = match.group(1).strip()

                # Keep the longest match
                if text and (best_text is None or len(text) > len(best_text)):
                    best_text = text
                    best_match_info = (i + 1, match)

            # Use the best match if it's meaningful
            if best_text and len(best_text) > 20:
                exclusion_text = best_text
                exclusion_pattern_matched = best_match_info[0]
                logger.info(f"✓ Exclusion criteria found using pattern #{exclusion_pattern_matched} ({len(exclusion_text)} chars, {len(matches)} total matches)")
                logger.info(f"Preview: {exclusion_text[:200]}...")
                break

    # === FALLBACK: Page-level content extraction ===
    # If patterns didn't find criteria, look for headings and extract surrounding content
    if not inclusion_text or not exclusion_text:
        logger.info("Attempting fallback: page-level content extraction around criteria headings")

        # Find lines that contain inclusion/exclusion headings
        inclusion_heading_indices = []
        exclusion_heading_indices = []

        for i, line in enumerate(text_lines):
            line_lower = line.lower()
            # Look for inclusion heading indicators
            if not inclusion_text and ('inclusion' in line_lower and
                ('criteria' in line_lower or 'criterion' in line_lower)):
                inclusion_heading_indices.append(i)
                logger.info(f"Found potential inclusion heading at line {i}: {line[:100]}")

            # Look for exclusion heading indicators
            if not exclusion_text and ('exclusion' in line_lower and
                ('criteria' in line_lower or 'criterion' in line_lower)):
                exclusion_heading_indices.append(i)
                logger.info(f"Found potential exclusion heading at line {i}: {line[:100]}")

        # Extract content around inclusion heading
        if not inclusion_text and inclusion_heading_indices:
            start_idx = inclusion_heading_indices[0]
            # Capture up to 100 lines after the heading (roughly 2-3 pages)
            end_idx = min(start_idx + 100, len(text_lines))

            # Try to find natural endpoint (exclusion heading or major section)
            for i in range(start_idx + 1, end_idx):
                line_lower = text_lines[i].lower()
                if ('exclusion' in line_lower and 'criteria' in line_lower) or \
                   re.match(r'^\d+\.\d+\s+[A-Z]', text_lines[i]):
                    end_idx = i
                    break

            inclusion_text = '\n'.join(text_lines[start_idx:end_idx]).strip()
            logger.info(f"✓ Fallback captured inclusion criteria ({len(inclusion_text)} chars, lines {start_idx}-{end_idx})")

        # Extract content around exclusion heading
        if not exclusion_text and exclusion_heading_indices:
            start_idx = exclusion_heading_indices[0]
            # Capture up to 100 lines after the heading
            end_idx = min(start_idx + 100, len(text_lines))

            # Try to find natural endpoint (next major section)
            for i in range(start_idx + 1, end_idx):
                if re.match(r'^\d+\.\d+\s+[A-Z]', text_lines[i]):
                    end_idx = i
                    break

            exclusion_text = '\n'.join(text_lines[start_idx:end_idx]).strip()
            logger.info(f"✓ Fallback captured exclusion criteria ({len(exclusion_text)} chars, lines {start_idx}-{end_idx})")

    # Clean extracted text
    def clean_criteria_text(text: str) -> str:
        """
        Clean extracted criteria text by removing excessive whitespace,
        normalizing bullet points, and formatting for readability.
        """
        if not text:
            return text

        # Split into lines
        lines = text.split('\n')
        cleaned_lines = []

        for line in lines:
            # Strip leading/trailing whitespace
            line = line.strip()

            # Skip empty lines and single-character lines (often just "-")
            if not line or len(line) <= 1:
                continue

            # Skip page headers/footers (UNIVERSITA', BiCRO, etc.)
            if any(keyword in line.upper() for keyword in ['UNIVERSITA', 'BICRO', 'STUDY PROTOCOL', 'REV 2.0']):
                continue

            # Normalize bullet points
            # Replace various dash types with standard hyphen
            line = re.sub(r'^[–—-]\s*', '- ', line)

            # Remove standalone dashes that are just separators
            if line.strip() in ['-', '–', '—', '•']:
                continue

            cleaned_lines.append(line)

        # Join lines and normalize whitespace
        cleaned_text = '\n'.join(cleaned_lines)

        # Remove excessive blank lines (more than 2 consecutive)
        cleaned_text = re.sub(r'\n{3,}', '\n\n', cleaned_text)

        return cleaned_text.strip()

    # Apply cleaning
    if inclusion_text:
        inclusion_text = clean_criteria_text(inclusion_text)

    if exclusion_text:
        exclusion_text = clean_criteria_text(exclusion_text)

    result = {}

    if inclusion_text:
        # Determine confidence based on extraction method
        confidence = 0.80 if inclusion_pattern_matched and inclusion_pattern_matched <= 5 else 0.70
        result['INCLUSION_CRITERIA_PATTERN'] = {
            'text': inclusion_text,
            'confidence': confidence,
            'extraction_method': f'pattern_{inclusion_pattern_matched}' if inclusion_pattern_matched else 'fallback'
        }

    if exclusion_text:
        # Determine confidence based on extraction method
        confidence = 0.80 if exclusion_pattern_matched and exclusion_pattern_matched <= 5 else 0.70
        result['EXCLUSION_CRITERIA_PATTERN'] = {
            'text': exclusion_text,
            'confidence': confidence,
            'extraction_method': f'pattern_{exclusion_pattern_matched}' if exclusion_pattern_matched else 'fallback'
        }

    if result:
        logger.info(f"✓ Pattern extraction successful: {len(result)} sections found")
    else:
        logger.warning("⚠ Pattern extraction found no criteria sections")

    return result


@tracer.capture_method
def calculate_overall_confidence(textract_response: Dict, query_answers: Dict, tables: List[Dict]) -> float:
    """
    Calculate overall confidence score for the extraction.

    Args:
        textract_response: Complete Textract response
        query_answers: Extracted query answers
        tables: Extracted tables

    Returns:
        Confidence score (0-1)
    """
    scores = []

    # Query confidence
    if query_answers:
        query_confidences = [qa['confidence'] for qa in query_answers.values()]
        scores.append(sum(query_confidences) / len(query_confidences))

    # Table confidence
    if tables:
        table_confidences = [t['confidence'] for t in tables]
        scores.append(sum(table_confidences) / len(table_confidences))

    # Overall document metadata
    metadata = textract_response.get('DocumentMetadata', {})
    pages = metadata.get('Pages', 0)

    # More pages generally means lower per-page confidence for large docs
    if pages > 100:
        scores.append(0.9)  # Slightly lower for very large docs
    elif pages > 50:
        scores.append(0.95)
    else:
        scores.append(1.0)

    return sum(scores) / len(scores) if scores else 0.5


@logger.inject_lambda_context(log_event=True)
@tracer.capture_lambda_handler
def lambda_handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    Lambda handler for Textract document processing.

    Expected event format:
    {
        "s3_bucket": "my-protocols-bucket",
        "s3_key": "NCT12345678.pdf",
        "trial_id": "NCT12345678"  // Optional
    }

    Returns:
    {
        "statusCode": 200,
        "body": {
            "trial_id": "NCT12345678",
            "query_answers": {...},
            "tables": [...],
            "confidence": 0.89,
            "pages": 156,
            "extraction_time_seconds": 45.2
        }
    }
    """
    start_time = time.time()

    try:
        # Parse event - handle both direct invocation and S3 event trigger
        s3_bucket = None
        s3_key = None
        trial_id = None

        # Check if this is an S3 event
        if 'Records' in event and event['Records']:
            # S3 event format
            record = event['Records'][0]
            s3_bucket = record['s3']['bucket']['name']
            s3_key = record['s3']['object']['key']
            # Extract trial_id from folder structure: protocols/TRIAL-XXXXX/filename.pdf
            # Split by '/' and get the second-to-last element (folder name)
            s3_key_parts = s3_key.split('/')
            if len(s3_key_parts) >= 2:
                trial_id = s3_key_parts[-2]  # Get the folder name (TRIAL-XXXXX)
            else:
                trial_id = s3_key.replace('.pdf', '').split('/')[-1]  # Fallback to filename
            logger.info(f"Triggered by S3 event: s3://{s3_bucket}/{s3_key}")
        else:
            # Direct invocation format
            s3_bucket = event.get('s3_bucket')
            s3_key = event.get('s3_key')
            trial_id = event.get('trial_id')

        if not s3_bucket or not s3_key:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Missing required fields: s3_bucket, s3_key'
                })
            }

        # Extract trial_id from filename if not provided
        if not trial_id:
            trial_id = s3_key.replace('.pdf', '').split('/')[-1]

        logger.info(f"Processing protocol document: trial_id={trial_id}, s3://{s3_bucket}/{s3_key}")

        # Step 1: Start Textract job
        job_id = start_textract_job(s3_bucket, s3_key)

        # Step 2: Wait for completion
        textract_response = wait_for_textract_completion(job_id)

        # Step 3: Extract query answers
        query_answers = extract_query_answers(textract_response)

        # Step 3.5: Pattern-based fallback (if no criteria found in queries)
        # Check if we have actual inclusion/exclusion criteria in query answers
        criteria_aliases = [
            # Inclusion criteria aliases
            'INCLUSION_CRITERIA', 'INCLUSION_CRITERIA_LIST', 'INCLUSION_REQUIREMENTS',
            # Exclusion criteria aliases
            'EXCLUSION_CRITERIA', 'EXCLUSION_CRITERIA_LIST', 'EXCLUSION_FACTORS',
            # Combined/alternative aliases
            'ELIGIBILITY_CRITERIA', 'SELECTION_CRITERIA', 'ENROLLMENT_CRITERIA'
        ]

        has_criteria = any(alias in query_answers for alias in criteria_aliases)

        if not has_criteria:
            logger.info("No criteria found in query answers, attempting pattern-based extraction")
            pattern_results = extract_criteria_by_pattern(textract_response)
            if pattern_results:
                query_answers.update(pattern_results)
                logger.info(f"✓ Pattern extraction added {len(pattern_results)} results")
        else:
            logger.info(f"✓ Criteria found in query answers: {[alias for alias in criteria_aliases if alias in query_answers]}")

        # Step 4: Extract tables
        tables = extract_tables(textract_response)

        # Step 5: Calculate confidence
        confidence = calculate_overall_confidence(textract_response, query_answers, tables)

        # Extract metadata
        metadata = textract_response.get('DocumentMetadata', {})
        pages = metadata.get('Pages', 0)

        extraction_time = time.time() - start_time

        # Prepare response
        result = {
            'trial_id': trial_id,
            's3_location': f"s3://{s3_bucket}/{s3_key}",
            'textract_job_id': job_id,
            'query_answers': query_answers,
            'tables': tables,
            'confidence': confidence,
            'pages': pages,
            'extraction_time_seconds': round(extraction_time, 2),
            'status': 'success'
        }

        logger.info(f"Textract processing completed for {trial_id}: {pages} pages, confidence={confidence:.2f}, time={extraction_time:.1f}s")

        # Step 6: Automatically trigger Protocol Orchestrator (if enabled)
        if AUTO_TRIGGER_ORCHESTRATOR:
            try:
                logger.info(f"Triggering Protocol Orchestrator for trial {trial_id}")

                orchestrator_event = {
                    'trial_id': trial_id,
                    'textract_output': {
                        'query_answers': query_answers,
                        'tables': tables,
                        'confidence': confidence,
                        'pages': pages
                    },
                    's3_bucket': s3_bucket,
                    's3_key': s3_key
                }

                orchestrator_response = lambda_client.invoke(
                    FunctionName=PROTOCOL_ORCHESTRATOR_FUNCTION,
                    InvocationType='Event',  # Async invocation
                    Payload=json.dumps(orchestrator_event)
                )

                logger.info(f"Protocol Orchestrator triggered successfully (StatusCode: {orchestrator_response['StatusCode']})")
                result['orchestrator_triggered'] = True

            except Exception as e:
                logger.error(f"Failed to trigger Protocol Orchestrator: {str(e)}", exc_info=True)
                result['orchestrator_triggered'] = False
                result['orchestrator_error'] = str(e)
        else:
            logger.info("Auto-trigger disabled, skipping Protocol Orchestrator invocation")
            result['orchestrator_triggered'] = False

        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json'
            },
            'body': json.dumps(result)
        }

    except TimeoutError as e:
        logger.error(f"Textract processing timeout: {str(e)}")
        return {
            'statusCode': 504,
            'body': json.dumps({
                'error': 'Textract processing timeout',
                'message': str(e)
            })
        }

    except Exception as e:
        logger.error(f"Error in Textract processing: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Textract processing failed',
                'message': str(e)
            })
        }
