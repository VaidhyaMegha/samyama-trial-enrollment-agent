# Protocol Processing Guide

## Overview

A comprehensive end-to-end system for processing clinical trial protocol PDFs through AWS Textract and Amazon Comprehend Medical to extract and classify eligibility criteria.

## Quick Start

### Process Any Protocol PDF in One Command

```bash
python scripts/process_protocol_pdf.py /path/to/protocol.pdf
```

That's it! The script will:
1. Upload the PDF to S3
2. Extract text and criteria using AWS Textract
3. Classify criteria using Amazon Comprehend Medical
4. Save outputs to `tmp/` directory
5. Display formatted criteria in the console

### Usage Examples

```bash
# Basic usage
python scripts/process_protocol_pdf.py ~/Downloads/trial_protocol.pdf

# With custom trial ID
python scripts/process_protocol_pdf.py protocol-docs/26_page.pdf --trial-id NCT12345678

# From any location
python scripts/process_protocol_pdf.py /path/to/any/protocol.pdf

# Get help
python scripts/process_protocol_pdf.py --help
```

## System Architecture

```
┌─────────────────────┐
│  Protocol PDF       │  ← Input: Any clinical trial protocol
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  1. S3 Upload       │  ← Automatic upload to S3 bucket
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  2. Textract        │  ← AWS Textract Document Analysis
│     Processor       │    - Pattern-based extraction
│     Lambda          │    - Query-based extraction
└─────────┬───────────┘    - Table detection
          │
          ▼
┌─────────────────────┐
│  3. Section         │  ← Amazon Comprehend Medical
│     Classifier      │    - Medical entity detection
│     Lambda          │    - Criteria classification
└─────────┬───────────┘    - Entity density analysis
          │
          ▼
┌─────────────────────┐
│  4. Save Outputs    │  ← tmp/textract_*.json
│                     │    tmp/classifier_*.json
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  5. Console Output  │  ← Formatted criteria display
│     & Next Steps    │    Ready for parse-criteria API
└─────────────────────┘
```

## Components

### 1. Textract Processor Lambda

**Location**: `src/lambda/textract_processor/`

**Purpose**: Extracts text, tables, and criteria from protocol PDFs using AWS Textract.

**Key Features**:
- Asynchronous document analysis for large PDFs (supports up to 124+ pages)
- Multiple extraction strategies:
  - **Pattern-based extraction**: Uses regex patterns to find inclusion/exclusion criteria sections
  - **Query-based extraction**: Asks Textract specific questions about criteria
  - **Table extraction**: Detects and extracts eligibility tables
- Confidence scoring for extraction quality
- Automatic retry logic with exponential backoff
- 10-minute timeout for processing large documents

**Configuration**:
```python
Environment Variables:
- TEXTRACT_MAX_WAIT_TIME: 300 seconds (5 minutes)
- TEXTRACT_POLL_INTERVAL: 5 seconds
- PROTOCOL_ORCHESTRATOR_FUNCTION: Name of orchestrator Lambda
- AUTO_TRIGGER_ORCHESTRATOR: "true"
```

**Extraction Patterns**:
1. **Pattern 1** (Primary): `Inclusion Criteria:` / `Exclusion Criteria:`
2. **Pattern 2** (Alternative): `Eligibility Criteria` with subsections
3. **Pattern 3** (Numbered): `1. Inclusion Criteria` / `2. Exclusion Criteria`

**Output Format**:
```json
{
  "trial_id": "TEST_TRIAL",
  "s3_location": "s3://bucket/key",
  "textract_job_id": "...",
  "query_answers": {
    "INCLUSION_CRITERIA_PATTERN": {
      "text": "Age >= 18 years; Diagnosis of T2DM...",
      "confidence": 0.8,
      "extraction_method": "pattern_1"
    },
    "EXCLUSION_CRITERIA_PATTERN": {
      "text": "Pregnancy; Active malignancy...",
      "confidence": 0.8,
      "extraction_method": "pattern_1"
    }
  },
  "tables": [...],
  "confidence": 0.88,
  "pages": 26,
  "extraction_time_seconds": 22.5,
  "status": "success"
}
```

### 2. Section Classifier Lambda

**Location**: `src/lambda/section_classifier/`

**Purpose**: Classifies and enriches extracted criteria using Amazon Comprehend Medical.

**Key Features**:
- Medical entity detection (conditions, medications, procedures, etc.)
- Medical entity density calculation (entities per 100 words)
- Criteria validation and cleaning
- Supports both query-based and table-based extraction
- Generates formatted text ready for parse-criteria API

**Configuration**:
```python
Environment Variables:
- MIN_CRITERION_LENGTH: 10 characters
- MAX_CRITERION_LENGTH: 500 characters
- USE_COMPREHEND_MEDICAL: "true"
```

**Extraction Methods**:
- **Queries**: Extracts from Textract query answers
  - Supports aliases: `INCLUSION_CRITERIA`, `INCLUSION_CRITERIA_PATTERN`, etc.
