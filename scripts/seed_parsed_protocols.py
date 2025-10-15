"""
Seed DynamoDB Criteria Cache with Pre-Parsed Protocols
Directly inserts structured parsed criteria without needing Bedrock processing
"""

import boto3
import json
from datetime import datetime, timedelta
from decimal import Decimal

# Initialize DynamoDB
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table_name = 'TrialEnrollmentAgentStack-CriteriaCacheTableFDCD8472-1QNO79RYH9M88'
table = dynamodb.Table(table_name)

def convert_to_decimal(obj):
    """Convert floats to Decimal for DynamoDB."""
    if isinstance(obj, list):
        return [convert_to_decimal(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: convert_to_decimal(value) for key, value in obj.items()}
    elif isinstance(obj, float):
        return Decimal(str(obj))
    return obj

# Define 10 diverse clinical trial protocols with pre-parsed criteria
PROTOCOLS = [
    {
        "trial_id": "DIABETES-SIMPLE-001",
        "title": "Type 2 Diabetes Management Study",
        "description": "Simple diabetes trial focusing on age, diagnosis, and HbA1c",
        "parsed_criteria": [
            {
                "type": "inclusion",
                "category": "demographics",
                "description": "Age between 30 and 70 years",
                "attribute": "age",
                "operator": "between",
                "value": [30, 70],
                "unit": "years",
                "fhir_resource": "Patient",
                "fhir_path": "Patient.birthDate"
            },
            {
                "type": "inclusion",
                "category": "condition",
                "description": "Type 2 Diabetes Mellitus",
                "attribute": "diagnosis",
                "operator": "contains",
                "value": "Type 2 Diabetes",
                "fhir_resource": "Condition",
                "fhir_path": "Condition.code",
                "coding": {
                    "system": "http://hl7.org/fhir/sid/icd-10-cm",
                    "code": "E11",
                    "display": "Type 2 diabetes mellitus"
                }
            },
            {
                "type": "inclusion",
                "category": "lab_value",
                "description": "HbA1c between 7% and 10%",
                "attribute": "HbA1c",
                "operator": "between",
                "value": [7, 10],
                "unit": "%",
                "fhir_resource": "Observation",
                "fhir_path": "Observation.valueQuantity",
                "coding": {
                    "system": "http://loinc.org",
                    "code": "4548-4",
                    "display": "Hemoglobin A1c"
                }
            },
            {
                "type": "inclusion",
                "category": "medication",
                "description": "Currently taking metformin",
                "attribute": "medication_name",
                "operator": "contains",
                "value": "metformin",
                "fhir_resource": "MedicationStatement",
                "fhir_path": "MedicationStatement.medicationCodeableConcept",
                "status": "active"
            },
            {
                "type": "exclusion",
                "category": "condition",
                "description": "No chronic kidney disease stage 4 or higher",
                "attribute": "chronic_kidney_disease",
                "operator": "not_contains",
                "value": "chronic kidney disease stage 4",
                "fhir_resource": "Condition",
                "fhir_path": "Condition.code"
            }
        ]
    },
    {
        "trial_id": "HYPERTENSION-002",
        "title": "Hypertension Control Trial",
        "description": "Blood pressure management study",
        "parsed_criteria": [
            {
                "type": "inclusion",
                "category": "demographics",
                "description": "Age 40 years or older",
                "attribute": "age",
                "operator": "greater_than",
                "value": 40,
                "unit": "years",
                "fhir_resource": "Patient",
                "fhir_path": "Patient.birthDate"
            },
            {
                "type": "inclusion",
                "category": "condition",
                "description": "Hypertension diagnosis",
                "attribute": "diagnosis",
                "operator": "contains",
                "value": "hypertension",
                "fhir_resource": "Condition",
                "fhir_path": "Condition.code",
                "coding": {
                    "system": "http://hl7.org/fhir/sid/icd-10-cm",
                    "code": "I10",
                    "display": "Essential (primary) hypertension"
                }
            },
            {
                "type": "inclusion",
                "category": "medication",
                "description": "On ACE inhibitor or ARB",
                "attribute": "medication_class",
                "operator": "contains",
                "value": "lisinopril",
                "fhir_resource": "MedicationStatement",
                "fhir_path": "MedicationStatement.medicationCodeableConcept",
                "status": "active"
            },
            {
                "type": "exclusion",
                "category": "allergy",
                "description": "No allergy to ACE inhibitors",
                "attribute": "allergen",
                "operator": "not_contains",
                "value": "ACE inhibitor",
                "fhir_resource": "AllergyIntolerance",
                "fhir_path": "AllergyIntolerance.code"
            }
        ]
    },
    {
        "trial_id": "LUNG-CANCER-003",
        "title": "Non-Small Cell Lung Cancer Study",
        "description": "Advanced NSCLC with chemotherapy",
        "parsed_criteria": [
            {
                "type": "inclusion",
                "category": "demographics",
                "description": "Age between 18 and 75 years",
                "attribute": "age",
                "operator": "between",
                "value": [18, 75],
                "unit": "years",
                "fhir_resource": "Patient",
                "fhir_path": "Patient.birthDate"
            },
            {
                "type": "inclusion",
                "category": "condition",
                "description": "Non-small cell lung cancer",
                "attribute": "diagnosis",
                "operator": "contains",
                "value": "non-small cell lung cancer",
                "fhir_resource": "Condition",
                "fhir_path": "Condition.code",
                "coding": {
                    "system": "http://hl7.org/fhir/sid/icd-10-cm",
                    "code": "C34.90",
                    "display": "Malignant neoplasm of unspecified part of unspecified bronchus or lung"
                }
            },
            {
                "type": "inclusion",
                "category": "performance_status",
                "description": "ECOG performance status 0-1",
                "attribute": "ecog",
                "operator": "between",
                "value": [0, 1],
                "fhir_resource": "Observation",
                "fhir_path": "Observation.valueInteger",
                "coding": {
                    "system": "http://loinc.org",
                    "code": "89247-1",
                    "display": "ECOG Performance Status"
                }
            },
            {
                "type": "inclusion",
                "category": "lab_value",
                "description": "Hemoglobin ≥9 g/dL",
                "attribute": "hemoglobin",
                "operator": "greater_than",
                "value": 9,
                "unit": "g/dL",
                "fhir_resource": "Observation",
                "fhir_path": "Observation.valueQuantity",
                "coding": {
                    "system": "http://loinc.org",
                    "code": "718-7",
                    "display": "Hemoglobin [Mass/volume] in Blood"
                }
            },
            {
                "type": "inclusion",
                "category": "procedure",
                "description": "Prior surgical resection",
                "attribute": "procedure_type",
                "operator": "contains",
                "value": "surgical resection",
                "fhir_resource": "Procedure",
                "fhir_path": "Procedure.code"
            },
            {
                "type": "exclusion",
                "category": "allergy",
                "description": "No allergy to platinum-based chemotherapy",
                "attribute": "allergen",
                "operator": "not_contains",
                "value": "cisplatin",
                "fhir_resource": "AllergyIntolerance",
                "fhir_path": "AllergyIntolerance.code"
            }
        ]
    },
    {
        "trial_id": "HEART-FAILURE-004",
        "title": "Chronic Heart Failure Management",
        "description": "HF with reduced ejection fraction",
        "parsed_criteria": [
            {
                "type": "inclusion",
                "category": "demographics",
                "description": "Age 50 years or older",
                "attribute": "age",
                "operator": "greater_than",
                "value": 50,
                "unit": "years",
                "fhir_resource": "Patient",
                "fhir_path": "Patient.birthDate"
            },
            {
                "type": "inclusion",
                "category": "condition",
                "description": "Chronic heart failure",
                "attribute": "diagnosis",
                "operator": "contains",
                "value": "heart failure",
                "fhir_resource": "Condition",
                "fhir_path": "Condition.code",
                "coding": {
                    "system": "http://hl7.org/fhir/sid/icd-10-cm",
                    "code": "I50",
                    "display": "Heart failure"
                }
            },
            {
                "type": "inclusion",
                "category": "medication",
                "description": "On beta-blocker therapy",
                "attribute": "medication_class",
                "operator": "contains",
                "value": "metoprolol",
                "fhir_resource": "MedicationStatement",
                "fhir_path": "MedicationStatement.medicationCodeableConcept",
                "status": "active"
            },
            {
                "type": "inclusion",
                "category": "procedure",
                "description": "Echocardiogram within 12 months",
                "attribute": "procedure_type",
                "operator": "contains",
                "value": "echocardiogram",
                "fhir_resource": "Procedure",
                "fhir_path": "Procedure.code"
            },
            {
                "type": "exclusion",
                "category": "condition",
                "description": "No recent myocardial infarction",
                "attribute": "diagnosis",
                "operator": "not_contains",
                "value": "myocardial infarction",
                "fhir_resource": "Condition",
                "fhir_path": "Condition.code"
            }
        ]
    },
    {
        "trial_id": "ASTHMA-005",
        "title": "Severe Asthma Biologic Therapy",
        "description": "Asthma with inadequate control",
        "parsed_criteria": [
            {
                "type": "inclusion",
                "category": "demographics",
                "description": "Age between 18 and 65 years",
                "attribute": "age",
                "operator": "between",
                "value": [18, 65],
                "unit": "years",
                "fhir_resource": "Patient",
                "fhir_path": "Patient.birthDate"
            },
            {
                "type": "inclusion",
                "category": "condition",
                "description": "Severe persistent asthma",
                "attribute": "diagnosis",
                "operator": "contains",
                "value": "asthma",
                "fhir_resource": "Condition",
                "fhir_path": "Condition.code",
                "coding": {
                    "system": "http://hl7.org/fhir/sid/icd-10-cm",
                    "code": "J45",
                    "display": "Asthma"
                }
            },
            {
                "type": "inclusion",
                "category": "medication",
                "description": "On high-dose inhaled corticosteroids",
                "attribute": "medication_class",
                "operator": "contains",
                "value": "fluticasone",
                "fhir_resource": "MedicationStatement",
                "fhir_path": "MedicationStatement.medicationCodeableConcept",
                "status": "active"
            },
            {
                "type": "inclusion",
                "category": "immunization",
                "description": "Influenza vaccination current",
                "attribute": "vaccine_type",
                "operator": "contains",
                "value": "influenza",
                "fhir_resource": "Immunization",
                "fhir_path": "Immunization.vaccineCode"
            },
            {
                "type": "exclusion",
                "category": "allergy",
                "description": "No allergy to monoclonal antibodies",
                "attribute": "allergen",
                "operator": "not_contains",
                "value": "monoclonal antibody",
                "fhir_resource": "AllergyIntolerance",
                "fhir_path": "AllergyIntolerance.code"
            }
        ]
    },
    {
        "trial_id": "ARTHRITIS-006",
        "title": "Rheumatoid Arthritis Treatment",
        "description": "Active RA requiring biologic therapy",
        "parsed_criteria": [
            {
                "type": "inclusion",
                "category": "demographics",
                "description": "Age between 18 and 75 years",
                "attribute": "age",
                "operator": "between",
                "value": [18, 75],
                "unit": "years",
                "fhir_resource": "Patient",
                "fhir_path": "Patient.birthDate"
            },
            {
                "type": "inclusion",
                "category": "condition",
                "description": "Rheumatoid arthritis",
                "attribute": "diagnosis",
                "operator": "contains",
                "value": "rheumatoid arthritis",
                "fhir_resource": "Condition",
                "fhir_path": "Condition.code",
                "coding": {
                    "system": "http://hl7.org/fhir/sid/icd-10-cm",
                    "code": "M06",
                    "display": "Rheumatoid arthritis"
                }
            },
            {
                "type": "inclusion",
                "category": "lab_value",
                "description": "WBC ≥3500/μL",
                "attribute": "wbc",
                "operator": "greater_than",
                "value": 3500,
                "unit": "/μL",
                "fhir_resource": "Observation",
                "fhir_path": "Observation.valueQuantity",
                "coding": {
                    "system": "http://loinc.org",
                    "code": "6690-2",
                    "display": "Leukocytes [#/volume] in Blood"
                }
            },
            {
                "type": "inclusion",
                "category": "immunization",
                "description": "MMR vaccination documented",
                "attribute": "vaccine_type",
                "operator": "contains",
                "value": "MMR",
                "fhir_resource": "Immunization",
                "fhir_path": "Immunization.vaccineCode"
            },
            {
                "type": "exclusion",
                "category": "allergy",
                "description": "No allergy to biologic agents",
                "attribute": "allergen",
                "operator": "not_contains",
                "value": "TNF inhibitor",
                "fhir_resource": "AllergyIntolerance",
                "fhir_path": "AllergyIntolerance.code"
            }
        ]
    },
    {
        "trial_id": "CKD-007",
        "title": "Chronic Kidney Disease Progression Study",
        "description": "CKD Stage 3b-4 management",
        "parsed_criteria": [
            {
                "type": "inclusion",
                "category": "demographics",
                "description": "Age between 30 and 80 years",
                "attribute": "age",
                "operator": "between",
                "value": [30, 80],
                "unit": "years",
                "fhir_resource": "Patient",
                "fhir_path": "Patient.birthDate"
            },
            {
                "type": "inclusion",
                "category": "condition",
                "description": "Chronic kidney disease",
                "attribute": "diagnosis",
                "operator": "contains",
                "value": "chronic kidney disease",
                "fhir_resource": "Condition",
                "fhir_path": "Condition.code",
                "coding": {
                    "system": "http://hl7.org/fhir/sid/icd-10-cm",
                    "code": "N18",
                    "display": "Chronic kidney disease"
                }
            },
            {
                "type": "inclusion",
                "category": "lab_value",
                "description": "Serum creatinine 2.0-5.0 mg/dL",
                "attribute": "creatinine",
                "operator": "between",
                "value": [2.0, 5.0],
                "unit": "mg/dL",
                "fhir_resource": "Observation",
                "fhir_path": "Observation.valueQuantity",
                "coding": {
                    "system": "http://loinc.org",
                    "code": "2160-0",
                    "display": "Creatinine [Mass/volume] in Serum or Plasma"
                }
            },
            {
                "type": "inclusion",
                "category": "medication",
                "description": "On ACE inhibitor or ARB",
                "attribute": "medication_class",
                "operator": "contains",
                "value": "lisinopril",
                "fhir_resource": "MedicationStatement",
                "fhir_path": "MedicationStatement.medicationCodeableConcept",
                "status": "active"
            },
            {
                "type": "exclusion",
                "category": "procedure",
                "description": "Not currently on dialysis",
                "attribute": "procedure_type",
                "operator": "not_exists",
                "value": "dialysis",
                "fhir_resource": "Procedure",
                "fhir_path": "Procedure.code"
            }
        ]
    },
    {
        "trial_id": "COPD-008",
        "title": "COPD Exacerbation Prevention",
        "description": "Moderate to severe COPD management",
        "parsed_criteria": [
            {
                "type": "inclusion",
                "category": "demographics",
                "description": "Age 45 years or older",
                "attribute": "age",
                "operator": "greater_than",
                "value": 45,
                "unit": "years",
                "fhir_resource": "Patient",
                "fhir_path": "Patient.birthDate"
            },
            {
                "type": "inclusion",
                "category": "condition",
                "description": "Chronic obstructive pulmonary disease",
                "attribute": "diagnosis",
                "operator": "contains",
                "value": "COPD",
                "fhir_resource": "Condition",
                "fhir_path": "Condition.code",
                "coding": {
                    "system": "http://hl7.org/fhir/sid/icd-10-cm",
                    "code": "J44",
                    "display": "Chronic obstructive pulmonary disease"
                }
            },
            {
                "type": "inclusion",
                "category": "medication",
                "description": "On bronchodilator therapy",
                "attribute": "medication_class",
                "operator": "contains",
                "value": "albuterol",
                "fhir_resource": "MedicationStatement",
                "fhir_path": "MedicationStatement.medicationCodeableConcept",
                "status": "active"
            },
            {
                "type": "inclusion",
                "category": "immunization",
                "description": "Pneumococcal vaccination",
                "attribute": "vaccine_type",
                "operator": "contains",
                "value": "pneumococcal",
                "fhir_resource": "Immunization",
                "fhir_path": "Immunization.vaccineCode"
            }
        ]
    },
    {
        "trial_id": "DEPRESSION-009",
        "title": "Treatment-Resistant Depression Study",
        "description": "Major depressive disorder not responding to SSRIs",
        "parsed_criteria": [
            {
                "type": "inclusion",
                "category": "demographics",
                "description": "Age between 18 and 65 years",
                "attribute": "age",
                "operator": "between",
                "value": [18, 65],
                "unit": "years",
                "fhir_resource": "Patient",
                "fhir_path": "Patient.birthDate"
            },
            {
                "type": "inclusion",
                "category": "condition",
                "description": "Major depressive disorder",
                "attribute": "diagnosis",
                "operator": "contains",
                "value": "major depressive disorder",
                "fhir_resource": "Condition",
                "fhir_path": "Condition.code",
                "coding": {
                    "system": "http://hl7.org/fhir/sid/icd-10-cm",
                    "code": "F33",
                    "display": "Major depressive disorder, recurrent"
                }
            },
            {
                "type": "inclusion",
                "category": "medication",
                "description": "Currently on SSRI or SNRI",
                "attribute": "medication_class",
                "operator": "contains",
                "value": "sertraline",
                "fhir_resource": "MedicationStatement",
                "fhir_path": "MedicationStatement.medicationCodeableConcept",
                "status": "active"
            },
            {
                "type": "exclusion",
                "category": "condition",
                "description": "No bipolar disorder",
                "attribute": "diagnosis",
                "operator": "not_contains",
                "value": "bipolar",
                "fhir_resource": "Condition",
                "fhir_path": "Condition.code"
            },
            {
                "type": "exclusion",
                "category": "allergy",
                "description": "No allergy to ketamine",
                "attribute": "allergen",
                "operator": "not_contains",
                "value": "ketamine",
                "fhir_resource": "AllergyIntolerance",
                "fhir_path": "AllergyIntolerance.code"
            }
        ]
    },
    {
        "trial_id": "PARKINSONS-010",
        "title": "Early Parkinson's Disease Study",
        "description": "Neuroprotection in early PD",
        "parsed_criteria": [
            {
                "type": "inclusion",
                "category": "demographics",
                "description": "Age between 30 and 80 years",
                "attribute": "age",
                "operator": "between",
                "value": [30, 80],
                "unit": "years",
                "fhir_resource": "Patient",
                "fhir_path": "Patient.birthDate"
            },
            {
                "type": "inclusion",
                "category": "condition",
                "description": "Parkinson's disease",
                "attribute": "diagnosis",
                "operator": "contains",
                "value": "Parkinson",
                "fhir_resource": "Condition",
                "fhir_path": "Condition.code",
                "coding": {
                    "system": "http://hl7.org/fhir/sid/icd-10-cm",
                    "code": "G20",
                    "display": "Parkinson's disease"
                }
            },
            {
                "type": "inclusion",
                "category": "medication",
                "description": "On levodopa/carbidopa",
                "attribute": "medication_name",
                "operator": "contains",
                "value": "levodopa",
                "fhir_resource": "MedicationStatement",
                "fhir_path": "MedicationStatement.medicationCodeableConcept",
                "status": "active"
            },
            {
                "type": "inclusion",
                "category": "diagnostic_report",
                "description": "Brain MRI excluding other causes",
                "attribute": "report_type",
                "operator": "contains",
                "value": "MRI brain",
                "fhir_resource": "DiagnosticReport",
                "fhir_path": "DiagnosticReport.code"
            },
            {
                "type": "inclusion",
                "category": "immunization",
                "description": "Pneumococcal vaccination",
                "attribute": "vaccine_type",
                "operator": "contains",
                "value": "pneumococcal",
                "fhir_resource": "Immunization",
                "fhir_path": "Immunization.vaccineCode"
            },
            {
                "type": "exclusion",
                "category": "procedure",
                "description": "No prior brain surgery",
                "attribute": "procedure_type",
                "operator": "not_exists",
                "value": "brain surgery",
                "fhir_resource": "Procedure",
                "fhir_path": "Procedure.code"
            },
            {
                "type": "exclusion",
                "category": "family_history",
                "description": "No family history of early-onset Parkinson's",
                "attribute": "condition",
                "operator": "not_contains",
                "value": "Parkinson",
                "fhir_resource": "FamilyMemberHistory",
                "fhir_path": "FamilyMemberHistory.condition.code"
            }
        ]
    }
]

def seed_protocol(protocol):
    """Seed a single protocol into DynamoDB."""
    try:
        # Convert to DynamoDB format
        item = {
            'trial_id': protocol['trial_id'],
            'parsed_criteria': convert_to_decimal(protocol['parsed_criteria']),
            'title': protocol.get('title', ''),
            'description': protocol.get('description', ''),
            'created_at': datetime.now().isoformat(),
            'ttl': int((datetime.now() + timedelta(days=90)).timestamp())
        }

        # Put item in DynamoDB
        table.put_item(Item=item)

        print(f"✅ Seeded: {protocol['trial_id']} - {protocol['title']}")
        print(f"   Criteria count: {len(protocol['parsed_criteria'])}")
        return True

    except Exception as e:
        print(f"❌ Error seeding {protocol['trial_id']}: {e}")
        return False

def main():
    """Seed all protocols."""
    print('='*80)
    print('SEEDING PRE-PARSED PROTOCOLS INTO CRITERIA CACHE')
    print('='*80)
    print(f'Table: {table_name}')
    print(f'Protocols to seed: {len(PROTOCOLS)}')
    print('='*80)
    print()

    success_count = 0
    fail_count = 0

    for protocol in PROTOCOLS:
        if seed_protocol(protocol):
            success_count += 1
        else:
            fail_count += 1
        print()

    print('='*80)
    print('SEEDING COMPLETE')
    print('='*80)
    print(f'✅ Successfully seeded: {success_count}/{len(PROTOCOLS)}')
    if fail_count > 0:
        print(f'❌ Failed: {fail_count}/{len(PROTOCOLS)}')
    print()

    # Verify
    print('Verifying table contents...')
    response = table.scan(Select='COUNT')
    print(f'Total items in table: {response["Count"]}')
    print('='*80)

if __name__ == '__main__':
    main()
