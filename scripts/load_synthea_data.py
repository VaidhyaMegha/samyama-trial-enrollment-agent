"""
Script to load synthetic patient data from Synthea into FHIR server.

This script:
1. Downloads Synthea if not present
2. Generates synthetic patient data
3. Uploads FHIR bundles to the configured FHIR endpoint
"""

import json
import os
import sys
import requests
from pathlib import Path
from typing import List, Dict, Any


FHIR_ENDPOINT = os.environ.get('FHIR_ENDPOINT', 'http://localhost:8080/fhir')
SYNTHEA_DATA_DIR = Path(__file__).parent.parent / 'data' / 'synthetic_patients'


def load_sample_patients() -> List[Dict[str, Any]]:
    """
    Load sample patient FHIR bundles.

    For this demo, we'll create a few synthetic patients directly
    rather than requiring Synthea installation.

    Returns:
        List of FHIR patient bundles
    """
    patients = []

    # Patient 1: Eligible for diabetes trial (45yo with Type 2 Diabetes, HbA1c 8%)
    patient1 = {
        "resourceType": "Bundle",
        "type": "transaction",
        "entry": [
            {
                "fullUrl": "urn:uuid:patient-001",
                "resource": {
                    "resourceType": "Patient",
                    "id": "patient-001",
                    "gender": "female",
                    "birthDate": "1979-05-15",
                    "name": [{
                        "family": "Smith",
                        "given": ["Sarah"]
                    }]
                },
                "request": {
                    "method": "PUT",
                    "url": "Patient/patient-001"
                }
            },
            {
                "fullUrl": "urn:uuid:condition-001",
                "resource": {
                    "resourceType": "Condition",
                    "id": "condition-001",
                    "subject": {"reference": "Patient/patient-001"},
                    "code": {
                        "coding": [{
                            "system": "http://snomed.info/sct",
                            "code": "44054006",
                            "display": "Type 2 Diabetes Mellitus"
                        }],
                        "text": "Type 2 Diabetes Mellitus"
                    },
                    "clinicalStatus": {
                        "coding": [{
                            "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                            "code": "active"
                        }]
                    }
                },
                "request": {
                    "method": "PUT",
                    "url": "Condition/condition-001"
                }
            },
            {
                "fullUrl": "urn:uuid:observation-001",
                "resource": {
                    "resourceType": "Observation",
                    "id": "observation-001",
                    "status": "final",
                    "subject": {"reference": "Patient/patient-001"},
                    "code": {
                        "coding": [{
                            "system": "http://loinc.org",
                            "code": "4548-4",
                            "display": "Hemoglobin A1c"
                        }],
                        "text": "HbA1c"
                    },
                    "valueQuantity": {
                        "value": 8.0,
                        "unit": "%",
                        "system": "http://unitsofmeasure.org",
                        "code": "%"
                    },
                    "effectiveDateTime": "2024-09-15T10:30:00Z"
                },
                "request": {
                    "method": "PUT",
                    "url": "Observation/observation-001"
                }
            }
        ]
    }
    patients.append(patient1)

    # Patient 2: Not eligible - too young
    patient2 = {
        "resourceType": "Bundle",
        "type": "transaction",
        "entry": [
            {
                "fullUrl": "urn:uuid:patient-002",
                "resource": {
                    "resourceType": "Patient",
                    "id": "patient-002",
                    "gender": "male",
                    "birthDate": "2010-03-20",
                    "name": [{
                        "family": "Johnson",
                        "given": ["Michael"]
                    }]
                },
                "request": {
                    "method": "PUT",
                    "url": "Patient/patient-002"
                }
            }
        ]
    }
    patients.append(patient2)

    # Patient 3: Not eligible - has exclusion criterion (CKD)
    patient3 = {
        "resourceType": "Bundle",
        "type": "transaction",
        "entry": [
            {
                "fullUrl": "urn:uuid:patient-003",
                "resource": {
                    "resourceType": "Patient",
                    "id": "patient-003",
                    "gender": "male",
                    "birthDate": "1970-08-10",
                    "name": [{
                        "family": "Williams",
                        "given": ["Robert"]
                    }]
                },
                "request": {
                    "method": "PUT",
                    "url": "Patient/patient-003"
                }
            },
            {
                "fullUrl": "urn:uuid:condition-003-diabetes",
                "resource": {
                    "resourceType": "Condition",
                    "id": "condition-003-diabetes",
                    "subject": {"reference": "Patient/patient-003"},
                    "code": {
                        "coding": [{
                            "system": "http://snomed.info/sct",
                            "code": "44054006",
                            "display": "Type 2 Diabetes Mellitus"
                        }],
                        "text": "Type 2 Diabetes Mellitus"
                    },
                    "clinicalStatus": {
                        "coding": [{
                            "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                            "code": "active"
                        }]
                    }
                },
                "request": {
                    "method": "PUT",
                    "url": "Condition/condition-003-diabetes"
                }
            },
            {
                "fullUrl": "urn:uuid:condition-003-ckd",
                "resource": {
                    "resourceType": "Condition",
                    "id": "condition-003-ckd",
                    "subject": {"reference": "Patient/patient-003"},
                    "code": {
                        "coding": [{
                            "system": "http://snomed.info/sct",
                            "code": "431855005",
                            "display": "Chronic kidney disease stage 4"
                        }],
                        "text": "Chronic kidney disease stage 4"
                    },
                    "clinicalStatus": {
                        "coding": [{
                            "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                            "code": "active"
                        }]
                    }
                },
                "request": {
                    "method": "PUT",
                    "url": "Condition/condition-003-ckd"
                }
            },
            {
                "fullUrl": "urn:uuid:observation-003",
                "resource": {
                    "resourceType": "Observation",
                    "id": "observation-003",
                    "status": "final",
                    "subject": {"reference": "Patient/patient-003"},
                    "code": {
                        "coding": [{
                            "system": "http://loinc.org",
                            "code": "4548-4",
                            "display": "Hemoglobin A1c"
                        }],
                        "text": "HbA1c"
                    },
                    "valueQuantity": {
                        "value": 7.5,
                        "unit": "%",
                        "system": "http://unitsofmeasure.org",
                        "code": "%"
                    },
                    "effectiveDateTime": "2024-09-20T14:00:00Z"
                },
                "request": {
                    "method": "PUT",
                    "url": "Observation/observation-003"
                }
            }
        ]
    }
    patients.append(patient3)

    return patients