- **Tables**: Extracts from eligibility tables
  - Identifies tables with "inclusion" or "exclusion" keywords

**Output Format**:
```json
{
  "trial_id": "TEST_TRIAL",
  "inclusion_criteria": [
    "Age >= 18 years",
    "Diagnosis of T2DM"
  ],
  "exclusion_criteria": [
    "Pregnancy",
    "Active malignancy"
  ],
  "formatted_text": "Inclusion Criteria:\n- Age >= 18 years\n- Diagnosis of T2DM\n\nExclusion Criteria:\n- Pregnancy\n- Active malignancy",
  "metadata": {
    "total_criteria": 4,
    "inclusion_count": 2,
    "exclusion_count": 2,
    "textract_confidence": 0.88,
    "extraction_confidence": 1.0,
    "overall_confidence": 0.94,
    "extraction_methods": {
      "queries": true,
      "tables": false
    },
    "medical_entity_density": 15.22
  },
  "status": "success"
}
```

### 3. Process Protocol PDF Script

**Location**: `scripts/process_protocol_pdf.py`

**Purpose**: Command-line tool for end-to-end protocol processing.

**Key Features**:
- Single command operation
- Extended timeouts for large PDFs (10-minute read timeout)
- Comprehensive error handling
- Real-time progress reporting
- Automatic file naming with timestamps
- Works with any PDF path (absolute or relative)

**Timeout Configuration**:
```python
# Handles large PDFs (120+ pages)
config = Config(
    read_timeout=600,  # 10 minutes
    connect_timeout=10,
    retries={'max_attempts': 3}
)
```

## Output Files

### Directory Structure

```
tmp/
├── textract_<trial_id>_<timestamp>.json    # Textract analysis
└── classifier_<trial_id>_<timestamp>.json  # Comprehend Medical output
```

### Textract Output

Contains complete extraction results:
- All query answers with confidence scores
- Extracted tables (including eligibility tables)
- Page count and processing metadata
- S3 location and Textract job ID

### Classifier Output

Contains structured and formatted criteria:
- Lists of inclusion/exclusion criteria
- Formatted text ready for parse-criteria API
- Medical entity density metrics
- Extraction method indicators
- Confidence scores

## Performance

### Benchmarks

| PDF Details | Textract | Classifier | Total | Quality |
|------------|----------|------------|-------|---------|
| 26 pages, 0.45 MB | 23.7s | 0.9s | 26.7s | 94.07% confidence |
| 124 pages, 0.82 MB | 75.7s | 3.8s | 85.7s | 92.66% confidence |

### Scalability

- **Small PDFs** (< 30 pages): ~30 seconds
- **Medium PDFs** (30-100 pages): ~60-90 seconds
- **Large PDFs** (100+ pages): ~90-150 seconds

## Sample Output

```
================================================================================
  PROTOCOL PDF PROCESSOR
================================================================================

Configuration:
  PDF Path: /Users/user/protocol-docs/Prot_000.pdf
  Trial ID: TEST_PROT_000_FIXED
  S3 Bucket: trial-enrollment-protocols-519510601754
  AWS Region: us-east-1
  Output Directory: /path/to/tmp

[STEP 1] Uploading PDF to S3
--------------------------------------------------------------------------------
  ✓ Upload successful!

[STEP 2] Running Textract Document Analysis
--------------------------------------------------------------------------------
  ✓ Textract processing complete! (75.7s)

  TEXTRACT SUMMARY:
    Pages processed: 124
    Confidence: 85.32%
    Query answers found: 3
    Tables found: 68

[STEP 3] Saving Textract Output
--------------------------------------------------------------------------------
  ✓ Saved successfully! (141.5 KB)

[STEP 4] Running Section Classifier (Comprehend Medical)
--------------------------------------------------------------------------------
  ✓ Section classification complete! (3.8s)

  CLASSIFIER SUMMARY:
    Total criteria: 32
    Inclusion criteria: 11
    Exclusion criteria: 21
    Overall confidence: 92.66%
    Medical entity density: 21.32%
    Extraction methods: {'queries': True, 'tables': True}

[STEP 5] Saving Section Classifier Output
--------------------------------------------------------------------------------
  ✓ Saved successfully! (11.8 KB)

================================================================================
  EXTRACTED CRITERIA
================================================================================

INCLUSION CRITERIA (11 items):
--------------------------------------------------------------------------------
1. Male or female patient receiving insulin for the treatment of documented
   diagnosis of T1DM for at least 1 year at the time of Visit 1
2. Fasting C-peptide value of < 0.7 ng/mL (0.23 nmol/L) at Visit 2
3. HbA₁c >= 7.5% and <= 10.0% at Visit 5
...

EXCLUSION CRITERIA (21 items):
--------------------------------------------------------------------------------
1. History of T2DM, maturity onset diabetes of the young (MODY),
   pancreatic surgery or chronic pancreatitis
2. Pancreas, pancreatic islet cells or renal transplant recipient
...

================================================================================
  PROCESSING COMPLETE
================================================================================

  Total time: 85.7s

  Output files:
    - Textract: tmp/textract_TEST_PROT_000_FIXED_20251011_230903.json
    - Classifier: tmp/classifier_TEST_PROT_000_FIXED_20251011_230907.json
```

