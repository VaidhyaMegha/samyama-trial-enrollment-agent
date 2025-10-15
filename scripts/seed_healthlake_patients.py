"""
Seed HealthLake with 30 comprehensive patients with all 11 FHIR resources
Designed to match against seeded protocol criteria with varying match percentages
"""
import boto3
import json
import os
import uuid
from datetime import datetime, timedelta
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
import requests
from dateutil.relativedelta import relativedelta

# Configuration
REGION = 'us-east-1'
DATASTORE_ID = os.getenv('HEALTHLAKE_DATASTORE_ID')
FHIR_ENDPOINT = f'https://healthlake.{REGION}.amazonaws.com/datastore/{DATASTORE_ID}/r4'

# Create session and credentials
session = boto3.Session()
credentials = session.get_credentials()

def make_signed_request(method, url, params=None, data=None):
    """Make an AWS Signature V4 signed request to HealthLake FHIR API."""
    headers = {'Content-Type': 'application/fhir+json'} if data else {}
    
    request = AWSRequest(method=method, url=url, params=params, data=data, headers=headers)
    SigV4Auth(credentials, 'healthlake', REGION).add_auth(request)
    
    prepped = request.prepare()
    
    response = requests.request(
        method=prepped.method,
        url=prepped.url,
        headers=dict(prepped.headers),
        data=prepped.body
    )
    
    return response

def calculate_birth_date(age):
    """Calculate birth date from age."""
    return (datetime.now() - relativedelta(years=age)).strftime('%Y-%m-%d')

