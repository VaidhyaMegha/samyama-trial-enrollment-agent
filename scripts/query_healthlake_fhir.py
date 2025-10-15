"""
Query HealthLake FHIR API endpoint to examine patient data
Uses AWS Signature V4 authentication for FHIR REST API calls
"""
import boto3
import json
import os
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
import requests

# Configuration
REGION = 'us-east-1'
DATASTORE_ID = os.getenv('HEALTHLAKE_DATASTORE_ID')
FHIR_ENDPOINT = f'https://healthlake.{REGION}.amazonaws.com/datastore/{DATASTORE_ID}/r4'

# Create session and credentials
session = boto3.Session()
credentials = session.get_credentials()

def make_signed_request(method, url, params=None):
    """Make an AWS Signature V4 signed request to HealthLake FHIR API."""
    request = AWSRequest(method=method, url=url, params=params)
    SigV4Auth(credentials, 'healthlake', REGION).add_auth(request)
    
    # Convert to requests format
    prepped = request.prepare()
    
    response = requests.request(
        method=prepped.method,
        url=prepped.url,
        headers=dict(prepped.headers)
    )
    
    return response

print('='*80)
print('QUERYING HEALTHLAKE FHIR API')
print('='*80)
print()
print(f'Endpoint: {FHIR_ENDPOINT}')
print()

# 1. Search for all Patient resources
print('1. Searching for Patient resources...')
print('-'*80)
try:
    response = make_signed_request('GET', f'{FHIR_ENDPOINT}/Patient', params={'_count': 10})
    
    if response.status_code == 200:
        bundle = response.json()
        total = bundle.get('total', 0)
        entries = bundle.get('entry', [])
        
        print(f'Total patients found: {total}')
        print(f'Returned in this page: {len(entries)}')
        print()
        
        if entries:
            print('Sample patients:')
            for i, entry in enumerate(entries[:3], 1):
                patient = entry.get('resource', {})
                patient_id = patient.get('id', 'N/A')
                
                # Extract name
                names = patient.get('name', [])
                if names:
                    name = names[0]
                    given = ' '.join(name.get('given', []))
                    family = name.get('family', '')
                    full_name = f"{given} {family}"
                else:
                    full_name = 'N/A'
                
                # Extract demographics
                gender = patient.get('gender', 'N/A')
                birth_date = patient.get('birthDate', 'N/A')
                
                print(f'\n  Patient {i}:')
                print(f'    ID: {patient_id}')
                print(f'    Name: {full_name}')
                print(f'    Gender: {gender}')
                print(f'    Birth Date: {birth_date}')
        else:
            print('No patients found in datastore')
    else:
        print(f'Error: HTTP {response.status_code}')
        print(f'Response: {response.text}')
        
except Exception as e:
    print(f'Error querying Patient resources: {str(e)}')

print()
print()

# 2. Search for Condition resources
print('2. Searching for Condition resources...')
print('-'*80)
try:
    response = make_signed_request('GET', f'{FHIR_ENDPOINT}/Condition', params={'_count': 5})
    
    if response.status_code == 200:
        bundle = response.json()
        total = bundle.get('total', 0)
        entries = bundle.get('entry', [])
        
        print(f'Total conditions found: {total}')
        print(f'Returned in this page: {len(entries)}')
        
        if entries:
            print('\nSample conditions:')
            for i, entry in enumerate(entries[:3], 1):
                condition = entry.get('resource', {})
                condition_id = condition.get('id', 'N/A')
                
                # Extract code
                code_obj = condition.get('code', {})
                coding = code_obj.get('coding', [])
                if coding:
                    code = coding[0].get('code', 'N/A')
                    display = coding[0].get('display', 'N/A')
                else:
                    code = 'N/A'
                    display = 'N/A'
                
                # Extract patient reference
                subject = condition.get('subject', {})
                patient_ref = subject.get('reference', 'N/A')
                
                print(f'\n  Condition {i}:')
                print(f'    ID: {condition_id}')
                print(f'    Code: {code}')
                print(f'    Display: {display}')
                print(f'    Patient: {patient_ref}')
    else:
        print(f'Error: HTTP {response.status_code}')
        print(f'Response: {response.text}')
        
