#!/usr/bin/env python3
"""
End-to-End Protocol PDF Processor

This script processes a clinical trial protocol PDF through the complete pipeline:
1. Upload PDF to S3
2. Run Textract document analysis
3. Save Textract output to tmp/
4. Run Section Classifier (Comprehend Medical)
5. Save Section Classifier output to tmp/

Usage:
    python scripts/process_protocol_pdf.py <path_to_pdf>

Example:
    python scripts/process_protocol_pdf.py ~/Downloads/trial_protocol.pdf
"""

import argparse
import boto3
import json
import os
import sys
import time
from pathlib import Path
from datetime import datetime
from botocore.config import Config

# AWS Configuration
AWS_REGION = 'us-east-1'
AWS_ACCOUNT_ID = '519510601754'
S3_BUCKET = f'trial-enrollment-protocols-{AWS_ACCOUNT_ID}'
TEXTRACT_FUNCTION = 'TrialEnrollment-TextractProcessor'
CLASSIFIER_FUNCTION = 'TrialEnrollment-SectionClassifier'

# Initialize AWS clients with extended timeouts for large PDFs
config = Config(
    read_timeout=600,  # 10 minutes for Textract processing
    connect_timeout=10,
    retries={'max_attempts': 3}
)

s3_client = boto3.client('s3', region_name=AWS_REGION)
lambda_client = boto3.client('lambda', region_name=AWS_REGION, config=config)

# Output directories
SCRIPT_DIR = Path(__file__).parent.absolute()
PROJECT_DIR = SCRIPT_DIR.parent
TMP_DIR = PROJECT_DIR / 'tmp'
TMP_DIR.mkdir(exist_ok=True)


def print_header(text):
    """Print formatted header"""
    print(f"\n{'='*80}")
    print(f"  {text}")
    print('='*80)


def print_step(number, text):
    """Print formatted step"""
    print(f"\n[STEP {number}] {text}")
    print('-' * 80)


def upload_to_s3(pdf_path, trial_id):
    """
    Upload PDF to S3 bucket

    Args:
        pdf_path: Path to the PDF file
        trial_id: Unique identifier for this trial

    Returns:
        S3 key for the uploaded file
    """
    print_step(1, "Uploading PDF to S3")

    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    # Generate S3 key
    filename = Path(pdf_path).name
    s3_key = f"protocols/{trial_id}/{filename}"

    print(f"  File: {pdf_path}")
    print(f"  Bucket: {S3_BUCKET}")
    print(f"  Key: {s3_key}")
    print(f"  Size: {os.path.getsize(pdf_path) / (1024*1024):.2f} MB")

    try:
        # Upload file
        print(f"\n  Uploading...")
        s3_client.upload_file(pdf_path, S3_BUCKET, s3_key)
        print(f"  ✓ Upload successful!")
        return s3_key
    except Exception as e:
        print(f"  ✗ Upload failed: {e}")
        raise


def invoke_textract_processor(s3_bucket, s3_key, trial_id):
    """
    Invoke Textract Processor Lambda to extract text from PDF

    Args:
        s3_bucket: S3 bucket name
        s3_key: S3 key for the PDF
        trial_id: Trial identifier

    Returns:
        Textract processor output
    """
    print_step(2, "Running Textract Document Analysis")

    # Prepare event for Textract Processor
    event = {
        "s3_bucket": s3_bucket,
        "s3_key": s3_key,
        "trial_id": trial_id
    }

    print(f"  Function: {TEXTRACT_FUNCTION}")
    print(f"  Trial ID: {trial_id}")
    print(f"  Input: {json.dumps(event, indent=2)}")

    try:
        print(f"\n  Invoking Lambda (this may take 30-60 seconds for large PDFs)...")
        start_time = time.time()

        response = lambda_client.invoke(
            FunctionName=TEXTRACT_FUNCTION,
            InvocationType='RequestResponse',
            Payload=json.dumps(event)
        )

        elapsed = time.time() - start_time

        # Parse response
        result = json.loads(response['Payload'].read())

        if response['StatusCode'] != 200:
            raise Exception(f"Lambda invocation failed with status {response['StatusCode']}")

        # Handle Lambda error response
        if 'errorMessage' in result:
            raise Exception(f"Lambda error: {result['errorMessage']}")

        # Parse body (Lambda returns API Gateway format)
        if 'body' in result:
            body = json.loads(result['body']) if isinstance(result['body'], str) else result['body']
        else:
            body = result

        print(f"  ✓ Textract processing complete! ({elapsed:.1f}s)")

        # Print summary
        # Note: Response structure varies - check for nested or top-level data
        if 'textract_output' in body:
            textract_data = body['textract_output']
        else:
            # Data is at top level
            textract_data = body

        print(f"\n  TEXTRACT SUMMARY:")
        print(f"    Pages processed: {textract_data.get('pages', 0)}")
        print(f"    Confidence: {textract_data.get('confidence', 0)*100:.2f}%")

        # Handle both dict (query_answers) and list formats
        query_answers = textract_data.get('query_answers', {})
        if isinstance(query_answers, dict):
            print(f"    Query answers found: {len(query_answers)}")
        else:
            print(f"    Query answers found: {len(query_answers) if query_answers else 0}")

        print(f"    Tables found: {len(textract_data.get('tables', []))}")

        return body

    except Exception as e:
        print(f"  ✗ Textract processing failed: {e}")
        raise


