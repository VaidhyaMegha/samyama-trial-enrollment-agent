#!/usr/bin/env python3
"""
End-to-End Demo of Trial Enrollment Agent

This script demonstrates the complete workflow:
1. Parse eligibility criteria using Bedrock
2. Check patient eligibility against HealthLake FHIR data
3. Display results
"""

import json
import boto3
from datetime import datetime

# Configuration
CRITERIA_PARSER_FUNCTION = "TrialEnrollment-CriteriaParser"
FHIR_SEARCH_FUNCTION = "TrialEnrollment-FHIRSearch"
REGION = "us-east-1"

# Initialize Lambda client
lambda_client = boto3.client('lambda', region_name=REGION)


def parse_criteria(criteria_text: str, trial_id: str) -> dict:
    """Parse eligibility criteria using the Criteria Parser Lambda."""
    print("="*80)
    print("STEP 1: Parsing Eligibility Criteria")
    print("="*80)
    print(f"\nTrial ID: {trial_id}")
    print(f"Criteria Text: {criteria_text}\n")

    payload = {
        "criteria_text": criteria_text,
        "trial_id": trial_id
    }

    response = lambda_client.invoke(
        FunctionName=CRITERIA_PARSER_FUNCTION,
        InvocationType='RequestResponse',
        Payload=json.dumps(payload)
    )

    result = json.loads(response['Payload'].read())

    if result['statusCode'] == 200:
        body = json.loads(result['body'])
        print(f"✓ Successfully parsed {body['count']} criteria\n")

        for idx, criterion in enumerate(body['criteria'], 1):
            print(f"Criterion {idx}:")
            print(f"  Type: {criterion['type']}")
            print(f"  Category: {criterion['category']}")
            print(f"  Description: {criterion['description']}")
            print(f"  Attribute: {criterion['attribute']}")
            print(f"  Operator: {criterion['operator']}")
            print(f"  Value: {criterion['value']}")
            print()

        return body['criteria']
    else:
        print(f"✗ Error parsing criteria: {result}")
        return []


def check_patient_eligibility(patient_id: str, criteria: list) -> dict:
    """Check patient eligibility using the FHIR Search Lambda."""
    print("="*80)
    print(f"STEP 2: Checking Patient Eligibility - {patient_id}")
    print("="*80)

    payload = {
        "patient_id": patient_id,
        "criteria": criteria
    }

    response = lambda_client.invoke(
        FunctionName=FHIR_SEARCH_FUNCTION,
        InvocationType='RequestResponse',
        Payload=json.dumps(payload)
    )

    result = json.loads(response['Payload'].read())

    if result['statusCode'] == 200:
        body = json.loads(result['body'])

        print(f"\nPatient: {body['patient_id']}")
        print(f"Eligible: {'✓ YES' if body['eligible'] else '✗ NO'}\n")

        print("Criteria Results:")
        for idx, res in enumerate(body['results'], 1):
            criterion = res['criterion']
            status = "✓ MET" if res['met'] else "✗ NOT MET"
            print(f"  {idx}. {criterion['description']}: {status}")
            print(f"     Reason: {res['reason']}")

        print(f"\nSummary:")
        print(f"  Total Criteria: {body['summary']['total_criteria']}")
        print(f"  Inclusion Met: {body['summary']['inclusion_met']}")
        print(f"  Exclusion Violated: {body['summary']['exclusion_violated']}")

        return body
    else:
        print(f"✗ Error checking eligibility: {result}")
        return {}


def main():
    """Run the end-to-end demo."""
    print("\n" + "="*80)
    print("AWS TRIAL ENROLLMENT AGENT - END-TO-END DEMO")
    print("="*80)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Test Case 1: Simple age criterion
    criteria_text = "Patients must be between 18 and 65 years old"
    trial_id = "demo-trial-001"

    # Parse criteria
    parsed_criteria = parse_criteria(criteria_text, trial_id)

    if not parsed_criteria:
        print("Failed to parse criteria. Exiting.")
        return

    # Test against multiple patients
    test_patients = [
        ("patient-001", "Female, 46 years old - Expected: ELIGIBLE"),
        ("patient-002", "Male, 15 years old - Expected: NOT ELIGIBLE"),
        ("patient-003", "Male, 55 years old - Expected: ELIGIBLE")
    ]

    results_summary = []

    for patient_id, description in test_patients:
        print(f"\nTesting: {description}")
        result = check_patient_eligibility(patient_id, parsed_criteria)
        results_summary.append({
            'patient_id': patient_id,
            'description': description,
            'eligible': result.get('eligible', False)
        })
        print()

    # Final Summary
    print("="*80)
    print("FINAL SUMMARY")
    print("="*80)
    print(f"\nTrial: {trial_id}")
    print(f"Criteria: {criteria_text}\n")
    print("Patient Eligibility Results:")

    for res in results_summary:
        status = "✓ ELIGIBLE" if res['eligible'] else "✗ NOT ELIGIBLE"
        print(f"  {res['patient_id']}: {status}")
        print(f"    {res['description']}")

    eligible_count = sum(1 for r in results_summary if r['eligible'])
    print(f"\nTotal Patients Tested: {len(results_summary)}")
    print(f"Eligible Patients: {eligible_count}")
    print(f"Not Eligible: {len(results_summary) - eligible_count}")

    print("\n" + "="*80)
    print("DEMO COMPLETE!")
    print("="*80)


if __name__ == "__main__":
    main()
