"""
Patient Manager Lambda Function

Manages patient data operations for the CRC persona:
- List all patients from HealthLake
- Search patients by demographics
- Create new patients with all FHIR resources
- Update patient data
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
import boto3
import requests
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from urllib.parse import urlencode
import uuid

logger = Logger()
tracer = Tracer()

# FHIR endpoint configuration
FHIR_ENDPOINT = os.environ.get('FHIR_ENDPOINT', '').rstrip('/')
USE_HEALTHLAKE = os.environ.get('USE_HEALTHLAKE', 'false').lower() == 'true'

def cors_headers() -> Dict[str, str]:
    return {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,Authorization,X-Requested-With',
        'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
    }

@tracer.capture_method
def query_fhir(resource_type: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Query FHIR endpoint with SigV4 authentication.

    Args:
        resource_type: FHIR resource type
        params: Query parameters

    Returns:
        FHIR Bundle response
    """
    if params is None:
        params = {}

    url = f"{FHIR_ENDPOINT}/{resource_type}"

    try:
        if USE_HEALTHLAKE:
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
            # Standard HTTP request
            response = requests.get(url, params=params, timeout=10)

        response.raise_for_status()
        return response.json()

    except requests.exceptions.RequestException as e:
        logger.error(f"FHIR query failed: {str(e)}")
        raise

@tracer.capture_method
def create_fhir_resource(resource: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a FHIR resource in HealthLake.

    Args:
        resource: FHIR resource to create

    Returns:
        Created resource with ID
    """
    resource_type = resource.get('resourceType')
    if not resource_type:
        raise ValueError("Resource must have resourceType")

    url = f"{FHIR_ENDPOINT}/{resource_type}"

    try:
        if USE_HEALTHLAKE:
            # Create AWS request for signing
            request = AWSRequest(
                method='POST',
                url=url,
                data=json.dumps(resource),
                headers={
                    'Accept': 'application/fhir+json',
                    'Content-Type': 'application/fhir+json'
                }
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
                data=request.body,
                timeout=10
            )
        else:
            # Standard HTTP request
            response = requests.post(
                url,
                json=resource,
                headers={'Content-Type': 'application/fhir+json'},
                timeout=10
            )

        response.raise_for_status()
        return response.json()

    except requests.exceptions.RequestException as e:
        logger.error(f"FHIR create failed: {str(e)}")
        raise

@tracer.capture_method
def list_patients(search_params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    List all patients from HealthLake.

    Args:
        search_params: Optional search parameters (name, birthdate, gender, etc.)

    Returns:
        List of patients with demographics
    """
    params = search_params or {}
    params['_count'] = params.get('_count', 100)  # Default 100 patients per page

    bundle = query_fhir('Patient', params)

    patients = []
    if 'entry' in bundle:
        for entry in bundle['entry']:
            patient_resource = entry['resource']

            # Calculate age from birthDate
            birth_date_str = patient_resource.get('birthDate')
            age = None
            if birth_date_str:
                birth_date = datetime.strptime(birth_date_str, '%Y-%m-%d')
                today = datetime.now()
                age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))

            # Extract name
            name_parts = patient_resource.get('name', [{}])[0]
            given_name = ' '.join(name_parts.get('given', []))
            family_name = name_parts.get('family', '')
            full_name = f"{given_name} {family_name}".strip() or "Unknown"

            patients.append({
                'id': patient_resource.get('id'),
                'name': full_name,
                'gender': patient_resource.get('gender', 'unknown'),
                'birthDate': birth_date_str,
                'age': age,
                'identifier': patient_resource.get('identifier', [])
            })

    return {
        'total': bundle.get('total', len(patients)),
        'patients': patients
    }

