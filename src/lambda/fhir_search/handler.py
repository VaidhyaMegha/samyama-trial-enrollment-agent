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
FHIR_ENDPOINT = os.environ.get('FHIR_ENDPOINT', 'http://localhost:8080/fhir').rstrip('/')  # Remove trailing slash
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
def check_performance_status_criterion(patient_id: str, criterion: Dict[str, Any]) -> Dict[str, Any]:
    """
    Check performance status criteria (ECOG, Karnofsky).

    Args:
        patient_id: Patient identifier
        criterion: Parsed criterion

    Returns:
        Result with met status and evidence
    """
    # Query Observation resources for performance status
    params = {}

    # Add coding if specified (LOINC code for performance status)
    if 'coding' in criterion:
        coding = criterion['coding']
        params['code'] = f"{coding['system']}|{coding['code']}"

    bundle = query_fhir_resource('Observation', patient_id, params)

    observations = []
    if 'entry' in bundle:
        observations = [entry['resource'] for entry in bundle['entry']]

    if not observations:
        return {
            'met': False,
            'reason': 'No performance status observations found',
            'evidence': None
        }

    # Get most recent observation
    observations.sort(
        key=lambda x: x.get('effectiveDateTime', ''),
        reverse=True
    )
    latest_obs = observations[0]

    # Extract value (integer for both ECOG and Karnofsky)
    value = latest_obs.get('valueInteger')
    if value is None:
        # Try valueQuantity as fallback
        value_quantity = latest_obs.get('valueQuantity')
        if value_quantity:
            value = int(value_quantity.get('value', 0))
        else:
            return {
                'met': False,
                'reason': 'Performance status observation found but no value available',
                'evidence': {'observation': latest_obs}
            }

    # Compare based on operator
    operator = criterion['operator']
    criterion_value = criterion['value']

    met = False
    if operator == 'greater_than':
        met = value > criterion_value
    elif operator == 'less_than':
        met = value < criterion_value
    elif operator == 'between':
        met = criterion_value[0] <= value <= criterion_value[1]
    elif operator == 'equals':
        met = value == criterion_value

    # Determine scale name
    attribute = criterion.get('attribute', '').lower()
    scale_name = 'ECOG' if 'ecog' in attribute else 'Karnofsky' if 'karnofsky' in attribute else 'Performance status'

    reason = f"Patient's {scale_name} is {value}"

    return {
        'met': met,
        'reason': reason,
        'evidence': {
            'value': value,
            'criterion_value': criterion_value,
            'scale': scale_name,
            'date': latest_obs.get('effectiveDateTime'),
            'code': latest_obs.get('code', {}).get('text')
        }
    }


@tracer.capture_method
def check_medication_criterion(patient_id: str, criterion: Dict[str, Any]) -> Dict[str, Any]:
    """
    Check if patient meets a medication criterion.

    Supports:
    - Active/historical medication filtering
    - Medication name matching (fuzzy)
    - Medication class matching
    - RxNorm code matching

    Args:
        patient_id: Patient identifier
        criterion: Medication criterion

    Returns:
        Result with met status, reason, and medication evidence
    """
    try:
        # Get medication status filter (default: active)
        status_filter = criterion.get('status', 'active')

        # Query MedicationStatement
        params = {
            'subject': f'Patient/{patient_id}',
            'status': status_filter
        }

        response = query_fhir_resource('MedicationStatement', patient_id, params)

        if not response or response.get('total', 0) == 0:
            return {
                'met': False,
                'reason': f"No {status_filter} medications found",
                'evidence': None
            }

        # Extract medications
        medications = []
        entries = response.get('entry', [])

        for entry in entries:
            med_statement = entry.get('resource', {})

            # Extract medication name
            med_concept = med_statement.get('medicationCodeableConcept', {})
            med_name = med_concept.get('text', 'Unknown')

            # Extract coding
            codings = med_concept.get('coding', [])
            rxnorm_code = None
            for coding in codings:
                if 'rxnorm' in coding.get('system', '').lower():
                    rxnorm_code = coding.get('code')
                    break

            medications.append({
                'name': med_name,
                'status': med_statement.get('status', 'unknown'),
                'rxnorm_code': rxnorm_code,
                'effective_date': med_statement.get('effectiveDateTime', med_statement.get('effectivePeriod', {}).get('start'))
            })

        if not medications:
            return {
                'met': False,
                'reason': f"No medications found",
                'evidence': None
            }

        # Match medications against criterion
        search_value = criterion.get('value', '').lower()
        operator = criterion.get('operator', 'contains')

        # Check if criterion has RxNorm code
        criterion_rxnorm = None
        if 'coding' in criterion:
            criterion_rxnorm = criterion['coding'].get('code')

        matching_meds = []
        for med in medications:
            med_name_lower = med['name'].lower()

            # Match by RxNorm code (exact match)
            if criterion_rxnorm and med['rxnorm_code'] == criterion_rxnorm:
                matching_meds.append(med)
                continue

            # Match by name (fuzzy matching)
            if operator == 'contains':
                if search_value in med_name_lower or med_name_lower in search_value:
                    matching_meds.append(med)
            elif operator == 'equals':
                if search_value == med_name_lower:
                    matching_meds.append(med)
            elif operator == 'not_contains':
                # For not_contains, we check if medication should be excluded
                if search_value not in med_name_lower:
                    matching_meds.append(med)

        # Determine if criterion is met
        if operator == 'not_contains':
            # For exclusion criteria, met = True if NO matching medications found
            met = len(matching_meds) == len(medications)  # All meds don't contain the search term
            reason = f"Patient {'is not' if met else 'is'} taking {search_value}"
        else:
            # For inclusion criteria, met = True if ANY matching medication found
            met = len(matching_meds) > 0
            reason = f"Patient {'is' if met else 'is not'} taking {search_value}"

        return {
            'met': met,
            'reason': reason,
            'evidence': {
                'medication_count': len(matching_meds),
                'medications': matching_meds,
                'total_medications': len(medications)
            }
        }

    except Exception as e:
        logger.error(f"Error checking medication criterion: {str(e)}", exc_info=True)
        return {
            'met': False,
            'reason': f"Error checking medication: {str(e)}",
            'evidence': None
        }