# Define 30 diverse patients with complete FHIR resources
PATIENTS = [
    # Patient 1: 100% match for DIABETES-SIMPLE-001
    {
        "given_name": "John",
        "family_name": "Smith",
        "gender": "male",
        "age": 55,
        "identifier": "P001",
        "conditions": [
            {"code": "E11", "system": "ICD-10-CM", "display": "Type 2 diabetes mellitus"}
        ],
        "observations": [
            {"code": "4548-4", "system": "LOINC", "display": "Hemoglobin A1c", "value": 8.5, "unit": "%"},
            {"code": "718-7", "system": "LOINC", "display": "Hemoglobin", "value": 13.5, "unit": "g/dL"},
            {"code": "2160-0", "system": "LOINC", "display": "Creatinine", "value": 1.0, "unit": "mg/dL"}
        ],
        "medications": [
            {"name": "metformin", "code": "6809", "system": "RxNorm"}
        ],
        "allergies": [],
        "procedures": [],
        "immunizations": ["influenza"],
        "family_history": [],
        "diagnostic_reports": [],
        "care_plan": "Diabetes management with diet and metformin"
    },
    
    # Patient 2: 100% match for HYPERTENSION-002
    {
        "given_name": "Mary",
        "family_name": "Johnson",
        "gender": "female",
        "age": 62,
        "identifier": "P002",
        "conditions": [
            {"code": "I10", "system": "ICD-10-CM", "display": "Essential (primary) hypertension"}
        ],
        "observations": [
            {"code": "718-7", "system": "LOINC", "display": "Hemoglobin", "value": 12.8, "unit": "g/dL"}
        ],
        "medications": [
            {"name": "lisinopril", "code": "29046", "system": "RxNorm"}
        ],
        "allergies": [],
        "procedures": [],
        "immunizations": ["influenza"],
        "family_history": [],
        "diagnostic_reports": [],
        "care_plan": "Hypertension management with ACE inhibitor"
    },
    
    # Patient 3: 100% match for LUNG-CANCER-003
    {
        "given_name": "Robert",
        "family_name": "Williams",
        "gender": "male",
        "age": 68,
        "identifier": "P003",
        "conditions": [
            {"code": "C34.90", "system": "ICD-10-CM", "display": "Non-small cell lung cancer"}
        ],
        "observations": [
            {"code": "89247-1", "system": "LOINC", "display": "ECOG Performance Status", "value": 1, "unit": ""},
            {"code": "718-7", "system": "LOINC", "display": "Hemoglobin", "value": 11.5, "unit": "g/dL"}
        ],
        "medications": [
            {"name": "carboplatin", "code": "40048", "system": "RxNorm"}
        ],
        "allergies": [],
        "procedures": [
            {"code": "32480", "system": "CPT", "display": "Partial lung resection"}
        ],
        "immunizations": ["influenza"],
        "family_history": [],
        "diagnostic_reports": [
            {"code": "71250", "system": "CPT", "display": "CT chest"}
        ],
        "care_plan": "NSCLC treatment with chemotherapy post-resection"
    },
    
    # Patient 4: 80% match for DIABETES-SIMPLE-001 (missing metformin)
    {
        "given_name": "Jennifer",
        "family_name": "Brown",
        "gender": "female",
        "age": 48,
        "identifier": "P004",
        "conditions": [
            {"code": "E11", "system": "ICD-10-CM", "display": "Type 2 diabetes mellitus"}
        ],
        "observations": [
            {"code": "4548-4", "system": "LOINC", "display": "Hemoglobin A1c", "value": 7.8, "unit": "%"}
        ],
        "medications": [
            {"name": "glipizide", "code": "4815", "system": "RxNorm"}
        ],
        "allergies": [],
        "procedures": [],
        "immunizations": ["influenza"],
        "family_history": [
            {"relation": "mother", "condition": "Type 2 diabetes"}
        ],
        "diagnostic_reports": [],
        "care_plan": "Diabetes management with sulfonylurea"
    },
    
    # Patient 5: 100% match for HEART-FAILURE-004
    {
        "given_name": "Michael",
        "family_name": "Davis",
        "gender": "male",
        "age": 71,
        "identifier": "P005",
        "conditions": [
            {"code": "I50", "system": "ICD-10-CM", "display": "Heart failure"}
        ],
        "observations": [
            {"code": "718-7", "system": "LOINC", "display": "Hemoglobin", "value": 12.2, "unit": "g/dL"}
        ],
        "medications": [
            {"name": "metoprolol", "code": "6918", "system": "RxNorm"},
            {"name": "furosemide", "code": "4603", "system": "RxNorm"}
        ],
        "allergies": [],
        "procedures": [
            {"code": "93306", "system": "CPT", "display": "Echocardiogram"}
        ],
        "immunizations": ["pneumococcal", "influenza"],
        "family_history": [],
        "diagnostic_reports": [
            {"code": "93306", "system": "CPT", "display": "Echocardiogram report"}
        ],
        "care_plan": "Heart failure management with beta-blocker and diuretic"
    },
    
    # Patient 6: 100% match for ASTHMA-005
    {
        "given_name": "Lisa",
        "family_name": "Miller",
        "gender": "female",
        "age": 42,
        "identifier": "P006",
        "conditions": [
            {"code": "J45", "system": "ICD-10-CM", "display": "Asthma"}
        ],
        "observations": [],
        "medications": [
            {"name": "fluticasone", "code": "3104", "system": "RxNorm"},
            {"name": "albuterol", "code": "435", "system": "RxNorm"}
        ],
        "allergies": [],
        "procedures": [],
        "immunizations": ["influenza"],
        "family_history": [],
        "diagnostic_reports": [],
        "care_plan": "Asthma control with high-dose ICS and rescue inhaler"
    },
    
    # Patient 7: 100% match for ARTHRITIS-006
    {
        "given_name": "David",
        "family_name": "Wilson",
        "gender": "male",
        "age": 56,
        "identifier": "P007",
        "conditions": [
            {"code": "M06", "system": "ICD-10-CM", "display": "Rheumatoid arthritis"}
        ],
        "observations": [
            {"code": "6690-2", "system": "LOINC", "display": "WBC", "value": 7500, "unit": "/μL"}
        ],
        "medications": [
            {"name": "methotrexate", "code": "6851", "system": "RxNorm"}
        ],
        "allergies": [],
        "procedures": [],
        "immunizations": ["MMR", "influenza"],
        "family_history": [],
        "diagnostic_reports": [],
        "care_plan": "Rheumatoid arthritis treatment with DMARD"
    },
    
    # Patient 8: 100% match for CKD-007
    {
        "given_name": "Susan",
        "family_name": "Moore",
        "gender": "female",
        "age": 65,
        "identifier": "P008",
        "conditions": [
            {"code": "N18", "system": "ICD-10-CM", "display": "Chronic kidney disease"}
        ],
        "observations": [
            {"code": "2160-0", "system": "LOINC", "display": "Creatinine", "value": 3.2, "unit": "mg/dL"}
        ],
        "medications": [
            {"name": "lisinopril", "code": "29046", "system": "RxNorm"}
        ],
        "allergies": [],
        "procedures": [],
        "immunizations": ["influenza"],
        "family_history": [],
        "diagnostic_reports": [],
        "care_plan": "CKD stage 3b management with ACE inhibitor"
    },
    
    # Patient 9: 100% match for COPD-008
    {
        "given_name": "James",
        "family_name": "Taylor",
        "gender": "male",
        "age": 69,
        "identifier": "P009",
        "conditions": [
            {"code": "J44", "system": "ICD-10-CM", "display": "COPD"}
        ],
        "observations": [],
        "medications": [
            {"name": "albuterol", "code": "435", "system": "RxNorm"},
            {"name": "tiotropium", "code": "73274", "system": "RxNorm"}
        ],
        "allergies": [],
        "procedures": [],
        "immunizations": ["pneumococcal", "influenza"],
        "family_history": [],
        "diagnostic_reports": [],
        "care_plan": "COPD management with bronchodilators"
    },
    
    # Patient 10: 100% match for DEPRESSION-009
    {
        "given_name": "Patricia",
        "family_name": "Anderson",
        "gender": "female",
        "age": 45,
        "identifier": "P010",
        "conditions": [
            {"code": "F33", "system": "ICD-10-CM", "display": "Major depressive disorder, recurrent"}
        ],
        "observations": [],
        "medications": [
            {"name": "sertraline", "code": "36437", "system": "RxNorm"}
        ],
        "allergies": [],
        "procedures": [],
        "immunizations": ["influenza"],
        "family_history": [],
        "diagnostic_reports": [],
        "care_plan": "Treatment-resistant depression management with SSRI"
    },
    
    # Patients 11-20: 80% matches
    {
        "given_name": "Charles",
        "family_name": "Thomas",
        "gender": "male",
        "age": 58,
        "identifier": "P011",
        "conditions": [
            {"code": "E11", "system": "ICD-10-CM", "display": "Type 2 diabetes mellitus"},
            {"code": "I10", "system": "ICD-10-CM", "display": "Essential hypertension"}
        ],
        "observations": [
            {"code": "4548-4", "system": "LOINC", "display": "Hemoglobin A1c", "value": 9.2, "unit": "%"}
        ],
        "medications": [
            {"name": "metformin", "code": "6809", "system": "RxNorm"},
            {"name": "atorvastatin", "code": "83367", "system": "RxNorm"}
        ],
        "allergies": [],
        "procedures": [],
        "immunizations": ["influenza"],
        "family_history": [],
        "diagnostic_reports": [],
        "care_plan": "Diabetes and hypertension management"
    },
    
    {
        "given_name": "Barbara",
        "family_name": "Jackson",
        "gender": "female",
        "age": 53,
        "identifier": "P012",
        "conditions": [
            {"code": "I10", "system": "ICD-10-CM", "display": "Essential hypertension"},
            {"code": "E78.5", "system": "ICD-10-CM", "display": "Hyperlipidemia"}
        ],
        "observations": [],
        "medications": [
            {"name": "lisinopril", "code": "29046", "system": "RxNorm"},
            {"name": "atorvastatin", "code": "83367", "system": "RxNorm"}
        ],
        "allergies": [],
        "procedures": [],
        "immunizations": ["influenza"],
        "family_history": [
            {"relation": "father", "condition": "Heart disease"}
        ],
        "diagnostic_reports": [],
        "care_plan": "Cardiovascular risk management"
    },
    
    {
        "given_name": "Christopher",
        "family_name": "White",
        "gender": "male",
        "age": 64,
        "identifier": "P013",
        "conditions": [
            {"code": "C34.90", "system": "ICD-10-CM", "display": "Non-small cell lung cancer"}
        ],
        "observations": [
            {"code": "89247-1", "system": "LOINC", "display": "ECOG Performance Status", "value": 0, "unit": ""},
            {"code": "718-7", "system": "LOINC", "display": "Hemoglobin", "value": 12.5, "unit": "g/dL"}
        ],
        "medications": [],
        "allergies": [],
        "procedures": [
            {"code": "32480", "system": "CPT", "display": "Partial lung resection"}
        ],
        "immunizations": ["influenza"],
        "family_history": [],
        "diagnostic_reports": [
            {"code": "71250", "system": "CPT", "display": "CT chest"}
        ],
        "care_plan": "NSCLC post-surgical monitoring"
    },
    
    {
        "given_name": "Nancy",
        "family_name": "Harris",
        "gender": "female",
        "age": 49,
        "identifier": "P014",
        "conditions": [
            {"code": "J45", "system": "ICD-10-CM", "display": "Asthma"},
            {"code": "J30.1", "system": "ICD-10-CM", "display": "Allergic rhinitis"}
        ],
        "observations": [],
        "medications": [
            {"name": "fluticasone", "code": "3104", "system": "RxNorm"},
            {"name": "montelukast", "code": "30009", "system": "RxNorm"}
        ],
        "allergies": [
            {"code": "91936005", "system": "SNOMED-CT", "display": "Allergy to peanuts"}
        ],
        "procedures": [],
        "immunizations": ["influenza"],
        "family_history": [],
        "diagnostic_reports": [],
        "care_plan": "Asthma and allergic rhinitis management"
    },
    
    {
        "given_name": "Daniel",
        "family_name": "Martin",
        "gender": "male",
        "age": 72,
        "identifier": "P015",
        "conditions": [
            {"code": "I50", "system": "ICD-10-CM", "display": "Heart failure"},
            {"code": "I10", "system": "ICD-10-CM", "display": "Essential hypertension"}
        ],
        "observations": [],
        "medications": [
            {"name": "metoprolol", "code": "6918", "system": "RxNorm"},
            {"name": "furosemide", "code": "4603", "system": "RxNorm"},
            {"name": "lisinopril", "code": "29046", "system": "RxNorm"}
        ],
        "allergies": [],
        "procedures": [],
        "immunizations": ["pneumococcal", "influenza"],
        "family_history": [],
        "diagnostic_reports": [],
        "care_plan": "Heart failure with multiple medications"
    },
    
    {
        "given_name": "Jessica",
        "family_name": "Thompson",
        "gender": "female",
        "age": 38,
        "identifier": "P016",
        "conditions": [
            {"code": "M06", "system": "ICD-10-CM", "display": "Rheumatoid arthritis"}
        ],
        "observations": [
            {"code": "6690-2", "system": "LOINC", "display": "WBC", "value": 8200, "unit": "/μL"}
        ],
        "medications": [
            {"name": "methotrexate", "code": "6851", "system": "RxNorm"},
            {"name": "folic acid", "code": "4496", "system": "RxNorm"}
        ],
        "allergies": [],
        "procedures": [],
        "immunizations": ["influenza"],
        "family_history": [
            {"relation": "mother", "condition": "Rheumatoid arthritis"}
        ],
        "diagnostic_reports": [],
        "care_plan": "Active RA management with methotrexate"
    },
    
    {
        "given_name": "Matthew",
        "family_name": "Garcia",
        "gender": "male",
        "age": 67,
        "identifier": "P017",
        "conditions": [
            {"code": "N18", "system": "ICD-10-CM", "display": "Chronic kidney disease"},
            {"code": "E11", "system": "ICD-10-CM", "display": "Type 2 diabetes mellitus"}
        ],
        "observations": [
            {"code": "2160-0", "system": "LOINC", "display": "Creatinine", "value": 2.8, "unit": "mg/dL"},
            {"code": "4548-4", "system": "LOINC", "display": "Hemoglobin A1c", "value": 7.5, "unit": "%"}
        ],
        "medications": [
            {"name": "lisinopril", "code": "29046", "system": "RxNorm"},
            {"name": "metformin", "code": "6809", "system": "RxNorm"}
        ],
        "allergies": [],
        "procedures": [],
        "immunizations": ["influenza"],
        "family_history": [],
        "diagnostic_reports": [],
        "care_plan": "Diabetic nephropathy management"
    },
    
    {
        "given_name": "Sarah",
        "family_name": "Martinez",
        "gender": "female",
        "age": 61,
        "identifier": "P018",
        "conditions": [
            {"code": "J44", "system": "ICD-10-CM", "display": "COPD"}
        ],
        "observations": [],
        "medications": [
            {"name": "albuterol", "code": "435", "system": "RxNorm"}
        ],
        "allergies": [],
        "procedures": [],
        "immunizations": ["pneumococcal"],
        "family_history": [],
        "diagnostic_reports": [],
        "care_plan": "COPD management with bronchodilator only"
    },
    
    {
        "given_name": "Andrew",
        "family_name": "Robinson",
        "gender": "male",
        "age": 43,
        "identifier": "P019",
        "conditions": [
            {"code": "F33", "system": "ICD-10-CM", "display": "Major depressive disorder, recurrent"},
            {"code": "F41.1", "system": "ICD-10-CM", "display": "Generalized anxiety disorder"}
        ],
        "observations": [],
        "medications": [
            {"name": "sertraline", "code": "36437", "system": "RxNorm"},
            {"name": "buspirone", "code": "1827", "system": "RxNorm"}
        ],
        "allergies": [],
        "procedures": [],
        "immunizations": ["influenza"],
        "family_history": [
            {"relation": "sister", "condition": "Depression"}
        ],
        "diagnostic_reports": [],
        "care_plan": "Depression and anxiety management"
    },
    
    {
        "given_name": "Karen",
        "family_name": "Clark",
        "gender": "female",
        "age": 57,
        "identifier": "P020",
        "conditions": [
            {"code": "G20", "system": "ICD-10-CM", "display": "Parkinson's disease"}
        ],
        "observations": [],
        "medications": [
            {"name": "levodopa", "code": "6047", "system": "RxNorm"}
        ],
        "allergies": [],
        "procedures": [],
        "immunizations": ["pneumococcal", "influenza"],
        "family_history": [],
        "diagnostic_reports": [
            {"code": "70553", "system": "CPT", "display": "MRI brain"}
        ],
        "care_plan": "Early Parkinson's disease management"
    },
    
    # Patients 21-30: 60% matches or multi-protocol matches
    {
        "given_name": "Joseph",
        "family_name": "Rodriguez",
        "gender": "male",
        "age": 51,
        "identifier": "P021",
        "conditions": [
            {"code": "E11", "system": "ICD-10-CM", "display": "Type 2 diabetes mellitus"}
        ],
        "observations": [
            {"code": "4548-4", "system": "LOINC", "display": "Hemoglobin A1c", "value": 6.8, "unit": "%"}
        ],
        "medications": [
            {"name": "metformin", "code": "6809", "system": "RxNorm"}
        ],
        "allergies": [],
        "procedures": [],
        "immunizations": ["influenza"],
        "family_history": [],
        "diagnostic_reports": [],
        "care_plan": "Well-controlled diabetes"
    },
    
    {
        "given_name": "Betty",
        "family_name": "Lewis",
        "gender": "female",
        "age": 75,
        "identifier": "P022",
        "conditions": [
            {"code": "I10", "system": "ICD-10-CM", "display": "Essential hypertension"},
            {"code": "I50", "system": "ICD-10-CM", "display": "Heart failure"},
            {"code": "E11", "system": "ICD-10-CM", "display": "Type 2 diabetes mellitus"}
        ],
        "observations": [
            {"code": "4548-4", "system": "LOINC", "display": "Hemoglobin A1c", "value": 8.1, "unit": "%"}
        ],
        "medications": [
            {"name": "metformin", "code": "6809", "system": "RxNorm"},
            {"name": "lisinopril", "code": "29046", "system": "RxNorm"},
            {"name": "metoprolol", "code": "6918", "system": "RxNorm"}
        ],
        "allergies": [],
        "procedures": [],
        "immunizations": ["pneumococcal", "influenza"],
        "family_history": [],
        "diagnostic_reports": [],
        "care_plan": "Multiple chronic conditions management"
    },
    
    {
        "given_name": "Steven",
        "family_name": "Lee",
        "gender": "male",
        "age": 47,
        "identifier": "P023",
        "conditions": [
            {"code": "J45", "system": "ICD-10-CM", "display": "Asthma"}
        ],
        "observations": [],
        "medications": [
            {"name": "albuterol", "code": "435", "system": "RxNorm"}
        ],
        "allergies": [],
        "procedures": [],
        "immunizations": [],
        "family_history": [],
        "diagnostic_reports": [],
        "care_plan": "Mild asthma with rescue inhaler only"
    },
    
    {
        "given_name": "Donna",
        "family_name": "Walker",
        "gender": "female",
        "age": 59,
        "identifier": "P024",
        "conditions": [
            {"code": "M06", "system": "ICD-10-CM", "display": "Rheumatoid arthritis"},
            {"code": "M81.0", "system": "ICD-10-CM", "display": "Osteoporosis"}
        ],
        "observations": [
            {"code": "6690-2", "system": "LOINC", "display": "WBC", "value": 6800, "unit": "/μL"}
        ],
        "medications": [
            {"name": "hydroxychloroquine", "code": "5521", "system": "RxNorm"},
            {"name": "alendronate", "code": "18600", "system": "RxNorm"}
        ],
        "allergies": [],
        "procedures": [],
        "immunizations": ["MMR"],
        "family_history": [],
        "diagnostic_reports": [],
        "care_plan": "RA and osteoporosis management"
    },
    
    {
        "given_name": "Kenneth",
        "family_name": "Hall",
        "gender": "male",
        "age": 70,
        "identifier": "P025",
        "conditions": [
            {"code": "N18", "system": "ICD-10-CM", "display": "Chronic kidney disease"}
        ],
        "observations": [
            {"code": "2160-0", "system": "LOINC", "display": "Creatinine", "value": 4.8, "unit": "mg/dL"}
        ],
        "medications": [
            {"name": "lisinopril", "code": "29046", "system": "RxNorm"}
        ],
        "allergies": [],
        "procedures": [],
        "immunizations": ["influenza"],
        "family_history": [],
        "diagnostic_reports": [],
        "care_plan": "CKD stage 4 management"
    },
    
    {
        "given_name": "Margaret",
        "family_name": "Allen",
        "gender": "female",
        "age": 66,
        "identifier": "P026",
        "conditions": [
            {"code": "J44", "system": "ICD-10-CM", "display": "COPD"},
            {"code": "J45", "system": "ICD-10-CM", "display": "Asthma"}
        ],
        "observations": [],
        "medications": [
            {"name": "albuterol", "code": "435", "system": "RxNorm"},
            {"name": "fluticasone", "code": "3104", "system": "RxNorm"}
        ],
        "allergies": [],
        "procedures": [],
        "immunizations": ["pneumococcal", "influenza"],
        "family_history": [],
        "diagnostic_reports": [],
        "care_plan": "ACOS (Asthma-COPD overlap syndrome)"
    },
    
    {
        "given_name": "Edward",
        "family_name": "Young",
        "gender": "male",
        "age": 41,
        "identifier": "P027",
        "conditions": [
            {"code": "F33", "system": "ICD-10-CM", "display": "Major depressive disorder, recurrent"}
        ],
        "observations": [],
        "medications": [
            {"name": "escitalopram", "code": "321988", "system": "RxNorm"}
        ],
        "allergies": [],
        "procedures": [],
        "immunizations": [],
        "family_history": [],
        "diagnostic_reports": [],
        "care_plan": "Depression management with SSRI"
    },
    
    {
        "given_name": "Laura",
        "family_name": "Hernandez",
        "gender": "female",
        "age": 54,
        "identifier": "P028",
        "conditions": [
            {"code": "G20", "system": "ICD-10-CM", "display": "Parkinson's disease"}
        ],
        "observations": [],
        "medications": [
            {"name": "pramipexole", "code": "41493", "system": "RxNorm"}
        ],
        "allergies": [],
        "procedures": [],
        "immunizations": ["influenza"],
        "family_history": [
            {"relation": "father", "condition": "Parkinson's disease"}
        ],
        "diagnostic_reports": [],
        "care_plan": "Parkinson's with dopamine agonist"
    },
    
    {
        "given_name": "Paul",
        "family_name": "King",
        "gender": "male",
        "age": 63,
        "identifier": "P029",
        "conditions": [
            {"code": "I10", "system": "ICD-10-CM", "display": "Essential hypertension"},
            {"code": "E78.5", "system": "ICD-10-CM", "display": "Hyperlipidemia"}
        ],
        "observations": [],
        "medications": [
            {"name": "amlodipine", "code": "17767", "system": "RxNorm"},
            {"name": "atorvastatin", "code": "83367", "system": "RxNorm"}
        ],
        "allergies": [
            {"code": "91936005", "system": "SNOMED-CT", "display": "Allergy to ACE inhibitors"}
        ],
        "procedures": [],
        "immunizations": ["influenza"],
        "family_history": [],
        "diagnostic_reports": [],
        "care_plan": "Hypertension with calcium channel blocker"
    },
    
    {
        "given_name": "Helen",
        "family_name": "Wright",
        "gender": "female",
        "age": 52,
        "identifier": "P030",
        "conditions": [
            {"code": "C50.9", "system": "ICD-10-CM", "display": "Breast cancer"},
            {"code": "E11", "system": "ICD-10-CM", "display": "Type 2 diabetes mellitus"}
        ],
        "observations": [
            {"code": "4548-4", "system": "LOINC", "display": "Hemoglobin A1c", "value": 7.2, "unit": "%"},
            {"code": "718-7", "system": "LOINC", "display": "Hemoglobin", "value": 10.8, "unit": "g/dL"}
        ],
        "medications": [
            {"name": "metformin", "code": "6809", "system": "RxNorm"},
            {"name": "tamoxifen", "code": "10324", "system": "RxNorm"}
        ],
        "allergies": [],
        "procedures": [
            {"code": "19301", "system": "CPT", "display": "Mastectomy"}
        ],
        "immunizations": ["influenza"],
        "family_history": [
            {"relation": "mother", "condition": "Breast cancer"}
        ],
        "diagnostic_reports": [
            {"code": "77067", "system": "CPT", "display": "Mammogram"}
        ],
        "care_plan": "Breast cancer post-mastectomy with diabetes"
    }
]

print('Patient data file created successfully!')
print(f'Total patients defined: {len(PATIENTS)}')