@tracer.capture_method
def get_patient_by_id(patient_id: str) -> Dict[str, Any]:
    """
    Get a specific patient by ID with all associated FHIR resources.

    Args:
        patient_id: Patient FHIR ID

    Returns:
        Patient data with all FHIR resources
    """
    try:
        # Get patient resource
        patient_bundle = query_fhir('Patient', {'_id': patient_id})

        if 'entry' not in patient_bundle or len(patient_bundle['entry']) == 0:
            return {
                'success': False,
                'error': 'Patient not found'
            }

        patient_resource = patient_bundle['entry'][0]['resource']

        # Calculate age from birthDate
        birth_date_str = patient_resource.get('birthDate')
        age = None
        if birth_date_str:
            birth_date = datetime.strptime(birth_date_str, '%Y-%m-%d')
            today = datetime.now()
            age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))

        # Extract name
        name_parts = patient_resource.get('name', [{}])[0]
        given_name = ' '.join(name_parts.get('given', []))
        family_name = name_parts.get('family', '')
        full_name = f"{given_name} {family_name}".strip() or "Unknown"

        patient_data = {
            'id': patient_resource.get('id'),
            'name': full_name,
            'gender': patient_resource.get('gender', 'unknown'),
            'birthDate': birth_date_str,
            'age': age,
            'identifier': patient_resource.get('identifier', [])
        }

        # Query all related FHIR resources for this patient
        resource_types = [
            'Condition',
            'Observation',
            'MedicationStatement',
            'AllergyIntolerance',
            'Procedure',
            'Immunization',
            'FamilyMemberHistory',
            'Encounter',
            'DiagnosticReport'
        ]

        for resource_type in resource_types:
            try:
                bundle = query_fhir(resource_type, {'patient': patient_id, '_count': 100})
                resources = []
                if 'entry' in bundle:
                    for entry in bundle['entry']:
                        resources.append(entry['resource'])

                # Store with lowercase plural key
                key = resource_type.lower() + 's' if not resource_type.endswith('y') else resource_type.lower()[:-1] + 'ies'
                if resource_type == 'FamilyMemberHistory':
                    key = 'familyHistory'
                patient_data[key] = resources
            except Exception as e:
                logger.warning(f"Failed to fetch {resource_type} for patient {patient_id}: {str(e)}")
                patient_data[resource_type.lower() + 's'] = []

        return {
            'success': True,
            'patient': patient_data
        }

    except Exception as e:
        logger.error(f"Error fetching patient {patient_id}: {str(e)}", exc_info=True)
        return {
            'success': False,
            'error': str(e)
        }