## AWS Resources

### S3 Bucket
- **Name**: `trial-enrollment-protocols-{account_id}`
- **Purpose**: Store protocol PDFs
- **Structure**: `protocols/{trial_id}/{filename}.pdf`

### Lambda Functions

#### Textract Processor
- **Name**: `TrialEnrollment-TextractProcessor`
- **Timeout**: 10 minutes
- **Memory**: 1024 MB
- **Runtime**: Python 3.11
- **Permissions**: Textract read, S3 read, Lambda invoke

#### Section Classifier
- **Name**: `TrialEnrollment-SectionClassifier`
- **Timeout**: 2 minutes
- **Memory**: 512 MB
- **Runtime**: Python 3.11
- **Permissions**: Comprehend Medical read

### AWS Services Used
- **AWS Textract**: Document Analysis API
- **Amazon Comprehend Medical**: Entity Detection V2 API
- **Amazon S3**: Protocol PDF storage
- **AWS Lambda**: Serverless compute
- **Amazon CloudWatch**: Logging and monitoring

## Integration Points

### Next Steps After Processing

1. **Parse-Criteria API** (Next in pipeline)
   - Converts formatted text to FHIR format
   - Generates structured eligibility criteria
   - Creates searchable FHIR resources

2. **DynamoDB Storage**
   - Caches parsed criteria
   - Enables fast trial lookup
   - 90-day TTL for data retention

3. **FHIR Search**
   - Matches patients against criteria
   - Generates eligibility reports
   - Ranks candidates by match score

## Troubleshooting

### Common Issues

#### "PDF file not found"
- Check the file path is correct
- Use absolute paths or `~/` for home directory
- Ensure file has `.pdf` extension

#### "Lambda invocation failed"
- Verify Lambda functions are deployed
- Check AWS credentials: `aws sts get-caller-identity`
- Ensure IAM permissions are configured

#### Timeout errors
- Large PDFs (>100 pages) take longer
- Script has 10-minute timeout configured
- Check CloudWatch logs for detailed errors
- Verify Lambda function timeouts

#### Empty criteria extracted
- PDF might not have clear criteria sections
- Check Textract confidence scores in output
- Review `query_answers` in textract output file
- Try different protocol PDFs for comparison

#### Low confidence scores
- Protocol formatting may be non-standard
- Consider manual review of extracted criteria
- Check medical entity density (should be >10%)
- Review Textract confidence by page

## Best Practices

### For Best Extraction Results

1. **Protocol Format**:
   - Clear section headers ("Inclusion Criteria", "Exclusion Criteria")
   - Numbered or bulleted lists
   - Standard medical terminology
   - Readable fonts (not handwritten or artistic fonts)

2. **File Quality**:
   - Use original PDF (not scanned images when possible)
   - Good resolution for scanned documents (300+ DPI)
   - Clear, high-contrast text
   - Minimal watermarks or overlays

3. **Validation**:
   - Review confidence scores (aim for >85%)
   - Check medical entity density (>10% is good)
   - Verify criteria count matches expectations
   - Inspect JSON outputs for completeness

## Development

### Testing

Run the script with test protocols:
```bash
# Test with small PDF
python scripts/process_protocol_pdf.py protocol-docs/26_page.pdf

# Test with large PDF
python scripts/process_protocol_pdf.py protocol-docs/Prot_000.pdf
```

### Extending the System

1. **Add New Extraction Patterns**:
   - Edit `src/lambda/textract_processor/handler.py`
   - Add patterns to `CRITERIA_PATTERNS` list
   - Test with diverse protocol formats

2. **Customize Section Classifier**:
   - Modify `src/lambda/section_classifier/handler.py`
   - Adjust `MIN_CRITERION_LENGTH` / `MAX_CRITERION_LENGTH`
   - Add custom entity detection logic

3. **Enhance Script**:
   - Add batch processing support
   - Implement progress callbacks
   - Add email notifications
   - Create web UI wrapper

## Related Documentation

- **Infrastructure**: `infrastructure/app.py` - CDK stack definition
- **Deployment**: `docs/deployment_guide.md` - How to deploy the system
- **Test Results**: `tests/SECTION_CLASSIFIER_TEST_RESULTS.md` - Validation results
- **Pipeline Overview**: `END_TO_END_PIPELINE_GUIDE.md` - Complete pipeline flow

---

**Document Version**: 2.0
**Last Updated**: 2025-10-11
**Status**: ✅ Production Ready
**Test Coverage**: Small (26p) and Large (124p) PDFs validated
