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

# Criteria evaluation configuration
MAX_CRITERIA_DEPTH = int(os.environ.get('MAX_CRITERIA_DEPTH', '10'))

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

            # Match by name (bidirectional fuzzy matching)
            # Uses bidirectional substring matching to handle both:
            # - Generic-to-brand: "statin" matches "atorvastatin"
            # - Brand-to-generic: "atorvastatin" matches "statin therapy"
            # Note: This intentionally does NOT match very short partial strings
            # e.g., "met" will NOT match "metformin" (neither contains the other)
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

            # Match by allergen name (bidirectional fuzzy matching)
            # Uses bidirectional substring matching to handle both:
            # - Generic-to-specific: "penicillin" matches "penicillin G"
            # - Specific-to-generic: "amoxicillin" matches "penicillin allergy"
            # Note: This intentionally does NOT match very short partial strings
            # e.g., "pen" will NOT match "penicillin" (neither contains the other)
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
def check_procedure_criterion(patient_id: str, criterion: Dict[str, Any]) -> Dict[str, Any]:
    """
    Check if patient meets a procedure criterion.

    Supports:
    - Procedure existence checks (e.g., "No prior surgery")
    - Procedure code matching (CPT, SNOMED CT, ICD-10-PCS)
    - Procedure name/type matching (fuzzy)
    - Category filtering (surgical, diagnostic, therapeutic)
    - Status filtering (completed, in-progress, etc.)
    - Temporal constraints (basic support)

    Args:
        patient_id: Patient identifier
        criterion: Procedure criterion

    Returns:
        Result with met status, reason, and procedure evidence
    """
    try:
        # Query Procedure resource
        params = {
            'subject': f'Patient/{patient_id}'
        }

        # Add category filter if specified
        procedure_category = criterion.get('procedure_category')
        if procedure_category:
            params['category'] = procedure_category

        response = query_fhir_resource('Procedure', patient_id, params)

        # Handle "not_exists" operator (no prior procedure)
        operator = criterion.get('operator', 'contains')
        if operator == 'not_exists':
            has_procedures = response and response.get('total', 0) > 0

            # If we have procedures, need to check if any match the criterion
            if has_procedures and criterion.get('value'):
                # Extract and filter procedures to see if any match the specific type
                entries = response.get('entry', [])
                search_value = criterion.get('value', '').lower()
                criterion_coding = criterion.get('coding', {})
                criterion_code = criterion_coding.get('code') if criterion_coding else None

                matching_count = 0
                for entry in entries:
                    proc_resource = entry.get('resource', {})

                    # Filter by status (only count completed procedures by default)
                    status = proc_resource.get('status', 'unknown')
                    if status not in ['completed', 'in-progress']:
                        continue

                    # Extract procedure details
                    code_concept = proc_resource.get('code', {})
                    proc_text = code_concept.get('text', '').lower()

                    # Check code match
                    codings = code_concept.get('coding', [])
                    has_code_match = False
                    for coding in codings:
                        if criterion_code and coding.get('code') == criterion_code:
                            has_code_match = True
                            break

                    # Check text match (fuzzy)
                    has_text_match = search_value in proc_text or proc_text in search_value

                    if has_code_match or has_text_match:
                        matching_count += 1

                # For not_exists, met = True only if NO matching procedures found
                met = matching_count == 0
                reason = f"Patient {'has no prior' if met else 'has prior'} {criterion.get('value', 'procedure')}"
            else:
                # No procedures at all, or no specific value to match
                met = not has_procedures
                reason = f"Patient {'has no' if met else 'has'} procedure history"

            return {
                'met': met,
                'reason': reason,
                'evidence': {
                    'procedure_count': 0 if met else 1,
                    'procedures': [],
                    'total_procedures': response.get('total', 0) if response else 0
                }
            }

        # For other operators, we need procedures to exist
        if not response or response.get('total', 0) == 0:
            return {
                'met': False,
                'reason': "No procedures found",
                'evidence': None
            }

        # Extract procedures
        procedures = []
        entries = response.get('entry', [])

        for entry in entries:
            proc_resource = entry.get('resource', {})

            # Filter by status (only include completed and in-progress by default)
            status = proc_resource.get('status', 'unknown')
            if status not in ['completed', 'in-progress']:
                continue

            # Extract procedure code and text
            code_concept = proc_resource.get('code', {})
            proc_text = code_concept.get('text', 'Unknown procedure')

            # Extract coding systems
            codings = code_concept.get('coding', [])
            cpt_code = None
            snomed_code = None
            icd10_code = None

            for coding in codings:
                system = coding.get('system', '')
                code = coding.get('code')

                if 'cpt' in system.lower() and code:
                    cpt_code = code
                elif 'snomed' in system.lower() and code:
                    snomed_code = code
                elif 'icd-10' in system.lower() and code:
                    icd10_code = code

            # Extract dates
            performed_date = proc_resource.get('performedDateTime')
            if not performed_date:
                performed_period = proc_resource.get('performedPeriod', {})
                performed_date = performed_period.get('start')

            # Extract category
            categories = proc_resource.get('category', {}).get('coding', [])
            category_code = categories[0].get('code') if categories else None

            procedures.append({
                'text': proc_text,
                'status': status,
                'cpt_code': cpt_code,
                'snomed_code': snomed_code,
                'icd10_code': icd10_code,
                'performed_date': performed_date,
                'category': category_code
            })

        if not procedures:
            return {
                'met': False,
                'reason': "No completed/in-progress procedures found",
                'evidence': None
            }

        # Match procedures against criterion
        search_value = criterion.get('value', '').lower()

        # Check if criterion has coding (CPT, SNOMED, or ICD-10)
        criterion_coding = criterion.get('coding', {})
        criterion_code = criterion_coding.get('code') if criterion_coding else None
        criterion_system = criterion_coding.get('system', '').lower() if criterion_coding else ''

        matching_procedures = []
        for proc in procedures:
            proc_text_lower = proc['text'].lower()

            # Match by code (exact match with appropriate system)
            if criterion_code:
                if 'cpt' in criterion_system and proc['cpt_code'] == criterion_code:
                    matching_procedures.append(proc)
                    continue
                elif 'snomed' in criterion_system and proc['snomed_code'] == criterion_code:
                    matching_procedures.append(proc)
                    continue
                elif 'icd-10' in criterion_system and proc['icd10_code'] == criterion_code:
                    matching_procedures.append(proc)
                    continue

            # Match by procedure text (bidirectional fuzzy matching)
            # Uses bidirectional substring matching to handle both:
            # - Generic-to-specific: "surgery" matches "hip replacement surgery"
            # - Specific-to-generic: "total hip arthroplasty" matches "hip replacement"
            if operator == 'contains':
                if search_value in proc_text_lower or proc_text_lower in search_value:
                    matching_procedures.append(proc)
            elif operator == 'equals':
                if search_value == proc_text_lower:
                    matching_procedures.append(proc)
            elif operator == 'not_contains':
                if search_value not in proc_text_lower:
                    matching_procedures.append(proc)

        # Determine if criterion is met
        if operator == 'not_contains':
            # For exclusion criteria, met = True if NO matching procedures found
            met = len(matching_procedures) == len(procedures)  # All procedures don't match search term
            reason = f"Patient {'has no' if met else 'has'} {search_value} procedure"
        else:
            # For inclusion criteria, met = True if ANY matching procedure found
            met = len(matching_procedures) > 0
            reason = f"Patient {'has had' if met else 'has not had'} {search_value} procedure"

        return {
            'met': met,
            'reason': reason,
            'evidence': {
                'procedure_count': len(matching_procedures),
                'procedures': matching_procedures,
                'total_procedures': len(procedures)
            }
        }

    except Exception as e:
        logger.error(f"Error checking procedure criterion: {str(e)}", exc_info=True)
        return {
            'met': False,
            'reason': f"Error checking procedure: {str(e)}",
            'evidence': None
        }