@tracer.capture_method
def create_patient_with_resources(patient_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a new patient with all associated FHIR resources.

    Args:
        patient_data: Patient data including demographics and clinical info

    Returns:
        Created patient ID and status
    """
    created_resources = []

    try:
        # 1. Create Patient resource
        patient_resource = {
            'resourceType': 'Patient',
            'name': [{
                'given': patient_data.get('given_name', '').split(),
                'family': patient_data.get('family_name', '')
            }],
            'gender': patient_data.get('gender', 'unknown'),
            'birthDate': patient_data.get('birth_date')
        }

        created_patient = create_fhir_resource(patient_resource)
        patient_id = created_patient['id']
        created_resources.append({'type': 'Patient', 'id': patient_id})

        logger.info(f"Created patient: {patient_id}")

        # 2. Create Conditions if provided
        if patient_data.get('conditions'):
            for condition in patient_data['conditions']:
                try:
                    condition_resource = {
                        'resourceType': 'Condition',
                        'subject': {'reference': f'Patient/{patient_id}'},
                        'code': {
                            'text': condition.get('name'),
                            'coding': condition.get('coding', [])
                        },
                        'clinicalStatus': {
                            'coding': [{
                                'system': 'http://terminology.hl7.org/CodeSystem/condition-clinical',
                                'code': condition.get('status', 'active')
                            }]
                        },
                        'onsetDateTime': condition.get('onset_date', datetime.now().isoformat())
                    }

                    if condition.get('stage'):
                        condition_resource['stage'] = [{
                            'summary': {'text': f"Stage {condition['stage']}"}
                        }]

                    created_condition = create_fhir_resource(condition_resource)
                    created_resources.append({'type': 'Condition', 'id': created_condition['id']})
                except Exception as e:
                    logger.warning(f"Failed to create Condition: {str(e)}")

        # 3. Create Observations (lab values)
        if patient_data.get('observations'):
            for observation in patient_data['observations']:
                try:
                    observation_resource = {
                        'resourceType': 'Observation',
                        'status': 'final',
                        'subject': {'reference': f'Patient/{patient_id}'},
                        'code': {
                            'text': observation.get('name'),
                            'coding': observation.get('coding', [])
                        },
                        'valueQuantity': {
                            'value': observation.get('value'),
                            'unit': observation.get('unit'),
                            'system': 'http://unitsofmeasure.org'
                        },
                        'effectiveDateTime': observation.get('date', datetime.now().isoformat())
                    }

                    created_observation = create_fhir_resource(observation_resource)
                    created_resources.append({'type': 'Observation', 'id': created_observation['id']})
                except Exception as e:
                    logger.warning(f"Failed to create Observation: {str(e)}")

        # 4. Create Performance Status
        if patient_data.get('ecog_status') is not None:
            ecog_status_value = patient_data['ecog_status']
            # Ensure it's an integer
            if isinstance(ecog_status_value, str):
                ecog_status_value = int(ecog_status_value)

            ecog_resource = {
                'resourceType': 'Observation',
                'status': 'final',
                'category': [{
                    'coding': [{
                        'system': 'http://terminology.hl7.org/CodeSystem/observation-category',
                        'code': 'survey',
                        'display': 'Survey'
                    }]
                }],
                'subject': {'reference': f'Patient/{patient_id}'},
                'code': {
                    'coding': [{
                        'system': 'http://loinc.org',
                        'code': '89247-1',
                        'display': 'ECOG Performance Status'
                    }],
                    'text': 'ECOG Performance Status'
                },
                'valueCodeableConcept': {
                    'coding': [{
                        'system': 'http://loinc.org',
                        'code': f'LA{ecog_status_value}',
                        'display': f'ECOG {ecog_status_value}'
                    }],
                    'text': f'ECOG {ecog_status_value}'
                },
                'effectiveDateTime': datetime.now().isoformat()
            }

            try:
                created_ecog = create_fhir_resource(ecog_resource)
                created_resources.append({'type': 'Observation (ECOG)', 'id': created_ecog['id']})
                logger.info(f"Created ECOG observation: {created_ecog['id']}")
            except Exception as e:
                logger.warning(f"Failed to create ECOG observation: {str(e)}")
                # Continue with other resources even if ECOG fails

        # 5. Create MedicationStatements
        if patient_data.get('medications'):
            for medication in patient_data['medications']:
                try:
                    med_resource = {
                        'resourceType': 'MedicationStatement',
                        'status': medication.get('status', 'active'),
                        'subject': {'reference': f'Patient/{patient_id}'},
                        'medicationCodeableConcept': {
                            'text': medication.get('name'),
                            'coding': medication.get('coding', [])
                        },
                        'effectiveDateTime': medication.get('start_date', datetime.now().isoformat())
                    }

                    created_med = create_fhir_resource(med_resource)
                    created_resources.append({'type': 'MedicationStatement', 'id': created_med['id']})
                except Exception as e:
                    logger.warning(f"Failed to create MedicationStatement: {str(e)}")

        # 6. Create AllergyIntolerances
        if patient_data.get('allergies'):
            for allergy in patient_data['allergies']:
                try:
                    allergy_resource = {
                        'resourceType': 'AllergyIntolerance',
                        'patient': {'reference': f'Patient/{patient_id}'},
                        'code': {
                            'text': allergy.get('name'),
                            'coding': allergy.get('coding', [])
                        },
                        'type': allergy.get('type', 'allergy'),
                        'category': allergy.get('category', ['food']),
                        'criticality': allergy.get('criticality', 'low'),
                        'recordedDate': allergy.get('recorded_date', datetime.now().isoformat())
                    }

                    created_allergy = create_fhir_resource(allergy_resource)
                    created_resources.append({'type': 'AllergyIntolerance', 'id': created_allergy['id']})
                except Exception as e:
                    logger.warning(f"Failed to create AllergyIntolerance: {str(e)}")

        # 7. Create Procedures
        if patient_data.get('procedures'):
            for procedure in patient_data['procedures']:
                try:
                    procedure_resource = {
                        'resourceType': 'Procedure',
                        'status': 'completed',
                        'subject': {'reference': f'Patient/{patient_id}'},
                        'code': {
                            'text': procedure.get('name'),
                            'coding': procedure.get('coding', [])
                        },
                        'performedDateTime': procedure.get('performed_date', datetime.now().isoformat())
                    }

                    created_procedure = create_fhir_resource(procedure_resource)
                    created_resources.append({'type': 'Procedure', 'id': created_procedure['id']})
                except Exception as e:
                    logger.warning(f"Failed to create Procedure: {str(e)}")

        # 8. Create Immunizations
        if patient_data.get('immunizations'):
            for immunization in patient_data['immunizations']:
                try:
                    imm_resource = {
                        'resourceType': 'Immunization',
                        'status': 'completed',
                        'patient': {'reference': f'Patient/{patient_id}'},
                        'vaccineCode': {
                            'text': immunization.get('vaccine'),
                            'coding': immunization.get('coding', [])
                        },
                        'occurrenceDateTime': immunization.get('date', datetime.now().isoformat())
                    }

                    created_imm = create_fhir_resource(imm_resource)
                    created_resources.append({'type': 'Immunization', 'id': created_imm['id']})
                except Exception as e:
                    logger.warning(f"Failed to create Immunization: {str(e)}")

        # 9. Create FamilyMemberHistory
        if patient_data.get('family_history'):
            for history in patient_data['family_history']:
                try:
                    fmh_resource = {
                        'resourceType': 'FamilyMemberHistory',
                        'status': 'completed',
                        'patient': {'reference': f'Patient/{patient_id}'},
                        'relationship': {
                            'text': history.get('relationship'),
                            'coding': history.get('relationship_coding', [])
                        },
                        'condition': [{
                            'code': {
                                'text': history.get('condition'),
                                'coding': history.get('condition_coding', [])
                            }
                        }],
                        'date': history.get('date', datetime.now().isoformat())
                    }

                    created_fmh = create_fhir_resource(fmh_resource)
                    created_resources.append({'type': 'FamilyMemberHistory', 'id': created_fmh['id']})
                except Exception as e:
                    logger.warning(f"Failed to create FamilyMemberHistory: {str(e)}")

        # 10. Create Encounters
        if patient_data.get('encounters'):
            for encounter in patient_data['encounters']:
                try:
                    enc_resource = {
                        'resourceType': 'Encounter',
                        'status': encounter.get('status', 'finished'),
                        'class': {
                            'system': 'http://terminology.hl7.org/CodeSystem/v3-ActCode',
                            'code': encounter.get('class', 'AMB'),
                            'display': encounter.get('class_display', 'ambulatory')
                        },
                        'subject': {'reference': f'Patient/{patient_id}'},
                        'period': {
                            'start': encounter.get('start_date', datetime.now().isoformat()),
                            'end': encounter.get('end_date', datetime.now().isoformat())
                        }
                    }

                    if encounter.get('type'):
                        enc_resource['type'] = [{
                            'text': encounter['type'],
                            'coding': encounter.get('type_coding', [])
                        }]

                    created_enc = create_fhir_resource(enc_resource)
                    created_resources.append({'type': 'Encounter', 'id': created_enc['id']})
                except Exception as e:
                    logger.warning(f"Failed to create Encounter: {str(e)}")

        # 11. Create DiagnosticReports
        if patient_data.get('diagnostic_reports'):
            for report in patient_data['diagnostic_reports']:
                try:
                    report_resource = {
                        'resourceType': 'DiagnosticReport',
                        'status': report.get('status', 'final'),
                        'subject': {'reference': f'Patient/{patient_id}'},
                        'code': {
                            'text': report.get('name'),
                            'coding': report.get('coding', [])
                        },
                        'conclusion': report.get('conclusion', ''),
                        'issued': report.get('issued_date', datetime.now().isoformat())
                    }

                    created_report = create_fhir_resource(report_resource)
                    created_resources.append({'type': 'DiagnosticReport', 'id': created_report['id']})
                except Exception as e:
                    logger.warning(f"Failed to create DiagnosticReport: {str(e)}")

        return {
            'success': True,
            'patient_id': patient_id,
            'created_resources': created_resources,
            'message': f'Successfully created patient with {len(created_resources)} resources'
        }

    except Exception as e:
        logger.error(f"Error creating patient: {str(e)}", exc_info=True)
        return {
            'success': False,
            'error': str(e),
            'created_resources': created_resources,
            'message': 'Failed to create patient with all resources'
        }

@logger.inject_lambda_context(log_event=True)
@tracer.capture_lambda_handler
def lambda_handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    Lambda handler for patient management operations.

    Supported operations:
    - GET /patients - List all patients
    - GET /patients/{id} - Get specific patient with all FHIR resources
    - POST /patients/search - Search patients
    - POST /patients - Create new patient with resources
    """
    try:
        # Extract HTTP method and body
        http_method = event.get('httpMethod', 'GET')
        path = event.get('path', '')
        path_params = event.get('pathParameters', {}) or {}

        if 'body' in event:
            body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
        else:
            body = {}

        # Handle OPTIONS for CORS
        if http_method == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': cors_headers(),
                'body': json.dumps({'message': 'OK'})
            }

        # Get specific patient by ID
        if http_method == 'GET' and path_params.get('id'):
            patient_id = path_params['id']
            result = get_patient_by_id(patient_id)

            if not result.get('success'):
                return {
                    'statusCode': 404,
                    'headers': cors_headers(),
                    'body': json.dumps(result)
                }

            return {
                'statusCode': 200,
                'headers': cors_headers(),
                'body': json.dumps(result['patient'])
            }

        # List patients
        elif http_method == 'GET' and '/patients' in path:
            query_params = event.get('queryStringParameters', {}) or {}
            result = list_patients(query_params)

            return {
                'statusCode': 200,
                'headers': cors_headers(),
                'body': json.dumps(result)
            }

        # Search patients
        elif http_method == 'POST' and '/patients/search' in path:
            search_params = body.get('search_params', {})
            result = list_patients(search_params)

            return {
                'statusCode': 200,
                'headers': cors_headers(),
                'body': json.dumps(result)
            }

        # Create patient
        elif http_method == 'POST' and path.endswith('/patients'):
            patient_data = body.get('patient_data', {})
            result = create_patient_with_resources(patient_data)

            return {
                'statusCode': 201 if result['success'] else 400,
                'headers': cors_headers(),
                'body': json.dumps(result)
            }

        else:
            return {
                'statusCode': 404,
                'headers': cors_headers(),
                'body': json.dumps({'error': 'Not found'})
            }

    except Exception as e:
        logger.error(f"Error in lambda_handler: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'headers': cors_headers(),
            'body': json.dumps({
                'error': str(e),
                'message': 'Internal server error'
            })
        }
