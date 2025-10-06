"""
FHIR Search Lambda Function

Queries FHIR-compliant patient data stores (AWS HealthLake or HAPI FHIR)
to check if patients meet specific eligibility criteria.
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import boto3
import requests
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext

logger = Logger()
tracer = Tracer()

# FHIR endpoint configuration
FHIR_ENDPOINT = os.environ.get('FHIR_ENDPOINT', 'http://localhost:8080/fhir')
USE_HEALTHLAKE = os.environ.get('USE_HEALTHLAKE', 'false').lower() == 'true'

# Initialize AWS clients
if USE_HEALTHLAKE:
    healthlake_client = boto3.client('healthlake', region_name=os.environ.get('AWS_REGION', 'us-east-1'))


@tracer.capture_method
def calculate_age(birth_date_str: str) -> int:
    """
    Calculate age from FHIR birthDate.

    Args:
        birth_date_str: Date string in FHIR format (YYYY-MM-DD)

    Returns:
        Age in years
    """
    birth_date = datetime.strptime(birth_date_str, '%Y-%m-%d')
    today = datetime.now()
    age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
    return age


@tracer.capture_method
def query_fhir_resource(resource_type: str, patient_id: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Query FHIR endpoint for a specific resource type.

    Args:
        resource_type: FHIR resource type (e.g., "Patient", "Observation")
        patient_id: Patient identifier
        params: Additional query parameters

    Returns:
        FHIR Bundle response
    """
    if params is None:
        params = {}

    # Build query URL
    url = f"{FHIR_ENDPOINT}/{resource_type}"

    # Add patient reference if not querying Patient resource itself
    if resource_type != "Patient":
        params['subject'] = f"Patient/{patient_id}"

    try:
        logger.info(f"Querying FHIR: {url}", extra={"params": params})

        # Make authenticated request if using HealthLake
        if USE_HEALTHLAKE:
            from botocore.auth import SigV4Auth
            from botocore.awsrequest import AWSRequest
            from urllib.parse import urlencode

            # Build full URL with query params
            if params:
                url = f"{url}?{urlencode(params)}"

            # Create AWS request for signing
            request = AWSRequest(
                method='GET',
                url=url,
                headers={'Accept': 'application/fhir+json'}
            )

            # Sign with SigV4
            SigV4Auth(
                boto3.Session().get_credentials(),
                'healthlake',
                os.environ.get('AWS_REGION', 'us-east-1')
            ).add_auth(request)

            # Send authenticated request
            response = requests.request(
                method=request.method,
                url=request.url,
                headers=dict(request.headers),
                timeout=10
            )
        else:
            # Make standard HTTP request for non-HealthLake FHIR servers
            response = requests.get(url, params=params, timeout=10)

        response.raise_for_status()

        result = response.json()
        logger.info(f"FHIR query returned {result.get('total', 0)} results")

        return result

    except requests.exceptions.RequestException as e:
        logger.error(f"FHIR query failed: {str(e)}")
        raise


@tracer.capture_method
def get_patient_resource(patient_id: str) -> Dict[str, Any]:
    """
    Retrieve Patient resource from FHIR server.

    Args:
        patient_id: Patient identifier

    Returns:
        Patient FHIR resource
    """
    url = f"{FHIR_ENDPOINT}/Patient/{patient_id}"

    try:
        # Make authenticated request if using HealthLake
        if USE_HEALTHLAKE:
            from botocore.auth import SigV4Auth
            from botocore.awsrequest import AWSRequest

            # Create AWS request for signing
            request = AWSRequest(
                method='GET',
                url=url,
                headers={'Accept': 'application/fhir+json'}
            )

            # Sign with SigV4
            SigV4Auth(
                boto3.Session().get_credentials(),
                'healthlake',
                os.environ.get('AWS_REGION', 'us-east-1')
            ).add_auth(request)

            # Send authenticated request
            response = requests.request(
                method=request.method,
                url=request.url,
                headers=dict(request.headers),
                timeout=10
            )
        else:
            # Make standard HTTP request for non-HealthLake FHIR servers
            response = requests.get(url, timeout=10)

        response.raise_for_status()
        return response.json()

    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to retrieve patient {patient_id}: {str(e)}")
        raise