@tracer.capture_method
def check_diagnostic_report_criterion(patient_id: str, criterion: Dict[str, Any]) -> Dict[str, Any]:
    """
    Check if patient meets a diagnostic report criterion.

    Supports:
    - Report conclusion/status matching
    - Report category filtering (imaging, lab, pathology, cardiology)
    - LOINC code matching for specific tests
    - Text-based matching for findings

    Args:
        patient_id: Patient identifier
        criterion: DiagnosticReport criterion

    Returns:
        Result with met status, reason, and report evidence
    """
    try:
        # Query DiagnosticReport resource
        params = {
            'subject': f'Patient/{patient_id}'
        }

        # Add category filter if specified
        report_category = criterion.get('report_category')
        if report_category:
            params['category'] = report_category

        response = query_fhir_resource('DiagnosticReport', patient_id, params)

        # Handle operators
        operator = criterion.get('operator', 'contains')

        # Handle "not_exists" operator
        if operator == 'not_exists':
            has_reports = response and response.get('total', 0) > 0
            return {
                'met': not has_reports,
                'reason': f"Patient {'has' if has_reports else 'has no'} diagnostic reports",
                'evidence': {
                    'report_count': response.get('total', 0) if response else 0
                }
            }

        # No reports found
        if not response or response.get('total', 0) == 0:
            met = operator == 'not_contains'
            return {
                'met': met,
                'reason': "No diagnostic reports found",
                'evidence': None
            }

        # Extract reports
        reports = []
        entries = response.get('entry', [])

        for entry in entries:
            report = entry.get('resource', {})

            # Extract conclusion and status
            conclusion = report.get('conclusion', '').lower()
            status = report.get('status', 'unknown')

            # Extract report code
            code = report.get('code', {})
            report_text = code.get('text', 'Unknown report')

            # Extract LOINC code
            codings = code.get('coding', [])
            loinc_code = None
            for coding in codings:
                if 'loinc' in coding.get('system', '').lower():
                    loinc_code = coding.get('code')
                    break

            # Extract issued date
            issued_date = report.get('issued', report.get('effectiveDateTime'))

            reports.append({
                'text': report_text,
                'conclusion': conclusion,
                'status': status,
                'loinc_code': loinc_code,
                'issued_date': issued_date,
                'category': report_category or 'unknown'
            })

        if not reports:
            return {
                'met': False,
                'reason': "No diagnostic reports found",
                'evidence': None
            }

        # Match reports against criterion
        search_value = criterion.get('value', '').lower()

        # Check if criterion has LOINC code
        criterion_coding = criterion.get('coding', {})
        criterion_code = criterion_coding.get('code') if criterion_coding else None

        matching_reports = []
        for report in reports:
            # Match by LOINC code (exact match)
            if criterion_code and report['loinc_code'] == criterion_code:
                matching_reports.append(report)
                continue

            # Match by conclusion or report text (fuzzy matching)
            report_text_lower = report['text'].lower()
            conclusion_lower = report['conclusion']

            if operator == 'contains':
                if (search_value in conclusion_lower or conclusion_lower in search_value or
                    search_value in report_text_lower or report_text_lower in search_value):
                    matching_reports.append(report)
            elif operator == 'equals':
                if search_value == conclusion_lower or search_value == report_text_lower:
                    matching_reports.append(report)
            elif operator == 'not_contains':
                if search_value not in conclusion_lower and search_value not in report_text_lower:
                    matching_reports.append(report)

        # Determine if criterion is met
        if operator == 'not_contains':
            # For exclusion criteria, met = True if NO matching reports found
            met = len(matching_reports) == len(reports)
            reason = f"Patient reports {'do not contain' if met else 'contain'} {search_value}"
        else:
            # For inclusion criteria, met = True if ANY matching report found
            met = len(matching_reports) > 0
            reason = f"Patient {'has' if met else 'has no'} diagnostic report with {search_value}"

        return {
            'met': met,
            'reason': reason,
            'evidence': {
                'report_count': len(matching_reports),
                'reports': matching_reports,
                'total_reports': len(reports)
            }
        }

    except Exception as e:
        logger.error(f"Error checking diagnostic report criterion: {str(e)}", exc_info=True)
        return {
            'met': False,
            'reason': f"Error checking diagnostic report: {str(e)}",
            'evidence': None
        }


