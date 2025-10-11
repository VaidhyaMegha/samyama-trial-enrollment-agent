"""
Protocol Orchestrator Lambda Function

Orchestrates the end-to-end protocol processing pipeline:
1. Receives Textract output (from Textract Processor)
2. Invokes Section Classifier to extract criteria
3. Calls parse-criteria API to convert to FHIR format
4. Stores results in DynamoDB
5. Returns structured FHIR resources

Features:
- Automatic pipeline chaining
- Error handling and retries
- DynamoDB caching
- Progress tracking
- Comprehensive logging
"""

import json
import os
import time
from typing import Dict, List, Any, Optional
from datetime import datetime
import boto3
import urllib3
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext

logger = Logger()
tracer = Tracer()

# Initialize AWS clients
lambda_client = boto3.client('lambda')
dynamodb = boto3.resource('dynamodb')
http = urllib3.PoolManager()

# Configuration
SECTION_CLASSIFIER_FUNCTION = os.environ.get(
    'SECTION_CLASSIFIER_FUNCTION',
    'TrialEnrollment-SectionClassifier'
)
PARSE_CRITERIA_API_ENDPOINT = os.environ.get(
    'PARSE_CRITERIA_API_ENDPOINT',
    'https://gt7dlyqj78.execute-api.us-east-1.amazonaws.com/prod/parse-criteria'
)
CRITERIA_CACHE_TABLE = os.environ.get('CRITERIA_CACHE_TABLE', 'CriteriaCacheTable')
MAX_RETRIES = int(os.environ.get('MAX_RETRIES', '3'))
RETRY_DELAY_SECONDS = int(os.environ.get('RETRY_DELAY_SECONDS', '2'))


@tracer.capture_method
def invoke_section_classifier(
    textract_output: Dict[str, Any],
    trial_id: str
) -> Optional[Dict[str, Any]]:
    """
    Invoke Section Classifier Lambda to extract criteria.

    Args:
        textract_output: Output from Textract Processor
        trial_id: Clinical trial identifier

    Returns:
        Section Classifier response with criteria
    """
    event = {
        'textract_output': textract_output,
        'trial_id': trial_id
    }

    logger.info(f"Invoking Section Classifier for trial: {trial_id}")

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = lambda_client.invoke(
                FunctionName=SECTION_CLASSIFIER_FUNCTION,
                InvocationType='RequestResponse',
                Payload=json.dumps(event)
            )

            payload = json.loads(response['Payload'].read())

            if payload.get('statusCode') == 200:
                body = json.loads(payload['body'])
                logger.info(
                    f"Section Classifier success: "
                    f"{body['metadata']['total_criteria']} criteria extracted"
                )
                return body
            else:
                error = json.loads(payload['body'])
                logger.error(f"Section Classifier error: {error}")

                if attempt < MAX_RETRIES:
                    logger.info(f"Retrying... (attempt {attempt + 1}/{MAX_RETRIES})")
                    time.sleep(RETRY_DELAY_SECONDS * attempt)
                    continue

                return None

        except Exception as e:
            logger.error(f"Section Classifier invocation error: {str(e)}")

            if attempt < MAX_RETRIES:
                logger.info(f"Retrying... (attempt {attempt + 1}/{MAX_RETRIES})")
                time.sleep(RETRY_DELAY_SECONDS * attempt)
                continue

            raise

    return None


@tracer.capture_method
def call_parse_criteria_api(
    trial_id: str,
    criteria_text: str
) -> Optional[Dict[str, Any]]:
    """
    Call parse-criteria API to convert criteria to FHIR format.

    Args:
        trial_id: Clinical trial identifier
        criteria_text: Formatted criteria text (Inclusion/Exclusion)

    Returns:
        Parse-criteria API response with FHIR resources
    """
    payload = {
        'trial_id': trial_id,
        'criteria_text': criteria_text
    }

    logger.info(f"Calling parse-criteria API for trial: {trial_id}")

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = http.request(
                'POST',
                PARSE_CRITERIA_API_ENDPOINT,
                body=json.dumps(payload),
                headers={'Content-Type': 'application/json'},
                timeout=30.0
            )

            if response.status == 200:
                result = json.loads(response.data.decode('utf-8'))
                logger.info(
                    f"Parse-criteria API success: "
                    f"{len(result.get('parsed_criteria', []))} criteria parsed"
                )
                return result
            else:
                logger.error(
                    f"Parse-criteria API error (status {response.status}): "
                    f"{response.data.decode('utf-8')}"
                )

                if attempt < MAX_RETRIES:
                    logger.info(f"Retrying... (attempt {attempt + 1}/{MAX_RETRIES})")
                    time.sleep(RETRY_DELAY_SECONDS * attempt)
                    continue

                return None

        except Exception as e:
            logger.error(f"Parse-criteria API call error: {str(e)}")

            if attempt < MAX_RETRIES:
                logger.info(f"Retrying... (attempt {attempt + 1}/{MAX_RETRIES})")
                time.sleep(RETRY_DELAY_SECONDS * attempt)
                continue

            raise

    return None