@tracer.capture_method
def check_demographic_criterion(patient: Dict[str, Any], criterion: Dict[str, Any]) -> Dict[str, Any]:
    """
    Check demographic criteria (age, gender, etc.).

    Args:
        patient: Patient FHIR resource
        criterion: Parsed criterion

    Returns:
        Result with met status and evidence
    """
    attribute = criterion['attribute'].lower()

    if attribute == 'age':
        birth_date = patient.get('birthDate')
        if not birth_date:
            return {
                'met': False,
                'reason': 'Patient birth date not found',
                'evidence': None
            }

        age = calculate_age(birth_date)
        operator = criterion['operator']
        value = criterion['value']

        met = False
        if operator == 'greater_than':
            met = age > value
        elif operator == 'less_than':
            met = age < value
        elif operator == 'between':
            met = value[0] <= age <= value[1]
        elif operator == 'equals':
            met = age == value

        return {
            'met': met,
            'reason': f"Patient age is {age} years",
            'evidence': {
                'birthDate': birth_date,
                'calculated_age': age,
                'criterion_value': value
            }
        }

    elif attribute == 'gender':
        patient_gender = patient.get('gender', '').lower()
        criterion_gender = str(criterion['value']).lower()

        met = patient_gender == criterion_gender

        return {
            'met': met,
            'reason': f"Patient gender is {patient_gender}",
            'evidence': {
                'patient_gender': patient_gender,
                'criterion_gender': criterion_gender
            }
        }

    else:
        return {
            'met': False,
            'reason': f"Unknown demographic attribute: {attribute}",
            'evidence': None
        }


@tracer.capture_method
def check_condition_criterion(patient_id: str, criterion: Dict[str, Any]) -> Dict[str, Any]:
    """
    Check condition/diagnosis criteria.

    Args:
        patient_id: Patient identifier
        criterion: Parsed criterion

    Returns:
        Result with met status and evidence
    """
    # Query Condition resources for patient
    params = {}

    # Add coding if specified
    if 'coding' in criterion:
        coding = criterion['coding']
        params['code'] = f"{coding['system']}|{coding['code']}"

    bundle = query_fhir_resource('Condition', patient_id, params)

    conditions = []
    if 'entry' in bundle:
        conditions = [entry['resource'] for entry in bundle['entry']]

    operator = criterion['operator']
    value = str(criterion['value']).lower()

    # Check if condition exists
    has_condition = len(conditions) > 0

    if operator == 'contains' or operator == 'equals':
        met = has_condition
        reason = f"Patient has {len(conditions)} matching condition(s)" if has_condition else "No matching conditions found"

    elif operator == 'not_contains':
        met = not has_condition
        reason = "No matching conditions found" if met else f"Patient has {len(conditions)} matching condition(s)"

    else:
        met = False
        reason = f"Unsupported operator for conditions: {operator}"

    return {
        'met': met,
        'reason': reason,
        'evidence': {
            'condition_count': len(conditions),
            'conditions': [
                {
                    'code': c.get('code', {}).get('text', 'Unknown'),
                    'clinicalStatus': c.get('clinicalStatus', {}).get('coding', [{}])[0].get('code')
                }
                for c in conditions[:5]  # Limit to first 5 for brevity
            ]
        }
    }


@tracer.capture_method
def check_observation_criterion(patient_id: str, criterion: Dict[str, Any]) -> Dict[str, Any]:
    """
    Check lab value / observation criteria.

    Args:
        patient_id: Patient identifier
        criterion: Parsed criterion

    Returns:
        Result with met status and evidence
    """
    # Query Observation resources for patient
    params = {}

    # Add coding if specified (e.g., LOINC code for lab tests)
    if 'coding' in criterion:
        coding = criterion['coding']
        params['code'] = f"{coding['system']}|{coding['code']}"

    # Get recent observations (last 1 year)
    # date_param = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
    # params['date'] = f"ge{date_param}"

    bundle = query_fhir_resource('Observation', patient_id, params)

    observations = []
    if 'entry' in bundle:
        observations = [entry['resource'] for entry in bundle['entry']]

    if not observations:
        return {
            'met': False,
            'reason': 'No matching observations found',
            'evidence': None
        }

    # Get most recent observation
    # Sort by date (if available)
    observations.sort(
        key=lambda x: x.get('effectiveDateTime', ''),
        reverse=True
    )
    latest_obs = observations[0]

    # Extract value
    value_quantity = latest_obs.get('valueQuantity')
    if not value_quantity:
        return {
            'met': False,
            'reason': 'Observation found but no value available',
            'evidence': {'observation': latest_obs}
        }

    obs_value = value_quantity.get('value')
    obs_unit = value_quantity.get('unit', '')

    # Compare based on operator
    operator = criterion['operator']
    criterion_value = criterion['value']

    met = False
    if operator == 'greater_than':
        met = obs_value > criterion_value
    elif operator == 'less_than':
        met = obs_value < criterion_value
    elif operator == 'between':
        met = criterion_value[0] <= obs_value <= criterion_value[1]
    elif operator == 'equals':
        met = obs_value == criterion_value

    reason = f"Patient's {criterion['attribute']} is {obs_value}{obs_unit}"

    return {
        'met': met,
        'reason': reason,
        'evidence': {
            'value': obs_value,
            'unit': obs_unit,
            'criterion_value': criterion_value,
            'date': latest_obs.get('effectiveDateTime'),
            'code': latest_obs.get('code', {}).get('text')
        }
    }