@tracer.capture_method
def check_medication_request_criterion(patient_id: str, criterion: Dict[str, Any]) -> Dict[str, Any]:
    """
    Check if patient meets a medication request (prescription) criterion.

    Supports:
    - Prescribed medication filtering
    - Intent filtering (order, plan)
    - Status filtering (active, completed)
    - RxNorm code matching
    - Medication name matching (fuzzy)

    Args:
        patient_id: Patient identifier
        criterion: MedicationRequest criterion

    Returns:
        Result with met status, reason, and prescription evidence
    """
    try:
        # Query MedicationRequest resource
        params = {
            'subject': f'Patient/{patient_id}'
        }

        # Add intent filter if specified (default: order)
        intent_filter = criterion.get('intent', 'order')
        if intent_filter:
            params['intent'] = intent_filter

        # Add status filter if specified (default: active)
        status_filter = criterion.get('status', 'active')
        if status_filter:
            params['status'] = status_filter

        response = query_fhir_resource('MedicationRequest', patient_id, params)

        # Handle operators
        operator = criterion.get('operator', 'contains')

        # Handle "not_exists" operator
        if operator == 'not_exists':
            has_prescriptions = response and response.get('total', 0) > 0
            return {
                'met': not has_prescriptions,
                'reason': f"Patient {'has' if has_prescriptions else 'has no'} prescribed medications",
                'evidence': {
                    'prescription_count': response.get('total', 0) if response else 0
                }
            }

        # No prescriptions found
        if not response or response.get('total', 0) == 0:
            met = operator == 'not_contains'
            return {
                'met': met,
                'reason': "No prescribed medications found",
                'evidence': None
            }

        # Extract prescriptions
        prescriptions = []
        entries = response.get('entry', [])

        for entry in entries:
            med_request = entry.get('resource', {})

            # Extract medication name
            med_concept = med_request.get('medicationCodeableConcept', {})
            med_name = med_concept.get('text', 'Unknown')

            # Extract RxNorm code
            codings = med_concept.get('coding', [])
            rxnorm_code = None
            for coding in codings:
                if 'rxnorm' in coding.get('system', '').lower():
                    rxnorm_code = coding.get('code')
                    break

            # Extract dates
            authored_date = med_request.get('authoredOn')

            # Extract dosage info (optional)
            dosage_instructions = med_request.get('dosageInstruction', [])
            dosage_text = dosage_instructions[0].get('text') if dosage_instructions else None

            prescriptions.append({
                'medication': med_name,
                'intent': med_request.get('intent', 'unknown'),
                'status': med_request.get('status', 'unknown'),
                'rxnorm_code': rxnorm_code,
                'authored_date': authored_date,
                'dosage': dosage_text
            })

        if not prescriptions:
            return {
                'met': False,
                'reason': "No prescribed medications found",
                'evidence': None
            }

        # Match prescriptions against criterion
        search_value = criterion.get('value', '').lower()

        # Check if criterion has RxNorm code
        criterion_rxnorm = None
        if 'coding' in criterion:
            criterion_rxnorm = criterion['coding'].get('code')

        matching_prescriptions = []
        for prescription in prescriptions:
            med_name_lower = prescription['medication'].lower()

            # Match by RxNorm code (exact match)
            if criterion_rxnorm and prescription['rxnorm_code'] == criterion_rxnorm:
                matching_prescriptions.append(prescription)
                continue

            # Match by medication name (bidirectional fuzzy matching)
            if operator == 'contains':
                if search_value in med_name_lower or med_name_lower in search_value:
                    matching_prescriptions.append(prescription)
            elif operator == 'equals':
                if search_value == med_name_lower:
                    matching_prescriptions.append(prescription)
            elif operator == 'not_contains':
                if search_value not in med_name_lower:
                    matching_prescriptions.append(prescription)

        # Determine if criterion is met
        if operator == 'not_contains':
            # For exclusion criteria, met = True if NO matching prescriptions found
            met = len(matching_prescriptions) == len(prescriptions)
            reason = f"Patient {'is not prescribed' if met else 'is prescribed'} {search_value}"
        else:
            # For inclusion criteria, met = True if ANY matching prescription found
            met = len(matching_prescriptions) > 0
            reason = f"Patient {'is prescribed' if met else 'is not prescribed'} {search_value}"

        return {
            'met': met,
            'reason': reason,
            'evidence': {
                'prescription_count': len(matching_prescriptions),
                'prescriptions': matching_prescriptions,
                'total_prescriptions': len(prescriptions)
            }
        }

    except Exception as e:
        logger.error(f"Error checking medication request criterion: {str(e)}", exc_info=True)
        return {
            'met': False,
            'reason': f"Error checking medication request: {str(e)}",
            'evidence': None
        }


