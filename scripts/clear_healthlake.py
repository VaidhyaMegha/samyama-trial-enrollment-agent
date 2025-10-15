"""
Clear all data from HealthLake FHIR datastore
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

def make_signed_request(method, url, params=None, data=None):
    """Make an AWS Signature V4 signed request to HealthLake FHIR API."""
    request = AWSRequest(method=method, url=url, params=params, data=data)
    SigV4Auth(credentials, 'healthlake', REGION).add_auth(request)
    
    prepped = request.prepare()
    
    response = requests.request(
        method=prepped.method,
        url=prepped.url,
        headers=dict(prepped.headers),
        data=prepped.body
    )
    
    return response

print('='*80)
print('CLEARING HEALTHLAKE FHIR DATASTORE')
print('='*80)
print()

resource_types = [
    'Patient', 
    'Condition', 
    'Observation', 
    'MedicationStatement', 
    'Procedure', 
    'AllergyIntolerance', 
    'DiagnosticReport', 
    'Immunization', 
    'FamilyMemberHistory', 
    'CarePlan', 
    'Encounter'
]

total_deleted = 0

for resource_type in resource_types:
    print(f'Clearing {resource_type} resources...')
    
    try:
        # Get all resources of this type
        response = make_signed_request('GET', f'{FHIR_ENDPOINT}/{resource_type}', 
                                      params={'_count': 100})
        
        if response.status_code == 200:
            bundle = response.json()
            entries = bundle.get('entry', [])
            
            if entries:
                deleted_count = 0
                for entry in entries:
                    resource = entry.get('resource', {})
                    resource_id = resource.get('id')
                    
                    if resource_id:
                        # Delete the resource
                        del_response = make_signed_request('DELETE', 
                                                          f'{FHIR_ENDPOINT}/{resource_type}/{resource_id}')
                        
                        if del_response.status_code in [200, 204]:
                            deleted_count += 1
                        else:
                            print(f'  Warning: Failed to delete {resource_type}/{resource_id}: {del_response.status_code}')
                
                print(f'  ✅ Deleted {deleted_count} {resource_type} resources')
                total_deleted += deleted_count
            else:
                print(f'  ℹ️  No {resource_type} resources found')
        else:
            print(f'  ❌ Error querying {resource_type}: {response.status_code}')
            
    except Exception as e:
        print(f'  ❌ Error processing {resource_type}: {str(e)}')
    
    print()

print('='*80)
print(f'Total resources deleted: {total_deleted}')
print('='*80)

