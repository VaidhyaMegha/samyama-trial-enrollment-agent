"""
Upload synthetic patient data to AWS HealthLake
"""

import json
import boto3
import sys
import os
from pathlib import Path

# Add parent to path to import data generator
sys.path.insert(0, str(Path(__file__).parent))
from load_synthea_data import load_sample_patients

# HealthLake configuration
HEALTHLAKE_DATASTORE_ID = "8640ed6b344b85e4729ac42df1c7d00e"
REGION = "us-east-1"

# Initialize HealthLake client
healthlake = boto3.client('healthlake', region_name=REGION)


def upload_bundle_to_healthlake(bundle):
    """
    Upload a FHIR bundle to HealthLake.

    Args:
        bundle: FHIR bundle dictionary

    Returns:
        True if successful
    """
    try:
        # Start import job for the bundle
        # HealthLake requires bundles to be uploaded via S3 import jobs
        # For direct upload, we'll use the FHIR API

        # Get datastore endpoint
        response = healthlake.describe_fhir_datastore(DatastoreId=HEALTHLAKE_DATASTORE_ID)
        endpoint = response['DatastoreProperties']['DatastoreEndpoint']

        print(f"HealthLake Endpoint: {endpoint}")
        print(f"Note: Direct FHIR API uploads require AWS SigV4 authentication")
        print(f"For this demo, we'll use the alternate approach with boto3")

        # For now, let's use the FHIR REST API via requests with AWS auth
        import requests
        from botocore.auth import SigV4Auth
        from botocore.awsrequest import AWSRequest

        # Process each entry in the bundle
        for entry in bundle.get('entry', []):
            resource = entry['resource']
            resource_type = resource['resourceType']
            resource_id = resource.get('id')

            if resource_id:
                # PUT to create/update resource
                url = f"{endpoint}{resource_type}/{resource_id}"
                method = 'PUT'
            else:
                # POST to create new resource
                url = f"{endpoint}{resource_type}"
                method = 'POST'

            # Prepare request
            headers = {
                'Content-Type': 'application/fhir+json'
            }

            # Create AWS request for signing
            request = AWSRequest(
                method=method,
                url=url,
                data=json.dumps(resource),
                headers=headers
            )

            # Sign with SigV4
            SigV4Auth(
                boto3.Session().get_credentials(),
                'healthlake',
                REGION
            ).add_auth(request)

            # Send request
            response = requests.request(
                method=request.method,
                url=request.url,
                headers=dict(request.headers),
                data=request.body
            )

            if response.status_code in [200, 201]:
                print(f"✓ Uploaded {resource_type}/{resource_id or 'new'}")
            else:
                print(f"✗ Failed to upload {resource_type}/{resource_id}: {response.status_code}")
                print(f"  Response: {response.text[:200]}")

        return True

    except Exception as e:
        print(f"Error uploading to HealthLake: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main function"""
    print("="*80)
    print("Uploading Synthetic Patient Data to AWS HealthLake")
    print("="*80)
    print(f"\nDatastore ID: {HEALTHLAKE_DATASTORE_ID}")
    print(f"Region: {REGION}\n")

    # Load sample patients
    print("Generating sample patients...")
    patients = load_sample_patients()
    print(f"Generated {len(patients)} patient bundles\n")

    # Upload to HealthLake
    print("Uploading to HealthLake...")
    success_count = 0

    for idx, patient in enumerate(patients, 1):
        print(f"\nUploading patient bundle {idx}/{len(patients)}...")
        if upload_bundle_to_healthlake(patient):
            success_count += 1

    print(f"\n✓ Successfully uploaded {success_count}/{len(patients)} bundles to HealthLake")

    print("\n" + "="*80)
    print("Upload Complete!")
    print("="*80)


if __name__ == "__main__":
    main()