@tracer.capture_method
def store_results_in_dynamodb(
    trial_id: str,
    criteria_data: Dict[str, Any],
    parsed_data: Dict[str, Any],
    textract_confidence: float
) -> bool:
    """
    Store processing results in DynamoDB for caching.

    Args:
        trial_id: Clinical trial identifier
        criteria_data: Extracted criteria from Section Classifier
        parsed_data: Parsed FHIR data from parse-criteria API
        textract_confidence: Textract extraction confidence

    Returns:
        True if successful, False otherwise
    """
    try:
        table = dynamodb.Table(CRITERIA_CACHE_TABLE)

        timestamp = datetime.utcnow().isoformat()

        item = {
            'trial_id': trial_id,
            'timestamp': timestamp,
            'inclusion_criteria': criteria_data.get('inclusion_criteria', []),
            'exclusion_criteria': criteria_data.get('exclusion_criteria', []),
            'formatted_text': criteria_data.get('formatted_text', ''),
            'metadata': {
                'total_criteria': criteria_data['metadata']['total_criteria'],
                'inclusion_count': criteria_data['metadata']['inclusion_count'],
                'exclusion_count': criteria_data['metadata']['exclusion_count'],
                'textract_confidence': textract_confidence,
                'extraction_confidence': criteria_data['metadata']['extraction_confidence'],
                'overall_confidence': criteria_data['metadata']['overall_confidence'],
                'medical_entity_density': criteria_data['metadata'].get('medical_entity_density', 0),
                'extraction_methods': criteria_data['metadata'].get('extraction_methods', {})
            },
            'parsed_criteria': parsed_data.get('parsed_criteria', []),
            'fhir_resources': parsed_data.get('fhir_resources', {}),
            'processing_status': 'completed',
            'ttl': int(time.time()) + (90 * 24 * 60 * 60)  # 90 days TTL
        }

        table.put_item(Item=item)

        logger.info(f"Stored results in DynamoDB for trial: {trial_id}")
        return True

    except Exception as e:
        logger.error(f"DynamoDB storage error: {str(e)}")
        return False


