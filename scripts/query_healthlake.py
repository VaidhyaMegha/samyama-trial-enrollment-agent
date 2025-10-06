#!/usr/bin/env python3
"""
Query HealthLake FHIR Data

This script allows you to query patient data from AWS HealthLake
using AWS SigV4 authentication.
"""

import boto3
import requests
import json
import sys
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest

# Configuration
REGION = 'us-east-1'
DATASTORE_ID = '8640ed6b344b85e4729ac42df1c7d00e'  # Replace with your actual datastore ID

# Get HealthLake endpoint
healthlake_client = boto3.client('healthlake', region_name=REGION)

try:
    response = healthlake_client.describe_fhir_datastore(DatastoreId=DATASTORE_ID)
    endpoint = response['DatastoreProperties']['DatastoreEndpoint']
    print(f"✓ Connected to HealthLake: {endpoint}")
except Exception as e:
    print(f"✗ Error connecting to HealthLake: {e}")
    print("\nPlease update DATASTORE_ID in this script with your actual datastore ID")
    print("Run: aws healthlake list-fhir-datastores --region us-east-1")
    sys.exit(1)


def query_fhir(resource_type, params=None):
    """Query FHIR resources from HealthLake with AWS SigV4 auth."""
    url = f"{endpoint}{resource_type}"
    
    if params:
        url += '?' + '&'.join([f"{k}={v}" for k, v in params.items()])
    
    request = AWSRequest(method='GET', url=url)
    credentials = boto3.Session().get_credentials()
    SigV4Auth(credentials, 'healthlake', REGION).add_auth(request)
    
    response = requests.get(url, headers=dict(request.headers))
    response.raise_for_status()
    
    return response.json()


def get_patient(patient_id):
    """Get a specific patient by ID."""
    url = f"{endpoint}Patient/{patient_id}"
    
    request = AWSRequest(method='GET', url=url)
    credentials = boto3.Session().get_credentials()
    SigV4Auth(credentials, 'healthlake', REGION).add_auth(request)
    
    response = requests.get(url, headers=dict(request.headers))
    response.raise_for_status()
    
    return response.json()


# Quick commands
if __name__ == "__main__":
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "list-patients":
            bundle = query_fhir('Patient')
            print(json.dumps(bundle, indent=2))
        
        elif command == "get-patient" and len(sys.argv) > 2:
            patient = get_patient(sys.argv[2])
            print(json.dumps(patient, indent=2))
        
        elif command == "count":
            for resource_type in ['Patient', 'Condition', 'Observation']:
                bundle = query_fhir(resource_type, {'_summary': 'count'})
                print(f"{resource_type}: {bundle.get('total', 0)}")
        
        else:
            print("Usage:")
            print("  python query_healthlake.py list-patients")
            print("  python query_healthlake.py get-patient <patient-id>")
            print("  python query_healthlake.py count")
    else:
        print("Usage:")
        print("  python query_healthlake.py list-patients")
        print("  python query_healthlake.py get-patient <patient-id>")
        print("  python query_healthlake.py count")
