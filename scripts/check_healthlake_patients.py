"""
Query HealthLake FHIR datastore to examine patient data
"""
import boto3
import json
import os

# Initialize HealthLake client
healthlake = boto3.client('healthlake', region_name='us-east-1')
datastore_id = os.getenv('HEALTHLAKE_DATASTORE_ID')

print('='*80)
print('QUERYING HEALTHLAKE FHIR DATASTORE FOR PATIENT DATA')
print('='*80)
print()

# Get datastore details
print(f'Datastore ID: {datastore_id}')
print()

# Search for Patient resources
try:
    print('Searching for Patient resources...')
    print()
    
    # Use FHIR search API to get patients
    # HealthLake uses the AWS HealthLake API, not direct FHIR REST
    # We need to use search_with_get or search_with_post
    
    # Let's first check what import/export jobs exist
    print('Checking import/export jobs to understand data flow...')
    import_jobs = healthlake.list_fhir_import_jobs(
        DatastoreId=datastore_id,
        MaxResults=10
    )
    
    print(f"Import jobs found: {len(import_jobs.get('ImportJobPropertiesList', []))}")
    for job in import_jobs.get('ImportJobPropertiesList', []):
        print(f"  - Job ID: {job['JobId']}")
        print(f"    Status: {job['JobStatus']}")
        print(f"    Submit Time: {job['SubmitTime']}")
        print()
    
    export_jobs = healthlake.list_fhir_export_jobs(
        DatastoreId=datastore_id,
        MaxResults=10
    )
    
    print(f"Export jobs found: {len(export_jobs.get('ExportJobPropertiesList', []))}")
    for job in export_jobs.get('ExportJobPropertiesList', []):
        print(f"  - Job ID: {job['JobId']}")
        print(f"    Status: {job['JobStatus']}")
        print(f"    Submit Time: {job['SubmitTime']}")
        print()
    
except Exception as e:
    print(f"Error querying HealthLake: {str(e)}")
    print()

print('='*80)
print('NOTE: HealthLake requires SMART on FHIR or direct FHIR API calls')
print('For detailed patient queries, we need to use the FHIR REST API endpoint')
print('='*80)
print()

# Try using boto3 to query FHIR resources directly
print('Attempting to query FHIR resources using AWS SDK...')
print()

try:
    # HealthLake doesn't have a direct read/search API in boto3
    # We need to use HTTP requests to the FHIR endpoint
    import requests
    from botocore.auth import SigV4Auth
    from botocore.awsrequest import AWSRequest
    
    print('Will need to use HTTP requests with AWS Signature V4 authentication')
    print('Let me create a more comprehensive script...')
    
except Exception as e:
    print(f"Error: {str(e)}")