@tracer.capture_method
def get_cached_results(trial_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve cached results from DynamoDB if available.

    Args:
        trial_id: Clinical trial identifier

    Returns:
        Cached results or None
    """
    try:
        table = dynamodb.Table(CRITERIA_CACHE_TABLE)

        response = table.get_item(Key={'trial_id': trial_id})

        if 'Item' in response:
            item = response['Item']

            # Check if results are recent (within 30 days)
            timestamp = datetime.fromisoformat(item['timestamp'])
            age_days = (datetime.utcnow() - timestamp).days

            if age_days <= 30:
                logger.info(f"Using cached results for trial: {trial_id} (age: {age_days} days)")
                return item
            else:
                logger.info(f"Cached results too old for trial: {trial_id} (age: {age_days} days)")

        return None

    except Exception as e:
        logger.warning(f"DynamoDB cache retrieval error: {str(e)}")
        return None


@logger.inject_lambda_context(log_event=True)
@tracer.capture_lambda_handler
def lambda_handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    Lambda handler for protocol processing orchestration.

    Expected event formats:

    1. From Textract Processor (automatic pipeline):
    {
        "trial_id": "NCT12345678",
        "textract_output": {
            "query_answers": {...},
            "tables": [...],
            "confidence": 0.89
        }
    }

    2. Direct invocation with S3 reference:
    {
        "trial_id": "NCT12345678",
        "s3_bucket": "bucket-name",
        "s3_key": "NCT12345678.pdf",
        "use_cache": true  # Optional, defaults to true
    }

    Returns:
    {
        "statusCode": 200,
        "body": {
            "trial_id": "NCT12345678",
            "status": "success",
            "source": "cache" | "pipeline",
            "inclusion_criteria": [...],
            "exclusion_criteria": [...],
            "parsed_criteria": [...],
            "fhir_resources": {...},
            "metadata": {...}
        }
    }
    """
    start_time = time.time()

    try:
        # Extract input
        trial_id = event.get('trial_id')
        textract_output = event.get('textract_output')
        use_cache = event.get('use_cache', True)

        if not trial_id:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Missing required field: trial_id'
                })
            }

        logger.info(f"Starting protocol orchestration for trial: {trial_id}")

        # Check cache first (if enabled)
        if use_cache:
            cached_results = get_cached_results(trial_id)
            if cached_results:
                processing_time = time.time() - start_time

                result = {
                    'trial_id': trial_id,
                    'status': 'success',
                    'source': 'cache',
                    'inclusion_criteria': cached_results.get('inclusion_criteria', []),
                    'exclusion_criteria': cached_results.get('exclusion_criteria', []),
                    'formatted_text': cached_results.get('formatted_text', ''),
                    'parsed_criteria': cached_results.get('parsed_criteria', []),
                    'fhir_resources': cached_results.get('fhir_resources', {}),
                    'metadata': cached_results.get('metadata', {}),
                    'processing_time_seconds': round(processing_time, 2),
                    'cache_timestamp': cached_results.get('timestamp')
                }

                return {
                    'statusCode': 200,
                    'headers': {'Content-Type': 'application/json'},
                    'body': json.dumps(result)
                }

        # If no Textract output provided, cannot proceed
        if not textract_output:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Missing required field: textract_output',
                    'message': 'Textract output must be provided for processing'
                })
            }

        # Step 1: Invoke Section Classifier
        logger.info("Step 1/3: Extracting criteria with Section Classifier")
        criteria_data = invoke_section_classifier(textract_output, trial_id)

        if not criteria_data:
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'error': 'Section Classifier failed',
                    'trial_id': trial_id
                })
            }

        # Step 2: Call parse-criteria API
        logger.info("Step 2/3: Parsing criteria with parse-criteria API")
        formatted_criteria = criteria_data.get('formatted_text', '')

        if not formatted_criteria:
            logger.warning("No formatted criteria available, skipping parse-criteria API")
            parsed_data = {'parsed_criteria': [], 'fhir_resources': {}}
        else:
            parsed_data = call_parse_criteria_api(trial_id, formatted_criteria)

            if not parsed_data:
                return {
                    'statusCode': 500,
                    'body': json.dumps({
                        'error': 'Parse-criteria API failed',
                        'trial_id': trial_id
                    })
                }

        # Step 3: Store results in DynamoDB
        logger.info("Step 3/3: Storing results in DynamoDB")
        textract_confidence = textract_output.get('confidence', 0.0)
        store_success = store_results_in_dynamodb(
            trial_id,
            criteria_data,
            parsed_data,
            textract_confidence
        )

        if not store_success:
            logger.warning("Failed to store results in DynamoDB, but continuing")

        # Prepare final response
        processing_time = time.time() - start_time

        result = {
            'trial_id': trial_id,
            'status': 'success',
            'source': 'pipeline',
            'inclusion_criteria': criteria_data.get('inclusion_criteria', []),
            'exclusion_criteria': criteria_data.get('exclusion_criteria', []),
            'formatted_text': formatted_criteria,
            'parsed_criteria': parsed_data.get('parsed_criteria', []),
            'fhir_resources': parsed_data.get('fhir_resources', {}),
            'metadata': {
                **criteria_data.get('metadata', {}),
                'processing_time_seconds': round(processing_time, 2),
                'cache_stored': store_success,
                'pipeline_steps': {
                    'textract': 'completed',
                    'section_classifier': 'completed',
                    'parse_criteria': 'completed' if formatted_criteria else 'skipped',
                    'storage': 'completed' if store_success else 'failed'
                }
            }
        }

        logger.info(
            f"Protocol orchestration completed for trial {trial_id} "
            f"in {processing_time:.2f}s"
        )

        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps(result)
        }

    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(
            f"Protocol orchestration failed: {str(e)} "
            f"(after {processing_time:.2f}s)",
            exc_info=True
        )

        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Protocol orchestration failed',
                'message': str(e),
                'trial_id': event.get('trial_id', 'unknown')
            })
        }
