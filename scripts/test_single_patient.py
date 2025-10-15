"""Test creating a single patient to debug the FHIR bundle"""
import sys
sys.path.append('scripts')

from create_fhir_patients import create_patient_bundle, make_signed_request, FHIR_ENDPOINT
from seed_healthlake_patients import PATIENTS
import json

# Get first patient
patient = PATIENTS[0]
print(f"Testing patient: {patient['given_name']} {patient['family_name']}")
print()

# Create bundle
bundle = create_patient_bundle(patient)

print("Bundle structure:")
print(json.dumps(bundle, indent=2)[:1000])
print("...")
print()

# Try to post it
print("Posting to HealthLake...")
response = make_signed_request('POST', FHIR_ENDPOINT, data=json.dumps(bundle))

print(f"Status Code: {response.status_code}")
print(f"Response: {response.text}")