def upload_bundle_to_fhir(bundle: Dict[str, Any], endpoint: str) -> bool:
    """
    Upload a FHIR bundle to the server.

    Args:
        bundle: FHIR bundle
        endpoint: FHIR server endpoint

    Returns:
        True if successful
    """
    try:
        response = requests.post(
            endpoint,
            json=bundle,
            headers={'Content-Type': 'application/fhir+json'},
            timeout=30
        )
        response.raise_for_status()
        print(f"✓ Uploaded bundle successfully")
        return True

    except requests.exceptions.RequestException as e:
        print(f"✗ Failed to upload bundle: {str(e)}")
        return False


def save_sample_patients_locally(patients: List[Dict[str, Any]]):
    """
    Save sample patients to local files for reference.

    Args:
        patients: List of patient bundles
    """
    SYNTHEA_DATA_DIR.mkdir(parents=True, exist_ok=True)

    for idx, patient in enumerate(patients, 1):
        file_path = SYNTHEA_DATA_DIR / f"patient-{idx:03d}.json"
        with open(file_path, 'w') as f:
            json.dump(patient, f, indent=2)
        print(f"Saved patient bundle to {file_path}")


def main():
    """
    Main function to load synthetic data.
    """
    print("="*80)
    print("Loading Synthetic Patient Data")
    print("="*80)
    print(f"\nFHIR Endpoint: {FHIR_ENDPOINT}")
    print()

    # Load sample patients
    print("Generating sample patients...")
    patients = load_sample_patients()
    print(f"Generated {len(patients)} patient bundles\n")

    # Save locally
    print("Saving patients to local files...")
    save_sample_patients_locally(patients)
    print()

    # Upload to FHIR server
    print("Uploading to FHIR server...")
    upload_fhir = input("Upload to FHIR server? (y/n): ").lower().strip() == 'y'

    if upload_fhir:
        success_count = 0
        for idx, patient in enumerate(patients, 1):
            print(f"\nUploading patient bundle {idx}/{len(patients)}...")
            if upload_bundle_to_fhir(patient, FHIR_ENDPOINT):
                success_count += 1

        print(f"\n✓ Successfully uploaded {success_count}/{len(patients)} bundles")
    else:
        print("\nSkipped upload. Bundles saved locally only.")

    print("\n" + "="*80)
    print("Summary:")
    print("="*80)
    print(f"Patient 1 (patient-001): Eligible - 45yo female with Type 2 Diabetes, HbA1c 8%")
    print(f"Patient 2 (patient-002): Not Eligible - 14yo (too young)")
    print(f"Patient 3 (patient-003): Not Eligible - Has CKD stage 4 (exclusion criterion)")
    print("\nYou can now test the agent with these patient IDs.")
    print("="*80)


if __name__ == "__main__":
    main()