except Exception as e:
    print(f'Error querying Condition resources: {str(e)}')

print()
print()

# 3. Search for Observation resources
print('3. Searching for Observation resources...')
print('-'*80)
try:
    response = make_signed_request('GET', f'{FHIR_ENDPOINT}/Observation', params={'_count': 5})
    
    if response.status_code == 200:
        bundle = response.json()
        total = bundle.get('total', 0)
        entries = bundle.get('entry', [])
        
        print(f'Total observations found: {total}')
        print(f'Returned in this page: {len(entries)}')
        
        if entries:
            print('\nSample observations:')
            for i, entry in enumerate(entries[:3], 1):
                observation = entry.get('resource', {})
                obs_id = observation.get('id', 'N/A')
                
                # Extract code
                code_obj = observation.get('code', {})
                coding = code_obj.get('coding', [])
                if coding:
                    code = coding[0].get('code', 'N/A')
                    display = coding[0].get('display', 'N/A')
                else:
                    code = 'N/A'
                    display = 'N/A'
                
                # Extract value
                value_qty = observation.get('valueQuantity', {})
                if value_qty:
                    value = value_qty.get('value', 'N/A')
                    unit = value_qty.get('unit', '')
                    value_str = f"{value} {unit}"
                else:
                    value_str = 'N/A'
                
                print(f'\n  Observation {i}:')
                print(f'    ID: {obs_id}')
                print(f'    Code: {code}')
                print(f'    Display: {display}')
                print(f'    Value: {value_str}')
    else:
        print(f'Error: HTTP {response.status_code}')
        print(f'Response: {response.text}')
        
except Exception as e:
    print(f'Error querying Observation resources: {str(e)}')

print()
print()

# 4. Get a detailed view of one patient with all related resources
print('4. Detailed view of first patient with related resources...')
print('-'*80)
try:
    # Get first patient
    response = make_signed_request('GET', f'{FHIR_ENDPOINT}/Patient', params={'_count': 1})
    
    if response.status_code == 200:
        bundle = response.json()
        entries = bundle.get('entry', [])
        
        if entries:
            patient = entries[0].get('resource', {})
            patient_id = patient.get('id')
            
            print(f'Patient ID: {patient_id}')
            print()
            print('Full Patient Resource:')
            print(json.dumps(patient, indent=2))
            print()
            print('-'*80)
            
            # Get related conditions
            print(f'\nConditions for Patient/{patient_id}:')
            cond_response = make_signed_request('GET', f'{FHIR_ENDPOINT}/Condition', 
                                               params={'patient': patient_id, '_count': 5})
            if cond_response.status_code == 200:
                cond_bundle = cond_response.json()
                cond_entries = cond_bundle.get('entry', [])
                print(f'  Found {len(cond_entries)} conditions')
                for entry in cond_entries[:3]:
                    cond = entry.get('resource', {})
                    code_obj = cond.get('code', {})
                    text = code_obj.get('text', 'N/A')
                    print(f'    - {text}')
            
            # Get related observations
            print(f'\nObservations for Patient/{patient_id}:')
            obs_response = make_signed_request('GET', f'{FHIR_ENDPOINT}/Observation', 
                                              params={'patient': patient_id, '_count': 5})
            if obs_response.status_code == 200:
                obs_bundle = obs_response.json()
                obs_entries = obs_bundle.get('entry', [])
                print(f'  Found {len(obs_entries)} observations')
                for entry in obs_entries[:3]:
                    obs = entry.get('resource', {})
                    code_obj = obs.get('code', {})
                    text = code_obj.get('text', 'N/A')
                    value_qty = obs.get('valueQuantity', {})
                    if value_qty:
                        value = f"{value_qty.get('value', 'N/A')} {value_qty.get('unit', '')}"
                    else:
                        value = 'N/A'
                    print(f'    - {text}: {value}')
        else:
            print('No patients found')
    else:
        print(f'Error: HTTP {response.status_code}')
        
except Exception as e:
    print(f'Error getting detailed patient view: {str(e)}')

print()
print('='*80)
print('HEALTHLAKE QUERY COMPLETE')
print('='*80)

