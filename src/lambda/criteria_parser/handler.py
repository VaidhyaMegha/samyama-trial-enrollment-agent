"""
Criteria Parser Lambda Function

Converts free-text clinical trial eligibility criteria into structured JSON format
that can be programmatically evaluated against patient FHIR data.
"""

import json
import os
import boto3
import hashlib
from decimal import Decimal
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext

logger = Logger()
tracer = Tracer()

# Initialize AWS clients
bedrock_runtime = boto3.client('bedrock-runtime', region_name=os.environ.get('AWS_REGION', 'us-west-1'))
dynamodb = boto3.resource('dynamodb', region_name=os.environ.get('AWS_REGION', 'us-east-1'))

# Get DynamoDB table
CRITERIA_CACHE_TABLE_NAME = os.environ.get('CRITERIA_CACHE_TABLE')
criteria_cache_table = dynamodb.Table(CRITERIA_CACHE_TABLE_NAME) if CRITERIA_CACHE_TABLE_NAME else None

# Parsing prompt template
PARSING_PROMPT = """You are an expert medical AI assistant specializing in clinical trial eligibility criteria.

Your task is to parse free-text clinical trial eligibility criteria and convert them into a structured JSON format.

For each criterion, extract:
1. **type**: "inclusion" or "exclusion"
2. **category**: The domain (e.g., "demographics", "condition", "lab_value", "medication", "procedure")
3. **description**: Natural language description of the criterion
4. **attribute**: What is being checked (e.g., "age", "HbA1c", "diagnosis")
5. **operator**: Comparison operator ("equals", "greater_than", "less_than", "between", "contains", "not_contains")
6. **value**: The value(s) to compare against
7. **unit**: Unit of measurement (if applicable)
8. **fhir_resource**: FHIR resource type to query (e.g., "Patient", "Observation", "Condition")
9. **fhir_path**: FHIR path to the relevant field (e.g., "Patient.birthDate", "Observation.valueQuantity")

Examples:

Input: "Patients must be between 18 and 65 years old"
Output:
{{
  "type": "inclusion",
  "category": "demographics",
  "description": "Age between 18 and 65 years",
  "attribute": "age",
  "operator": "between",
  "value": [18, 65],
  "unit": "years",
  "fhir_resource": "Patient",
  "fhir_path": "Patient.birthDate"
}}

Input: "HbA1c must be between 7% and 10%"
Output:
{{
  "type": "inclusion",
  "category": "lab_value",
  "description": "HbA1c between 7% and 10%",
  "attribute": "HbA1c",
  "operator": "between",
  "value": [7, 10],
  "unit": "%",
  "fhir_resource": "Observation",
  "fhir_path": "Observation.valueQuantity",
  "coding": {{
    "system": "http://loinc.org",
    "code": "4548-4",
    "display": "Hemoglobin A1c"
  }}
}}

Input: "Patients must NOT have chronic kidney disease stage 4 or higher"
Output:
{{
  "type": "exclusion",
  "category": "condition",
  "description": "No chronic kidney disease stage 4 or higher",
  "attribute": "chronic_kidney_disease",
  "operator": "not_contains",
  "value": "chronic kidney disease stage 4",
  "fhir_resource": "Condition",
  "fhir_path": "Condition.code",
  "coding": {{
    "system": "http://snomed.info/sct",
    "code": "431855005",
    "display": "Chronic kidney disease stage 4"
  }}
}}

Now parse the following criteria text:

{criteria_text}

Return ONLY a JSON array of criterion objects. Do not include any explanatory text."""