@tracer.capture_method
def check_allergy_criterion(patient_id: str, criterion: Dict[str, Any]) -> Dict[str, Any]:
    """
    Check if patient meets an allergy criterion.

    Supports:
    - Allergy existence checks
    - Allergen name matching
    - Drug allergy filtering
    - SNOMED code matching

    Args:
        patient_id: Patient identifier
        criterion: Allergy criterion

    Returns:
        Result with met status, reason, and allergy evidence
    """
    try:
        # Query AllergyIntolerance
        params = {
            'patient': patient_id
        }

        # Add category filter if specified (e.g., "medication" for drug allergies)
        category_filter = criterion.get('category_filter')
        if category_filter:
            params['category'] = category_filter

        response = query_fhir_resource('AllergyIntolerance', patient_id, params)

        # Handle "not_exists" operator (no known allergies)
        operator = criterion.get('operator', 'contains')
        if operator == 'not_exists':
            has_allergies = response and response.get('total', 0) > 0
            return {
                'met': not has_allergies,
                'reason': f"Patient {'has' if has_allergies else 'has no'} known allergies",
                'evidence': {
                    'allergy_count': response.get('total', 0) if response else 0
                }
            }

        # No allergies found
        if not response or response.get('total', 0) == 0:
            # For "not_contains" (exclusion), this is good (met = True)
            # For "contains" (inclusion), this means criterion not met
            met = operator == 'not_contains'
            return {
                'met': met,
                'reason': "No allergies found",
                'evidence': None
            }

        # Extract allergies
        allergies = []
        entries = response.get('entry', [])

        for entry in entries:
            allergy = entry.get('resource', {})

            # Extract allergen name
            code = allergy.get('code', {})
            allergen_name = code.get('text', 'Unknown')

            # Extract coding
            codings = code.get('coding', [])
            snomed_code = None
            for coding in codings:
                if 'snomed' in coding.get('system', '').lower():
                    snomed_code = coding.get('code')
                    break

            allergies.append({
                'allergen': allergen_name,
                'type': allergy.get('type', 'unknown'),
                'category': allergy.get('category', []),
                'criticality': allergy.get('criticality', 'unknown'),
                'snomed_code': snomed_code,
                'recorded_date': allergy.get('recordedDate')
            })

        # Match allergies against criterion
        search_value = criterion.get('value', '').lower() if criterion.get('value') else ''

        # Check if criterion has SNOMED code
        criterion_snomed = None
        if 'coding' in criterion:
            criterion_snomed = criterion['coding'].get('code')

        matching_allergies = []
        for allergy in allergies:
            allergen_lower = allergy['allergen'].lower()

            # Match by SNOMED code (exact match)
            if criterion_snomed and allergy['snomed_code'] == criterion_snomed:
                matching_allergies.append(allergy)
                continue

            # Match by allergen name
            if operator == 'contains':
                if search_value in allergen_lower or allergen_lower in search_value:
                    matching_allergies.append(allergy)
            elif operator == 'equals':
                if search_value == allergen_lower:
                    matching_allergies.append(allergy)
            elif operator == 'not_contains':
                if search_value not in allergen_lower:
                    matching_allergies.append(allergy)

        # Determine if criterion is met
        if operator == 'not_contains':
            # For exclusion criteria, met = True if NO matching allergies found
            met = len(matching_allergies) == len(allergies)  # All allergies don't contain search term
            reason = f"Patient {'has no allergy' if met else 'has allergy'} to {search_value}"
        else:
            # For inclusion criteria, met = True if ANY matching allergy found
            met = len(matching_allergies) > 0
            reason = f"Patient {'has' if met else 'has no'} allergy to {search_value}"

        return {
            'met': met,
            'reason': reason,
            'evidence': {
                'allergy_count': len(matching_allergies),
                'allergies': matching_allergies,
                'total_allergies': len(allergies)
            }
        }

    except Exception as e:
        logger.error(f"Error checking allergy criterion: {str(e)}", exc_info=True)
        return {
            'met': False,
            'reason': f"Error checking allergy: {str(e)}",
            'evidence': None
        }


