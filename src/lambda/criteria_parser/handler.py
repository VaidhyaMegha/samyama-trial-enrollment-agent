"""
Criteria Parser Lambda Function

Converts free-text clinical trial eligibility criteria into structured JSON format
that can be programmatically evaluated against patient FHIR data.
"""

import json
import os
import boto3
from typing import Dict, List, Any
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext

logger = Logger()
tracer = Tracer()

# Initialize Bedrock client
bedrock_runtime = boto3.client('bedrock-runtime', region_name=os.environ.get('AWS_REGION', 'us-west-1'))

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
        if content.startswith('```json'):
            content = content[7:]  # Remove ```json
        if content.startswith('```'):
            content = content[3:]  # Remove ```
        if content.endswith('```'):
            content = content[:-3]  # Remove trailing ```
        content = content.strip()

        parsed_criteria = json.loads(content)

        # Ensure it's a list
        if isinstance(parsed_criteria, dict):
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

        # Parse criteria using Bedrock
        parsed_criteria = parse_criteria_with_bedrock(criteria_text)

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
                'timestamp': context.get_remaining_time_in_millis() if context else None
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