def save_textract_output(textract_output, trial_id):
    """
    Save Textract output to tmp directory

    Args:
        textract_output: Textract processor response
        trial_id: Trial identifier

    Returns:
        Path to saved file
    """
    print_step(3, "Saving Textract Output")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = TMP_DIR / f"textract_{trial_id}_{timestamp}.json"

    print(f"  Output file: {output_file}")

    try:
        with open(output_file, 'w') as f:
            json.dump(textract_output, f, indent=2)

        file_size = os.path.getsize(output_file) / 1024
        print(f"  ✓ Saved successfully! ({file_size:.1f} KB)")
        return output_file

    except Exception as e:
        print(f"  ✗ Save failed: {e}")
        raise


def invoke_section_classifier(textract_output, trial_id):
    """
    Invoke Section Classifier Lambda to extract and classify criteria

    Args:
        textract_output: Output from Textract processor
        trial_id: Trial identifier

    Returns:
        Section classifier output
    """
    print_step(4, "Running Section Classifier (Comprehend Medical)")

    # Prepare event for Section Classifier
    # Handle both nested and top-level response structures
    if 'textract_output' in textract_output:
        textract_data = textract_output['textract_output']
    else:
        # Data is already at top level, use as-is
        textract_data = textract_output

    event = {
        'textract_output': textract_data,
        'trial_id': trial_id
    }

    print(f"  Function: {CLASSIFIER_FUNCTION}")
    print(f"  Trial ID: {trial_id}")

    try:
        print(f"\n  Invoking Lambda (analyzing medical entities)...")
        start_time = time.time()

        response = lambda_client.invoke(
            FunctionName=CLASSIFIER_FUNCTION,
            InvocationType='RequestResponse',
            Payload=json.dumps(event)
        )

        elapsed = time.time() - start_time

        # Parse response
        result = json.loads(response['Payload'].read())

        if response['StatusCode'] != 200:
            raise Exception(f"Lambda invocation failed with status {response['StatusCode']}")

        # Handle Lambda error response
        if 'errorMessage' in result:
            raise Exception(f"Lambda error: {result['errorMessage']}")

        # Parse body
        if 'body' in result:
            body = json.loads(result['body']) if isinstance(result['body'], str) else result['body']
        else:
            body = result

        print(f"  ✓ Section classification complete! ({elapsed:.1f}s)")

        # Print summary
        metadata = body.get('metadata', {})

        print(f"\n  CLASSIFIER SUMMARY:")
        print(f"    Total criteria: {metadata.get('total_criteria', 0)}")
        print(f"    Inclusion criteria: {metadata.get('inclusion_count', 0)}")
        print(f"    Exclusion criteria: {metadata.get('exclusion_count', 0)}")
        print(f"    Overall confidence: {metadata.get('overall_confidence', 0)*100:.2f}%")
        print(f"    Medical entity density: {metadata.get('medical_entity_density', 0):.2f}%")
        print(f"    Extraction methods: {metadata.get('extraction_methods', {})}")

        return body

    except Exception as e:
        print(f"  ✗ Section classification failed: {e}")
        raise