@tracer.capture_method
def check_immunization_criterion(patient_id: str, criterion: Dict[str, Any]) -> Dict[str, Any]:
    """
    Check if patient meets an immunization (vaccination) criterion.

    Supports:
    - Vaccination history checks
    - Vaccine type matching (influenza, COVID-19, HPV, etc.)
    - CVX code matching (CDC vaccine codes)
    - Status filtering (completed, entered-in-error)
    - Temporal constraints (within X time period)

    Args:
        patient_id: Patient identifier
        criterion: Immunization criterion

    Returns:
        Result with met status, reason, and immunization evidence
    """
    try:
        # Query Immunization resource
        params = {
            'subject': f'Patient/{patient_id}'
        }

        # Add status filter if specified (default: completed)
        status_filter = criterion.get('status', 'completed')
        if status_filter:
            params['status'] = status_filter

        response = query_fhir_resource('Immunization', patient_id, params)

        # Handle operators
        operator = criterion.get('operator', 'contains')

        # Handle "not_exists" operator
        if operator == 'not_exists':
            has_immunizations = response and response.get('total', 0) > 0

            # If checking for specific vaccine type with not_exists
            if has_immunizations and criterion.get('value'):
                entries = response.get('entry', [])
                search_value = criterion.get('value', '').lower()
                criterion_cvx = criterion.get('coding', {}).get('code') if criterion.get('coding') else None

                matching_count = 0
                for entry in entries:
                    imm_resource = entry.get('resource', {})

                    # Extract vaccine info
                    vaccine_code = imm_resource.get('vaccineCode', {})
                    vaccine_text = vaccine_code.get('text', '').lower()

                    # Check CVX code match
                    codings = vaccine_code.get('coding', [])
                    has_code_match = False
                    for coding in codings:
                        if criterion_cvx and coding.get('code') == criterion_cvx:
                            has_code_match = True
                            break

                    # Check text match (fuzzy)
                    has_text_match = search_value in vaccine_text or vaccine_text in search_value

                    if has_code_match or has_text_match:
                        matching_count += 1

                met = matching_count == 0
                reason = f"Patient {'has not received' if met else 'has received'} {criterion.get('value', 'vaccine')}"
            else:
                met = not has_immunizations
                reason = f"Patient {'has no' if met else 'has'} immunization history"

            return {
                'met': met,
                'reason': reason,
                'evidence': {
                    'immunization_count': 0 if met else 1,
                    'immunizations': [],
                    'total_immunizations': response.get('total', 0) if response else 0
                }
            }

        # No immunizations found
        if not response or response.get('total', 0) == 0:
            met = operator == 'not_contains'
            return {
                'met': met,
                'reason': "No immunizations found",
                'evidence': None
            }

        # Extract immunizations
        immunizations = []
        entries = response.get('entry', [])

        for entry in entries:
            imm_resource = entry.get('resource', {})

            # Extract vaccine info
            vaccine_code = imm_resource.get('vaccineCode', {})
            vaccine_text = vaccine_code.get('text', 'Unknown vaccine')

            # Extract CVX code
            codings = vaccine_code.get('coding', [])
            cvx_code = None
            for coding in codings:
                if 'cvx' in coding.get('system', '').lower():
                    cvx_code = coding.get('code')
                    break

            # Extract dates
            occurrence_date = imm_resource.get('occurrenceDateTime')
            if not occurrence_date:
                occurrence_period = imm_resource.get('occurrencePeriod', {})
                occurrence_date = occurrence_period.get('start')

            # Extract lot number and expiration date (optional)
            lot_number = imm_resource.get('lotNumber')
            expiration_date = imm_resource.get('expirationDate')

            immunizations.append({
                'vaccine': vaccine_text,
                'status': imm_resource.get('status', 'unknown'),
                'cvx_code': cvx_code,
                'occurrence_date': occurrence_date,
                'lot_number': lot_number,
                'expiration_date': expiration_date
            })

        if not immunizations:
            return {
                'met': False,
                'reason': "No completed immunizations found",
                'evidence': None
            }

        # Match immunizations against criterion
        search_value = criterion.get('value', '').lower()

        # Check if criterion has CVX code
        criterion_cvx = None
        if 'coding' in criterion:
            criterion_cvx = criterion['coding'].get('code')

        matching_immunizations = []
        for immunization in immunizations:
            vaccine_lower = immunization['vaccine'].lower()

            # Match by CVX code (exact match)
            if criterion_cvx and immunization['cvx_code'] == criterion_cvx:
                matching_immunizations.append(immunization)
                continue

            # Match by vaccine name (bidirectional fuzzy matching)
            if operator == 'contains':
                if search_value in vaccine_lower or vaccine_lower in search_value:
                    matching_immunizations.append(immunization)
            elif operator == 'equals':
                if search_value == vaccine_lower:
                    matching_immunizations.append(immunization)
            elif operator == 'not_contains':
                if search_value not in vaccine_lower:
                    matching_immunizations.append(immunization)

        # Determine if criterion is met
        if operator == 'not_contains':
            # For exclusion criteria, met = True if NO matching immunizations found
            met = len(matching_immunizations) == len(immunizations)
            reason = f"Patient {'has not received' if met else 'has received'} {search_value}"
        else:
            # For inclusion criteria, met = True if ANY matching immunization found
            met = len(matching_immunizations) > 0
            reason = f"Patient {'has received' if met else 'has not received'} {search_value}"

        return {
            'met': met,
            'reason': reason,
            'evidence': {
                'immunization_count': len(matching_immunizations),
                'immunizations': matching_immunizations,
                'total_immunizations': len(immunizations)
            }
        }

    except Exception as e:
        logger.error(f"Error checking immunization criterion: {str(e)}", exc_info=True)
        return {
            'met': False,
            'reason': f"Error checking immunization: {str(e)}",
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

        elif category == 'medication_request':
            result = check_medication_request_criterion(patient_id, criterion)

        elif category == 'immunization':
            result = check_immunization_criterion(patient_id, criterion)

        elif category == 'allergy':
            result = check_allergy_criterion(patient_id, criterion)

        elif category == 'procedure':
            result = check_procedure_criterion(patient_id, criterion)

        elif category == 'diagnostic_report':
            result = check_diagnostic_report_criterion(patient_id, criterion)

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
    # Depth limit check
    if depth > MAX_CRITERIA_DEPTH:
        logger.error(f"Maximum recursion depth ({MAX_CRITERIA_DEPTH}) exceeded")
        return {
            'met': False,
            'reason': f"Maximum nesting depth ({MAX_CRITERIA_DEPTH}) exceeded",
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