@tracer.capture_method
def check_criterion(patient_id: str, criterion: Dict[str, Any]) -> Dict[str, Any]:
    """
    Check if patient meets a specific criterion.

    Args:
        patient_id: Patient identifier
        criterion: Parsed criterion dictionary

    Returns:
        Result dictionary with met status, reason, and evidence
    """
    category = criterion['category']

    try:
        if category == 'demographics':
            # Get patient resource first
            patient = get_patient_resource(patient_id)
            result = check_demographic_criterion(patient, criterion)

        elif category == 'condition':
            result = check_condition_criterion(patient_id, criterion)

        elif category == 'lab_value':
            result = check_observation_criterion(patient_id, criterion)

        else:
            result = {
                'met': False,
                'reason': f"Unsupported criterion category: {category}",
                'evidence': None
            }

        # Add criterion info to result
        result['criterion'] = {
            'type': criterion['type'],
            'description': criterion['description'],
            'category': category
        }

        return result

    except Exception as e:
        logger.error(f"Error checking criterion: {str(e)}", exc_info=True)
        return {
            'met': False,
            'reason': f"Error checking criterion: {str(e)}",
            'evidence': None,
            'criterion': {
                'type': criterion.get('type'),
                'description': criterion.get('description'),
                'category': category
            }
        }


@logger.inject_lambda_context(log_event=True)
@tracer.capture_lambda_handler
def lambda_handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    Lambda handler for FHIR search.

    Expected event format:
    {
        "patient_id": "patient-123",
        "criterion": {...parsed criterion...}
        OR
        "criteria": [...list of criteria...]
    }

    Returns:
    {
        "statusCode": 200,
        "body": {
            "patient_id": "...",
            "results": [...],
            "eligible": true/false
        }
    }
    """
    try:
        # Extract input
        if 'body' in event:
            body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
        else:
            body = event

        patient_id = body.get('patient_id')
        if not patient_id:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Missing required field: patient_id'
                })
            }

        # Check single criterion or multiple
        if 'criterion' in body:
            criteria = [body['criterion']]
        elif 'criteria' in body:
            criteria = body['criteria']
        else:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Missing required field: criterion or criteria'
                })
            }

        logger.info(f"Checking {len(criteria)} criteria for patient {patient_id}")

        # Check each criterion
        results = []
        for criterion in criteria:
            result = check_criterion(patient_id, criterion)
            results.append(result)

        # Determine overall eligibility
        # Patient is eligible if:
        # - All inclusion criteria are met
        # - No exclusion criteria are met
        eligible = True
        failed_criteria = []

        for result in results:
            criterion_type = result['criterion']['type']

            if criterion_type == 'inclusion' and not result['met']:
                eligible = False
                failed_criteria.append(result)

            elif criterion_type == 'exclusion' and result['met']:
                eligible = False
                failed_criteria.append(result)

        # Prepare response
        response_body = {
            'patient_id': patient_id,
            'eligible': eligible,
            'results': results,
            'summary': {
                'total_criteria': len(results),
                'inclusion_met': sum(1 for r in results if r['criterion']['type'] == 'inclusion' and r['met']),
                'exclusion_violated': sum(1 for r in results if r['criterion']['type'] == 'exclusion' and r['met']),
                'failed_criteria_count': len(failed_criteria)
            },
            'failed_criteria': failed_criteria if not eligible else []
        }

        logger.info(f"Patient {patient_id} eligibility: {eligible}")

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
                'message': 'Failed to check criteria'
            })
        }