def save_classifier_output(classifier_output, trial_id):
    """
    Save Section Classifier output to tmp directory

    Args:
        classifier_output: Section classifier response
        trial_id: Trial identifier

    Returns:
        Path to saved file
    """
    print_step(5, "Saving Section Classifier Output")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = TMP_DIR / f"classifier_{trial_id}_{timestamp}.json"

    print(f"  Output file: {output_file}")

    try:
        with open(output_file, 'w') as f:
            json.dump(classifier_output, f, indent=2)

        file_size = os.path.getsize(output_file) / 1024
        print(f"  ✓ Saved successfully! ({file_size:.1f} KB)")
        return output_file

    except Exception as e:
        print(f"  ✗ Save failed: {e}")
        raise


def print_extracted_criteria(classifier_output):
    """
    Pretty-print the extracted criteria

    Args:
        classifier_output: Section classifier output
    """
    print_header("EXTRACTED CRITERIA")

    inclusion = classifier_output.get('inclusion_criteria', [])
    exclusion = classifier_output.get('exclusion_criteria', [])

    print(f"\nINCLUSION CRITERIA ({len(inclusion)} items):")
    print('-' * 80)
    for i, criterion in enumerate(inclusion, 1):
        print(f"{i}. {criterion}")

    print(f"\nEXCLUSION CRITERIA ({len(exclusion)} items):")
    print('-' * 80)
    for i, criterion in enumerate(exclusion, 1):
        print(f"{i}. {criterion}")

    print(f"\nFORMATTED TEXT (ready for parse-criteria API):")
    print('-' * 80)
    print(classifier_output.get('formatted_text', ''))


def main():
    """Main execution function"""

    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='Process clinical trial protocol PDF through Textract and Section Classifier',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process a protocol PDF
  python scripts/process_protocol_pdf.py ~/Downloads/trial_protocol.pdf

  # Process with custom trial ID
  python scripts/process_protocol_pdf.py ~/Downloads/trial_protocol.pdf --trial-id NCT12345678
        """
    )
    parser.add_argument('pdf_path', help='Path to the protocol PDF file')
    parser.add_argument('--trial-id', help='Custom trial ID (default: auto-generated)', default=None)

    args = parser.parse_args()

    # Validate PDF path
    pdf_path = Path(args.pdf_path).expanduser().absolute()
    if not pdf_path.exists():
        print(f"ERROR: PDF file not found: {pdf_path}")
        sys.exit(1)

    if not pdf_path.suffix.lower() == '.pdf':
        print(f"ERROR: File is not a PDF: {pdf_path}")
        sys.exit(1)

    # Generate trial ID
    if args.trial_id:
        trial_id = args.trial_id
    else:
        # Use filename + timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        trial_id = f"{pdf_path.stem}_{timestamp}"

    # Print configuration
    print_header("PROTOCOL PDF PROCESSOR")
    print(f"\nConfiguration:")
    print(f"  PDF Path: {pdf_path}")
    print(f"  Trial ID: {trial_id}")
    print(f"  S3 Bucket: {S3_BUCKET}")
    print(f"  AWS Region: {AWS_REGION}")
    print(f"  Output Directory: {TMP_DIR}")

    try:
        # Execute pipeline
        start_time = time.time()

        # Step 1: Upload to S3
        s3_key = upload_to_s3(str(pdf_path), trial_id)

        # Step 2: Run Textract
        textract_output = invoke_textract_processor(S3_BUCKET, s3_key, trial_id)

        # Step 3: Save Textract output
        textract_file = save_textract_output(textract_output, trial_id)

        # Step 4: Run Section Classifier
        classifier_output = invoke_section_classifier(textract_output, trial_id)

        # Step 5: Save Classifier output
        classifier_file = save_classifier_output(classifier_output, trial_id)

        # Print extracted criteria
        print_extracted_criteria(classifier_output)

        # Print final summary
        total_time = time.time() - start_time
        print_header("PROCESSING COMPLETE")
        print(f"\n  Total time: {total_time:.1f}s")
        print(f"\n  Output files:")
        print(f"    - Textract: {textract_file}")
        print(f"    - Classifier: {classifier_file}")
        print(f"\n  Next steps:")
        print(f"    - Test parse-criteria API with: tmp/{classifier_file.name}")
        print(f"    - View formatted criteria above")
        print(f"    - S3 location: s3://{S3_BUCKET}/{s3_key}")
        print()

        sys.exit(0)

    except Exception as e:
        print(f"\n{'='*80}")
        print(f"  ERROR: {e}")
        print('='*80)
        sys.exit(1)


if __name__ == '__main__':
    main()