def convert_decimals(obj: Any) -> Any:
    """
    Recursively convert Decimal objects to int or float.
    DynamoDB returns numbers as Decimal objects which aren't JSON serializable.

    Args:
        obj: The object to convert

    Returns:
        The object with Decimals converted to int/float
    """
    if isinstance(obj, list):
        return [convert_decimals(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: convert_decimals(value) for key, value in obj.items()}
    elif isinstance(obj, Decimal):
        # Convert to int if it's a whole number, otherwise float
        if obj % 1 == 0:
            return int(obj)
        else:
            return float(obj)
    else:
        return obj


def generate_cache_key(criteria_text: str, trial_id: str) -> str:
    """
    Generate a unique cache key based on criteria text and trial ID.

    Args:
        criteria_text: The criteria text
        trial_id: Trial identifier

    Returns:
        Cache key string
    """
    content = f"{trial_id}:{criteria_text}"
    return hashlib.sha256(content.encode()).hexdigest()


@tracer.capture_method
def get_cached_criteria(trial_id: str, criteria_text: str) -> Optional[List[Dict[str, Any]]]:
    """
    Retrieve cached parsed criteria from DynamoDB.

    Args:
        trial_id: Trial identifier
        criteria_text: The criteria text to check

    Returns:
        Cached criteria if found and not expired, None otherwise
    """
    if not criteria_cache_table:
        logger.info("DynamoDB cache table not configured")
        return None

    try:
        cache_key = generate_cache_key(criteria_text, trial_id)

        response = criteria_cache_table.get_item(
            Key={'trial_id': trial_id}
        )

        if 'Item' not in response:
            logger.info(f"Cache miss for trial_id: {trial_id}")
            return None

        item = response['Item']

        # Check if cache key matches (criteria text hasn't changed)
        if item.get('cache_key') != cache_key:
            logger.info(f"Cache key mismatch for trial_id: {trial_id}")
            return None

        # Check if cache is expired (default TTL: 7 days)
        if 'ttl' in item:
            current_time = int(datetime.utcnow().timestamp())
            if current_time > item['ttl']:
                logger.info(f"Cache expired for trial_id: {trial_id}")
                return None

        logger.info(f"Cache hit for trial_id: {trial_id}")
        # Convert Decimal objects to int/float for JSON serialization
        cached_data = item.get('parsed_criteria')
        return convert_decimals(cached_data) if cached_data else None

    except Exception as e:
        logger.error(f"Error retrieving from cache: {str(e)}")
        # Don't fail the request if cache retrieval fails
        return None


@tracer.capture_method
def save_to_cache(trial_id: str, criteria_text: str, parsed_criteria: List[Dict[str, Any]]) -> None:
    """
    Save parsed criteria to DynamoDB cache.

    Args:
        trial_id: Trial identifier
        criteria_text: The original criteria text
        parsed_criteria: The parsed criteria to cache
    """
    if not criteria_cache_table:
        logger.info("DynamoDB cache table not configured")
        return

    try:
        cache_key = generate_cache_key(criteria_text, trial_id)

        # Set TTL to 7 days from now
        ttl = int((datetime.utcnow() + timedelta(days=7)).timestamp())

        criteria_cache_table.put_item(
            Item={
                'trial_id': trial_id,
                'cache_key': cache_key,
                'criteria_text': criteria_text,
                'parsed_criteria': parsed_criteria,
                'created_at': datetime.utcnow().isoformat(),
                'ttl': ttl
            }
        )

        logger.info(f"Saved to cache for trial_id: {trial_id}")

    except Exception as e:
        logger.error(f"Error saving to cache: {str(e)}")
        # Don't fail the request if cache save fails


@tracer.capture_method
def parse_criteria_with_bedrock(criteria_text: str, model_id: str = "amazon.titan-text-express-v1") -> List[Dict[str, Any]]:
    """
    Use Bedrock to parse eligibility criteria into structured format.

    Args:
        criteria_text: Free-text eligibility criteria
        model_id: Bedrock model ID to use

    Returns:
        List of parsed criterion dictionaries
    """
    prompt = PARSING_PROMPT.format(criteria_text=criteria_text)

    # Prepare request for Titan model
    request_body = {
        "inputText": prompt,
        "textGenerationConfig": {
            "maxTokenCount": 4000,
            "temperature": 0.1,  # Low temperature for consistent parsing
            "topP": 0.9
        }
    }

    try:
        response = bedrock_runtime.invoke_model(
            modelId=model_id,
            body=json.dumps(request_body)
        )

        response_body = json.loads(response['body'].read())
        logger.info("Bedrock response received", extra={"response": response_body})

        # Extract the parsed criteria from response (Titan format)
        # Support both old and new Bedrock API formats
        if 'results' in response_body:
            content = response_body['results'][0]['outputText']
        elif 'content' in response_body:
            content = response_body['content'][0]['text']
        else:
            raise ValueError(f"Unexpected Bedrock response format: {response_body}")

        # Parse JSON from response
        # Handle cases where LLM might wrap JSON in markdown code blocks
        content = content.strip()

        # Check if content contains backticks (markdown code blocks)
        if '```' in content:
            # Extract content between first and last backticks
            first_backtick = content.find('```')
            last_backtick = content.rfind('```')

            if first_backtick != -1 and last_backtick != -1 and first_backtick < last_backtick:
                # Extract the content between backticks
                content = content[first_backtick:last_backtick]

                # Remove the opening backticks and optional language identifier
                # Handle various formats: ```json, ```tabular-data-json, etc.
                if content.startswith('```'):
                    # Find the end of the first line (language identifier)
                    newline_pos = content.find('\n')
                    if newline_pos != -1:
                        content = content[newline_pos+1:]
                    else:
                        content = content[3:]

                content = content.strip()
        else:
            # No backticks, use content as-is
            content = content.strip()

        parsed_criteria = json.loads(content)

        # Ensure it's a list
        # Handle cases where the response might be wrapped in an object (e.g., {"rows": [...]})
        if isinstance(parsed_criteria, dict):
            if 'rows' in parsed_criteria:
                parsed_criteria = parsed_criteria['rows']
            else:
                parsed_criteria = [parsed_criteria]

        logger.info(f"Successfully parsed {len(parsed_criteria)} criteria")
        return parsed_criteria

    except Exception as e:
        logger.error(f"Error parsing criteria with Bedrock: {str(e)}")
        raise


@tracer.capture_method
def validate_criterion(criterion: Dict[str, Any]) -> bool:
    """
    Validate that a parsed criterion has all required fields.

    Args:
        criterion: Parsed criterion dictionary

    Returns:
        True if valid, raises ValueError if invalid
    """
    required_fields = ['type', 'category', 'description', 'attribute', 'operator', 'value']

    for field in required_fields:
        if field not in criterion:
            raise ValueError(f"Missing required field: {field}")

    # Validate type
    if criterion['type'] not in ['inclusion', 'exclusion']:
        raise ValueError(f"Invalid type: {criterion['type']}. Must be 'inclusion' or 'exclusion'")

    # Validate operator
    valid_operators = ['equals', 'greater_than', 'less_than', 'between', 'contains', 'not_contains', 'exists', 'not_exists']
    if criterion['operator'] not in valid_operators:
        raise ValueError(f"Invalid operator: {criterion['operator']}")

    return True


@logger.inject_lambda_context(log_event=True)
@tracer.capture_lambda_handler
def lambda_handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    Lambda handler for criteria parsing.

    Expected event format:
    {
        "criteria_text": "Free-text eligibility criteria...",
        "trial_id": "optional-trial-identifier"
    }

    Returns:
    {
        "statusCode": 200,
        "body": {
            "criteria": [...parsed criteria...],
            "trial_id": "...",
            "count": N
        }
    }
    """
    try:
        # Extract input
        if 'body' in event:
            body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
        else:
            body = event

        criteria_text = body.get('criteria_text')
        trial_id = body.get('trial_id', 'unknown')

        if not criteria_text:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Missing required field: criteria_text'
                })
            }

        logger.info(f"Parsing criteria for trial: {trial_id}")

        # Try to get from cache first
        cached_criteria = get_cached_criteria(trial_id, criteria_text)
        cache_hit = False

        if cached_criteria:
            logger.info(f"Using cached criteria for trial: {trial_id}")
            parsed_criteria = cached_criteria
            cache_hit = True
        else:
            # Parse criteria using Bedrock
            logger.info(f"Cache miss - parsing with Bedrock for trial: {trial_id}")
            parsed_criteria = parse_criteria_with_bedrock(criteria_text)

            # Save to cache for future requests
            save_to_cache(trial_id, criteria_text, parsed_criteria)

        # Validate each criterion
        for idx, criterion in enumerate(parsed_criteria):
            try:
                validate_criterion(criterion)
            except ValueError as e:
                logger.warning(f"Criterion {idx} validation failed: {str(e)}")
                # Add validation warning to criterion
                criterion['validation_warning'] = str(e)

        # Prepare response
        response_body = {
            'criteria': parsed_criteria,
            'trial_id': trial_id,
            'count': len(parsed_criteria),
            'metadata': {
                'model': 'amazon.titan-text-express-v1',
                'timestamp': context.get_remaining_time_in_millis() if context else None,
                'cache_hit': cache_hit,
                'cache_enabled': criteria_cache_table is not None
            }
        }

        logger.info(f"Successfully parsed {len(parsed_criteria)} criteria for trial {trial_id}")

        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(response_body)
        }

    except Exception as e:
        logger.error(f"Error in lambda_handler: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': str(e),
                'message': 'Failed to parse criteria'
            })
        }