@tracer.capture_method
def check_simple_criterion(patient_id: str, criterion: Dict[str, Any]) -> Dict[str, Any]:
    """
    Check if patient meets a simple (leaf) criterion.

    Args:
        patient_id: Patient identifier
        criterion: Parsed simple criterion dictionary

    Returns:
        Result dictionary with met status, reason, and evidence
    """
    category = criterion.get('category')

    try:
        if category == 'demographics':
            # Get patient resource first
            patient = get_patient_resource(patient_id)
            result = check_demographic_criterion(patient, criterion)

        elif category == 'condition':
            result = check_condition_criterion(patient_id, criterion)

        elif category == 'lab_value':
            result = check_observation_criterion(patient_id, criterion)

        elif category == 'performance_status':
            result = check_performance_status_criterion(patient_id, criterion)

        elif category == 'medication':
            result = check_medication_criterion(patient_id, criterion)

        elif category == 'allergy':
            result = check_allergy_criterion(patient_id, criterion)

        else:
            result = {
                'met': False,
                'reason': f"Unsupported criterion category: {category}",
                'evidence': None
            }

        # Add criterion info to result
        result['criterion'] = {
            'type': criterion.get('type'),
            'description': criterion.get('description'),
            'category': category
        }

        return result

    except Exception as e:
        logger.error(f"Error checking simple criterion: {str(e)}", exc_info=True)
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


@tracer.capture_method
def check_criterion(patient_id: str, criterion: Dict[str, Any], depth: int = 0) -> Dict[str, Any]:
    """
    Recursively check if patient meets a criterion (simple or complex).

    Supports nested logical operators (AND, OR, NOT).

    Args:
        patient_id: Patient identifier
        criterion: Parsed criterion dictionary (simple or complex)
        depth: Current recursion depth (for limiting)

    Returns:
        Result dictionary with met status, reason, and evidence
    """
    MAX_DEPTH = 10

    # Depth limit check
    if depth > MAX_DEPTH:
        logger.error(f"Maximum recursion depth ({MAX_DEPTH}) exceeded")
        return {
            'met': False,
            'reason': f"Maximum nesting depth ({MAX_DEPTH}) exceeded",
            'evidence': None,
            'criterion': criterion
        }

    # Check if this is a complex criterion (has sub-criteria)
    if 'criteria' in criterion and criterion['criteria']:
        # Complex criterion - recursive evaluation
        logic_op = criterion.get('logic_operator', 'AND')
        sub_criteria = criterion['criteria']

        logger.info(f"Evaluating complex criterion with {logic_op} and {len(sub_criteria)} sub-criteria")

        # Evaluate all sub-criteria recursively
        sub_results = []
        for sub_criterion in sub_criteria:
            result = check_criterion(patient_id, sub_criterion, depth + 1)
            sub_results.append(result)

        # Apply logical operator
        if logic_op == 'AND':
            met = all(r['met'] for r in sub_results)
            met_count = sum(1 for r in sub_results if r['met'])
            if met:
                reason = f"All {len(sub_results)} sub-criteria met"
            else:
                reason = f"Only {met_count} of {len(sub_results)} sub-criteria met (all required)"

        elif logic_op == 'OR':
            met = any(r['met'] for r in sub_results)
            met_count = sum(1 for r in sub_results if r['met'])
            if met:
                reason = f"At least 1 of {len(sub_results)} sub-criteria met ({met_count} met)"
            else:
                reason = f"None of {len(sub_results)} sub-criteria met"

        elif logic_op == 'NOT':
            if len(sub_results) != 1:
                logger.error(f"NOT operator requires exactly 1 sub-criterion, got {len(sub_results)}")
                return {
                    'met': False,
                    'reason': f"NOT operator requires exactly 1 sub-criterion, got {len(sub_results)}",
                    'evidence': None,
                    'criterion': criterion
                }
            met = not sub_results[0]['met']
            reason = f"Negation of: {sub_results[0]['reason']}"

        else:
            logger.error(f"Unknown logic operator: {logic_op}")
            return {
                'met': False,
                'reason': f"Unknown logic operator: {logic_op}",
                'evidence': None,
                'criterion': criterion
            }

        return {
            'met': met,
            'reason': reason,
            'evidence': {
                'logic_operator': logic_op,
                'sub_results': sub_results,
                'depth': depth
            },
            'criterion': {
                'type': criterion.get('type'),
                'description': criterion.get('description'),
                'logic_operator': logic_op
            }
        }

    else:
        # Simple criterion - direct evaluation
        return check_simple_criterion(patient_id, criterion)


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
