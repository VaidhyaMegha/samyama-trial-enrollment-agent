"""
Seed 40 Additional Pre-Parsed Protocols into Criteria Cache
Diverse medical specialties with varied FHIR resource coverage
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

# 40 Additional diverse protocols
PROTOCOLS = [
    {
        "trial_id": "MIGRAINE-011",
        "title": "Chronic Migraine Prevention Study",
        "description": "CGRP antagonist for migraine prevention",
        "parsed_criteria": [
            {"type": "inclusion", "category": "demographics", "description": "Age 18-65 years", "attribute": "age", "operator": "between", "value": [18, 65], "unit": "years", "fhir_resource": "Patient", "fhir_path": "Patient.birthDate"},
            {"type": "inclusion", "category": "condition", "description": "Chronic migraine diagnosis", "attribute": "diagnosis", "operator": "contains", "value": "chronic migraine", "fhir_resource": "Condition", "fhir_path": "Condition.code"},
            {"type": "inclusion", "category": "medication", "description": "Failed at least 2 preventive medications", "attribute": "medication_class", "operator": "contains", "value": "propranolol", "fhir_resource": "MedicationStatement", "fhir_path": "MedicationStatement.medicationCodeableConcept"},
            {"type": "exclusion", "category": "allergy", "description": "No allergy to CGRP antagonists", "attribute": "allergen", "operator": "not_contains", "value": "CGRP", "fhir_resource": "AllergyIntolerance", "fhir_path": "AllergyIntolerance.code"}
        ]
    },
    {
        "trial_id": "OSTEOPOROSIS-012",
        "title": "Postmenopausal Osteoporosis Treatment",
        "description": "Bone density improvement study",
        "parsed_criteria": [
            {"type": "inclusion", "category": "demographics", "description": "Female gender", "attribute": "gender", "operator": "equals", "value": "female", "fhir_resource": "Patient", "fhir_path": "Patient.gender"},
            {"type": "inclusion", "category": "demographics", "description": "Age 50-80 years", "attribute": "age", "operator": "between", "value": [50, 80], "unit": "years", "fhir_resource": "Patient", "fhir_path": "Patient.birthDate"},
            {"type": "inclusion", "category": "condition", "description": "Osteoporosis diagnosis", "attribute": "diagnosis", "operator": "contains", "value": "osteoporosis", "fhir_resource": "Condition", "fhir_path": "Condition.code"},
            {"type": "inclusion", "category": "diagnostic_report", "description": "DEXA scan showing T-score ≤-2.5", "attribute": "report_type", "operator": "contains", "value": "DEXA", "fhir_resource": "DiagnosticReport", "fhir_path": "DiagnosticReport.code"},
            {"type": "exclusion", "category": "allergy", "description": "No allergy to bisphosphonates", "attribute": "allergen", "operator": "not_contains", "value": "bisphosphonate", "fhir_resource": "AllergyIntolerance", "fhir_path": "AllergyIntolerance.code"}
        ]
    },
    {
        "trial_id": "HEPATITIS-C-013",
        "title": "Chronic Hepatitis C Direct-Acting Antiviral",
        "description": "HCV genotype 1 treatment",
        "parsed_criteria": [
            {"type": "inclusion", "category": "demographics", "description": "Age 18-75 years", "attribute": "age", "operator": "between", "value": [18, 75], "unit": "years", "fhir_resource": "Patient", "fhir_path": "Patient.birthDate"},
            {"type": "inclusion", "category": "condition", "description": "Chronic Hepatitis C", "attribute": "diagnosis", "operator": "contains", "value": "hepatitis C", "fhir_resource": "Condition", "fhir_path": "Condition.code"},
            {"type": "inclusion", "category": "lab_value", "description": "ALT ≤10x ULN", "attribute": "alt", "operator": "less_than", "value": 400, "unit": "U/L", "fhir_resource": "Observation", "fhir_path": "Observation.valueQuantity"},
            {"type": "inclusion", "category": "immunization", "description": "Hepatitis A vaccination", "attribute": "vaccine_type", "operator": "contains", "value": "hepatitis A", "fhir_resource": "Immunization", "fhir_path": "Immunization.vaccineCode"},
            {"type": "exclusion", "category": "condition", "description": "No decompensated cirrhosis", "attribute": "diagnosis", "operator": "not_contains", "value": "decompensated cirrhosis", "fhir_resource": "Condition", "fhir_path": "Condition.code"}
        ]
    },
    {
        "trial_id": "PSORIASIS-014",
        "title": "Moderate to Severe Psoriasis Biologic",
        "description": "IL-17 inhibitor study",
        "parsed_criteria": [
            {"type": "inclusion", "category": "demographics", "description": "Age 18-70 years", "attribute": "age", "operator": "between", "value": [18, 70], "unit": "years", "fhir_resource": "Patient", "fhir_path": "Patient.birthDate"},
            {"type": "inclusion", "category": "condition", "description": "Plaque psoriasis", "attribute": "diagnosis", "operator": "contains", "value": "psoriasis", "fhir_resource": "Condition", "fhir_path": "Condition.code"},
            {"type": "inclusion", "category": "medication", "description": "Failed topical therapy", "attribute": "medication_class", "operator": "contains", "value": "corticosteroid", "fhir_resource": "MedicationStatement", "fhir_path": "MedicationStatement.medicationCodeableConcept"},
            {"type": "exclusion", "category": "allergy", "description": "No allergy to biologics", "attribute": "allergen", "operator": "not_contains", "value": "biologic", "fhir_resource": "AllergyIntolerance", "fhir_path": "AllergyIntolerance.code"}
        ]
    },
    {
        "trial_id": "ALZHEIMERS-015",
        "title": "Mild Alzheimer's Disease Treatment",
        "description": "Amyloid-targeting antibody study",
        "parsed_criteria": [
            {"type": "inclusion", "category": "demographics", "description": "Age 60-85 years", "attribute": "age", "operator": "between", "value": [60, 85], "unit": "years", "fhir_resource": "Patient", "fhir_path": "Patient.birthDate"},
            {"type": "inclusion", "category": "condition", "description": "Mild cognitive impairment or Alzheimer's", "attribute": "diagnosis", "operator": "contains", "value": "Alzheimer", "fhir_resource": "Condition", "fhir_path": "Condition.code"},
            {"type": "inclusion", "category": "medication", "description": "On cholinesterase inhibitor", "attribute": "medication_name", "operator": "contains", "value": "donepezil", "fhir_resource": "MedicationStatement", "fhir_path": "MedicationStatement.medicationCodeableConcept"},
            {"type": "inclusion", "category": "diagnostic_report", "description": "Brain MRI within 12 months", "attribute": "report_type", "operator": "contains", "value": "MRI brain", "fhir_resource": "DiagnosticReport", "fhir_path": "DiagnosticReport.code"},
            {"type": "inclusion", "category": "immunization", "description": "Pneumococcal vaccination", "attribute": "vaccine_type", "operator": "contains", "value": "pneumococcal", "fhir_resource": "Immunization", "fhir_path": "Immunization.vaccineCode"}
        ]
    },
    {
        "trial_id": "PROSTATE-CANCER-016",
        "title": "Metastatic Prostate Cancer Hormone Therapy",
        "description": "Castration-resistant prostate cancer",
        "parsed_criteria": [
            {"type": "inclusion", "category": "demographics", "description": "Male gender", "attribute": "gender", "operator": "equals", "value": "male", "fhir_resource": "Patient", "fhir_path": "Patient.gender"},
            {"type": "inclusion", "category": "demographics", "description": "Age 50 years or older", "attribute": "age", "operator": "greater_than", "value": 50, "unit": "years", "fhir_resource": "Patient", "fhir_path": "Patient.birthDate"},
            {"type": "inclusion", "category": "condition", "description": "Metastatic prostate cancer", "attribute": "diagnosis", "operator": "contains", "value": "prostate cancer", "fhir_resource": "Condition", "fhir_path": "Condition.code"},
            {"type": "inclusion", "category": "lab_value", "description": "PSA >2 ng/mL", "attribute": "PSA", "operator": "greater_than", "value": 2, "unit": "ng/mL", "fhir_resource": "Observation", "fhir_path": "Observation.valueQuantity"},
            {"type": "inclusion", "category": "procedure", "description": "Prior radiation or surgery", "attribute": "procedure_type", "operator": "contains", "value": "radiation", "fhir_resource": "Procedure", "fhir_path": "Procedure.code"}
        ]
    },
    {
        "trial_id": "EPILEPSY-017",
        "title": "Refractory Epilepsy Management",
        "description": "Add-on antiepileptic therapy",
        "parsed_criteria": [
            {"type": "inclusion", "category": "demographics", "description": "Age 18-65 years", "attribute": "age", "operator": "between", "value": [18, 65], "unit": "years", "fhir_resource": "Patient", "fhir_path": "Patient.birthDate"},
            {"type": "inclusion", "category": "condition", "description": "Epilepsy diagnosis", "attribute": "diagnosis", "operator": "contains", "value": "epilepsy", "fhir_resource": "Condition", "fhir_path": "Condition.code"},
            {"type": "inclusion", "category": "medication", "description": "On at least 2 antiepileptic drugs", "attribute": "medication_class", "operator": "contains", "value": "levetiracetam", "fhir_resource": "MedicationStatement", "fhir_path": "MedicationStatement.medicationCodeableConcept"},
            {"type": "inclusion", "category": "diagnostic_report", "description": "EEG within 6 months", "attribute": "report_type", "operator": "contains", "value": "EEG", "fhir_resource": "DiagnosticReport", "fhir_path": "DiagnosticReport.code"}
        ]
    },
    {
        "trial_id": "ULCERATIVE-COLITIS-018",
        "title": "Moderate to Severe Ulcerative Colitis",
        "description": "JAK inhibitor for IBD",
        "parsed_criteria": [
            {"type": "inclusion", "category": "demographics", "description": "Age 18-70 years", "attribute": "age", "operator": "between", "value": [18, 70], "unit": "years", "fhir_resource": "Patient", "fhir_path": "Patient.birthDate"},
            {"type": "inclusion", "category": "condition", "description": "Ulcerative colitis", "attribute": "diagnosis", "operator": "contains", "value": "ulcerative colitis", "fhir_resource": "Condition", "fhir_path": "Condition.code"},
            {"type": "inclusion", "category": "lab_value", "description": "CRP ≥5 mg/L", "attribute": "CRP", "operator": "greater_than", "value": 5, "unit": "mg/L", "fhir_resource": "Observation", "fhir_path": "Observation.valueQuantity"},
            {"type": "inclusion", "category": "diagnostic_report", "description": "Colonoscopy within 6 months", "attribute": "report_type", "operator": "contains", "value": "colonoscopy", "fhir_resource": "DiagnosticReport", "fhir_path": "DiagnosticReport.code"},
            {"type": "inclusion", "category": "immunization", "description": "Hepatitis B vaccination", "attribute": "vaccine_type", "operator": "contains", "value": "hepatitis B", "fhir_resource": "Immunization", "fhir_path": "Immunization.vaccineCode"}
        ]
    },
    {
        "trial_id": "ANEMIA-019",
        "title": "Iron Deficiency Anemia Treatment",
        "description": "IV iron therapy study",
        "parsed_criteria": [
            {"type": "inclusion", "category": "demographics", "description": "Age 18 years or older", "attribute": "age", "operator": "greater_than", "value": 18, "unit": "years", "fhir_resource": "Patient", "fhir_path": "Patient.birthDate"},
            {"type": "inclusion", "category": "condition", "description": "Iron deficiency anemia", "attribute": "diagnosis", "operator": "contains", "value": "iron deficiency anemia", "fhir_resource": "Condition", "fhir_path": "Condition.code"},
            {"type": "inclusion", "category": "lab_value", "description": "Hemoglobin <10 g/dL", "attribute": "hemoglobin", "operator": "less_than", "value": 10, "unit": "g/dL", "fhir_resource": "Observation", "fhir_path": "Observation.valueQuantity"},
            {"type": "exclusion", "category": "allergy", "description": "No allergy to IV iron", "attribute": "allergen", "operator": "not_contains", "value": "iron", "fhir_resource": "AllergyIntolerance", "fhir_path": "AllergyIntolerance.code"}
        ]
    },
    {
        "trial_id": "THYROID-020",
        "title": "Hypothyroidism Dose Optimization",
        "description": "Levothyroxine therapy adjustment",
        "parsed_criteria": [
            {"type": "inclusion", "category": "demographics", "description": "Age 25-70 years", "attribute": "age", "operator": "between", "value": [25, 70], "unit": "years", "fhir_resource": "Patient", "fhir_path": "Patient.birthDate"},
            {"type": "inclusion", "category": "condition", "description": "Hypothyroidism", "attribute": "diagnosis", "operator": "contains", "value": "hypothyroidism", "fhir_resource": "Condition", "fhir_path": "Condition.code"},
            {"type": "inclusion", "category": "lab_value", "description": "TSH >5 mIU/L", "attribute": "TSH", "operator": "greater_than", "value": 5, "unit": "mIU/L", "fhir_resource": "Observation", "fhir_path": "Observation.valueQuantity"},
            {"type": "inclusion", "category": "medication", "description": "On levothyroxine", "attribute": "medication_name", "operator": "contains", "value": "levothyroxine", "fhir_resource": "MedicationStatement", "fhir_path": "MedicationStatement.medicationCodeableConcept"}
        ]
    },
    {
        "trial_id": "GOUT-021",
        "title": "Chronic Gout Management",
        "description": "Urate-lowering therapy study",
        "parsed_criteria": [
            {"type": "inclusion", "category": "demographics", "description": "Age 30 years or older", "attribute": "age", "operator": "greater_than", "value": 30, "unit": "years", "fhir_resource": "Patient", "fhir_path": "Patient.birthDate"},
            {"type": "inclusion", "category": "condition", "description": "Gout diagnosis", "attribute": "diagnosis", "operator": "contains", "value": "gout", "fhir_resource": "Condition", "fhir_path": "Condition.code"},
            {"type": "inclusion", "category": "lab_value", "description": "Uric acid >6 mg/dL", "attribute": "uric_acid", "operator": "greater_than", "value": 6, "unit": "mg/dL", "fhir_resource": "Observation", "fhir_path": "Observation.valueQuantity"},
            {"type": "inclusion", "category": "medication", "description": "On allopurinol or febuxostat", "attribute": "medication_name", "operator": "contains", "value": "allopurinol", "fhir_resource": "MedicationStatement", "fhir_path": "MedicationStatement.medicationCodeableConcept"}
        ]
    },
    {
        "trial_id": "ATRIAL-FIB-022",
        "title": "Atrial Fibrillation Anticoagulation",
        "description": "Novel oral anticoagulant study",
        "parsed_criteria": [
            {"type": "inclusion", "category": "demographics", "description": "Age 55 years or older", "attribute": "age", "operator": "greater_than", "value": 55, "unit": "years", "fhir_resource": "Patient", "fhir_path": "Patient.birthDate"},
            {"type": "inclusion", "category": "condition", "description": "Atrial fibrillation", "attribute": "diagnosis", "operator": "contains", "value": "atrial fibrillation", "fhir_resource": "Condition", "fhir_path": "Condition.code"},
            {"type": "inclusion", "category": "lab_value", "description": "Creatinine clearance ≥30 mL/min", "attribute": "creatinine_clearance", "operator": "greater_than", "value": 30, "unit": "mL/min", "fhir_resource": "Observation", "fhir_path": "Observation.valueQuantity"},
            {"type": "inclusion", "category": "diagnostic_report", "description": "EKG confirming atrial fibrillation", "attribute": "report_type", "operator": "contains", "value": "EKG", "fhir_resource": "DiagnosticReport", "fhir_path": "DiagnosticReport.code"},
            {"type": "exclusion", "category": "procedure", "description": "No recent major surgery", "attribute": "procedure_type", "operator": "not_exists", "value": "major surgery", "fhir_resource": "Procedure", "fhir_path": "Procedure.code"}
        ]
    },
    {
        "trial_id": "MACULAR-DEGEN-023",
        "title": "Wet Age-Related Macular Degeneration",
        "description": "Anti-VEGF intravitreal injection",
        "parsed_criteria": [
            {"type": "inclusion", "category": "demographics", "description": "Age 55 years or older", "attribute": "age", "operator": "greater_than", "value": 55, "unit": "years", "fhir_resource": "Patient", "fhir_path": "Patient.birthDate"},
            {"type": "inclusion", "category": "condition", "description": "Wet AMD", "attribute": "diagnosis", "operator": "contains", "value": "macular degeneration", "fhir_resource": "Condition", "fhir_path": "Condition.code"},
            {"type": "inclusion", "category": "diagnostic_report", "description": "OCT showing active CNV", "attribute": "report_type", "operator": "contains", "value": "OCT", "fhir_resource": "DiagnosticReport", "fhir_path": "DiagnosticReport.code"},
            {"type": "exclusion", "category": "allergy", "description": "No allergy to anti-VEGF agents", "attribute": "allergen", "operator": "not_contains", "value": "bevacizumab", "fhir_resource": "AllergyIntolerance", "fhir_path": "AllergyIntolerance.code"}
        ]
    },
    {
        "trial_id": "MULTIPLE-SCLEROSIS-024",
        "title": "Relapsing-Remitting Multiple Sclerosis",
        "description": "Disease-modifying therapy study",
        "parsed_criteria": [
            {"type": "inclusion", "category": "demographics", "description": "Age 18-55 years", "attribute": "age", "operator": "between", "value": [18, 55], "unit": "years", "fhir_resource": "Patient", "fhir_path": "Patient.birthDate"},
            {"type": "inclusion", "category": "condition", "description": "Relapsing-remitting MS", "attribute": "diagnosis", "operator": "contains", "value": "multiple sclerosis", "fhir_resource": "Condition", "fhir_path": "Condition.code"},
            {"type": "inclusion", "category": "diagnostic_report", "description": "Brain MRI showing lesions", "attribute": "report_type", "operator": "contains", "value": "MRI brain", "fhir_resource": "DiagnosticReport", "fhir_path": "DiagnosticReport.code"},
            {"type": "inclusion", "category": "medication", "description": "On interferon or glatiramer", "attribute": "medication_class", "operator": "contains", "value": "interferon", "fhir_resource": "MedicationStatement", "fhir_path": "MedicationStatement.medicationCodeableConcept"}
        ]
    },
    {
        "trial_id": "SLEEP-APNEA-025",
        "title": "Obstructive Sleep Apnea CPAP Study",
        "description": "CPAP adherence improvement",
        "parsed_criteria": [
            {"type": "inclusion", "category": "demographics", "description": "Age 30-70 years", "attribute": "age", "operator": "between", "value": [30, 70], "unit": "years", "fhir_resource": "Patient", "fhir_path": "Patient.birthDate"},
            {"type": "inclusion", "category": "condition", "description": "Obstructive sleep apnea", "attribute": "diagnosis", "operator": "contains", "value": "sleep apnea", "fhir_resource": "Condition", "fhir_path": "Condition.code"},
            {"type": "inclusion", "category": "diagnostic_report", "description": "Polysomnography showing AHI ≥15", "attribute": "report_type", "operator": "contains", "value": "sleep study", "fhir_resource": "DiagnosticReport", "fhir_path": "DiagnosticReport.code"},
            {"type": "exclusion", "category": "condition", "description": "No central sleep apnea", "attribute": "diagnosis", "operator": "not_contains", "value": "central sleep apnea", "fhir_resource": "Condition", "fhir_path": "Condition.code"}
        ]
    },
    {
        "trial_id": "BREAST-CANCER-026",
        "title": "Early Stage Breast Cancer Adjuvant",
        "description": "HER2-positive breast cancer",
        "parsed_criteria": [
            {"type": "inclusion", "category": "demographics", "description": "Female gender", "attribute": "gender", "operator": "equals", "value": "female", "fhir_resource": "Patient", "fhir_path": "Patient.gender"},
            {"type": "inclusion", "category": "demographics", "description": "Age 18-75 years", "attribute": "age", "operator": "between", "value": [18, 75], "unit": "years", "fhir_resource": "Patient", "fhir_path": "Patient.birthDate"},
            {"type": "inclusion", "category": "condition", "description": "Breast cancer", "attribute": "diagnosis", "operator": "contains", "value": "breast cancer", "fhir_resource": "Condition", "fhir_path": "Condition.code"},
            {"type": "inclusion", "category": "procedure", "description": "Prior surgical resection", "attribute": "procedure_type", "operator": "contains", "value": "mastectomy", "fhir_resource": "Procedure", "fhir_path": "Procedure.code"},
            {"type": "inclusion", "category": "performance_status", "description": "ECOG 0-1", "attribute": "ecog", "operator": "between", "value": [0, 1], "fhir_resource": "Observation", "fhir_path": "Observation.valueInteger"}
        ]
    },
    {
        "trial_id": "PANCREATITIS-027",
        "title": "Chronic Pancreatitis Pain Management",
        "description": "Enzyme replacement therapy",
        "parsed_criteria": [
            {"type": "inclusion", "category": "demographics", "description": "Age 25-70 years", "attribute": "age", "operator": "between", "value": [25, 70], "unit": "years", "fhir_resource": "Patient", "fhir_path": "Patient.birthDate"},
            {"type": "inclusion", "category": "condition", "description": "Chronic pancreatitis", "attribute": "diagnosis", "operator": "contains", "value": "chronic pancreatitis", "fhir_resource": "Condition", "fhir_path": "Condition.code"},
            {"type": "inclusion", "category": "diagnostic_report", "description": "CT or MRI showing pancreatic changes", "attribute": "report_type", "operator": "contains", "value": "CT abdomen", "fhir_resource": "DiagnosticReport", "fhir_path": "DiagnosticReport.code"},
            {"type": "exclusion", "category": "condition", "description": "No pancreatic cancer", "attribute": "diagnosis", "operator": "not_contains", "value": "pancreatic cancer", "fhir_resource": "Condition", "fhir_path": "Condition.code"}
        ]
    },
    {
        "trial_id": "BIPOLAR-028",
        "title": "Bipolar Disorder Mood Stabilization",
        "description": "Atypical antipsychotic adjunct",
        "parsed_criteria": [
            {"type": "inclusion", "category": "demographics", "description": "Age 18-65 years", "attribute": "age", "operator": "between", "value": [18, 65], "unit": "years", "fhir_resource": "Patient", "fhir_path": "Patient.birthDate"},
            {"type": "inclusion", "category": "condition", "description": "Bipolar I or II disorder", "attribute": "diagnosis", "operator": "contains", "value": "bipolar", "fhir_resource": "Condition", "fhir_path": "Condition.code"},
            {"type": "inclusion", "category": "medication", "description": "On mood stabilizer", "attribute": "medication_class", "operator": "contains", "value": "lithium", "fhir_resource": "MedicationStatement", "fhir_path": "MedicationStatement.medicationCodeableConcept"},
            {"type": "inclusion", "category": "lab_value", "description": "TSH within normal limits", "attribute": "TSH", "operator": "between", "value": [0.5, 5.0], "unit": "mIU/L", "fhir_resource": "Observation", "fhir_path": "Observation.valueQuantity"}
        ]
    },
    {
        "trial_id": "LUPUS-029",
        "title": "Systemic Lupus Erythematosus Biologic",
        "description": "Belimumab for active SLE",
        "parsed_criteria": [
            {"type": "inclusion", "category": "demographics", "description": "Age 18-65 years", "attribute": "age", "operator": "between", "value": [18, 65], "unit": "years", "fhir_resource": "Patient", "fhir_path": "Patient.birthDate"},
            {"type": "inclusion", "category": "condition", "description": "Systemic lupus erythematosus", "attribute": "diagnosis", "operator": "contains", "value": "lupus", "fhir_resource": "Condition", "fhir_path": "Condition.code"},
            {"type": "inclusion", "category": "lab_value", "description": "Positive ANA", "attribute": "ANA", "operator": "greater_than", "value": 80, "unit": "titer", "fhir_resource": "Observation", "fhir_path": "Observation.valueQuantity"},
            {"type": "inclusion", "category": "medication", "description": "On hydroxychloroquine", "attribute": "medication_name", "operator": "contains", "value": "hydroxychloroquine", "fhir_resource": "MedicationStatement", "fhir_path": "MedicationStatement.medicationCodeableConcept"},
            {"type": "inclusion", "category": "immunization", "description": "MMR vaccination", "attribute": "vaccine_type", "operator": "contains", "value": "MMR", "fhir_resource": "Immunization", "fhir_path": "Immunization.vaccineCode"}
        ]
    },
    {
        "trial_id": "GLAUCOMA-030",
        "title": "Primary Open-Angle Glaucoma",
        "description": "IOP-lowering medication study",
        "parsed_criteria": [
            {"type": "inclusion", "category": "demographics", "description": "Age 40 years or older", "attribute": "age", "operator": "greater_than", "value": 40, "unit": "years", "fhir_resource": "Patient", "fhir_path": "Patient.birthDate"},
            {"type": "inclusion", "category": "condition", "description": "Primary open-angle glaucoma", "attribute": "diagnosis", "operator": "contains", "value": "glaucoma", "fhir_resource": "Condition", "fhir_path": "Condition.code"},
            {"type": "inclusion", "category": "medication", "description": "On topical prostaglandin", "attribute": "medication_class", "operator": "contains", "value": "latanoprost", "fhir_resource": "MedicationStatement", "fhir_path": "MedicationStatement.medicationCodeableConcept"},
            {"type": "inclusion", "category": "diagnostic_report", "description": "Visual field test within 6 months", "attribute": "report_type", "operator": "contains", "value": "visual field", "fhir_resource": "DiagnosticReport", "fhir_path": "DiagnosticReport.code"}
        ]
    },
    {
        "trial_id": "ENDOMETRIOSIS-031",
        "title": "Endometriosis Pain Management",
        "description": "GnRH antagonist therapy",
        "parsed_criteria": [
            {"type": "inclusion", "category": "demographics", "description": "Female gender", "attribute": "gender", "operator": "equals", "value": "female", "fhir_resource": "Patient", "fhir_path": "Patient.gender"},
            {"type": "inclusion", "category": "demographics", "description": "Age 18-45 years", "attribute": "age", "operator": "between", "value": [18, 45], "unit": "years", "fhir_resource": "Patient", "fhir_path": "Patient.birthDate"},
            {"type": "inclusion", "category": "condition", "description": "Endometriosis", "attribute": "diagnosis", "operator": "contains", "value": "endometriosis", "fhir_resource": "Condition", "fhir_path": "Condition.code"},
            {"type": "inclusion", "category": "procedure", "description": "Surgically confirmed endometriosis", "attribute": "procedure_type", "operator": "contains", "value": "laparoscopy", "fhir_resource": "Procedure", "fhir_path": "Procedure.code"},
            {"type": "inclusion", "category": "immunization", "description": "HPV vaccination", "attribute": "vaccine_type", "operator": "contains", "value": "HPV", "fhir_resource": "Immunization", "fhir_path": "Immunization.vaccineCode"}
        ]
    },
    {
        "trial_id": "PERIPHERAL-ARTERY-032",
        "title": "Peripheral Artery Disease Claudication",
        "description": "Cilostazol for intermittent claudication",
        "parsed_criteria": [
            {"type": "inclusion", "category": "demographics", "description": "Age 50 years or older", "attribute": "age", "operator": "greater_than", "value": 50, "unit": "years", "fhir_resource": "Patient", "fhir_path": "Patient.birthDate"},
            {"type": "inclusion", "category": "condition", "description": "Peripheral artery disease", "attribute": "diagnosis", "operator": "contains", "value": "peripheral artery disease", "fhir_resource": "Condition", "fhir_path": "Condition.code"},
            {"type": "inclusion", "category": "diagnostic_report", "description": "Ankle-brachial index <0.9", "attribute": "report_type", "operator": "contains", "value": "ABI", "fhir_resource": "DiagnosticReport", "fhir_path": "DiagnosticReport.code"},
            {"type": "inclusion", "category": "medication", "description": "On antiplatelet therapy", "attribute": "medication_class", "operator": "contains", "value": "aspirin", "fhir_resource": "MedicationStatement", "fhir_path": "MedicationStatement.medicationCodeableConcept"}
        ]
    },
    {
        "trial_id": "PEANUT-ALLERGY-033",
        "title": "Peanut Allergy Oral Immunotherapy",
        "description": "Desensitization study for children",
        "parsed_criteria": [
            {"type": "inclusion", "category": "demographics", "description": "Age 4-17 years", "attribute": "age", "operator": "between", "value": [4, 17], "unit": "years", "fhir_resource": "Patient", "fhir_path": "Patient.birthDate"},
            {"type": "inclusion", "category": "allergy", "description": "Peanut allergy", "attribute": "allergen", "operator": "contains", "value": "peanut", "fhir_resource": "AllergyIntolerance", "fhir_path": "AllergyIntolerance.code"},
            {"type": "inclusion", "category": "medication", "description": "Carries epinephrine auto-injector", "attribute": "medication_name", "operator": "contains", "value": "epinephrine", "fhir_resource": "MedicationStatement", "fhir_path": "MedicationStatement.medicationCodeableConcept"},
            {"type": "inclusion", "category": "immunization", "description": "All childhood vaccines up-to-date", "attribute": "vaccine_type", "operator": "contains", "value": "MMR", "fhir_resource": "Immunization", "fhir_path": "Immunization.vaccineCode"}
        ]
    },
    {
        "trial_id": "HEMOPHILIA-034",
        "title": "Hemophilia A Prophylaxis",
        "description": "Factor VIII replacement therapy",
        "parsed_criteria": [
            {"type": "inclusion", "category": "demographics", "description": "Age 12 years or older", "attribute": "age", "operator": "greater_than", "value": 12, "unit": "years", "fhir_resource": "Patient", "fhir_path": "Patient.birthDate"},
            {"type": "inclusion", "category": "condition", "description": "Hemophilia A", "attribute": "diagnosis", "operator": "contains", "value": "hemophilia A", "fhir_resource": "Condition", "fhir_path": "Condition.code"},
            {"type": "inclusion", "category": "lab_value", "description": "Factor VIII <5%", "attribute": "factor_VIII", "operator": "less_than", "value": 5, "unit": "%", "fhir_resource": "Observation", "fhir_path": "Observation.valueQuantity"},
            {"type": "inclusion", "category": "immunization", "description": "Hepatitis A and B vaccines", "attribute": "vaccine_type", "operator": "contains", "value": "hepatitis B", "fhir_resource": "Immunization", "fhir_path": "Immunization.vaccineCode"}
        ]
    },
    {
        "trial_id": "ACNE-035",
        "title": "Severe Acne Isotretinoin Study",
        "description": "Oral isotretinoin for nodular acne",
        "parsed_criteria": [
            {"type": "inclusion", "category": "demographics", "description": "Age 15-40 years", "attribute": "age", "operator": "between", "value": [15, 40], "unit": "years", "fhir_resource": "Patient", "fhir_path": "Patient.birthDate"},
            {"type": "inclusion", "category": "condition", "description": "Severe nodular acne", "attribute": "diagnosis", "operator": "contains", "value": "acne", "fhir_resource": "Condition", "fhir_path": "Condition.code"},
            {"type": "inclusion", "category": "lab_value", "description": "ALT <2x ULN", "attribute": "alt", "operator": "less_than", "value": 80, "unit": "U/L", "fhir_resource": "Observation", "fhir_path": "Observation.valueQuantity"},
            {"type": "exclusion", "category": "condition", "description": "Not pregnant", "attribute": "pregnancy", "operator": "not_exists", "value": "pregnancy", "fhir_resource": "Condition", "fhir_path": "Condition.code"}
        ]
    },
    {
        "trial_id": "SICKLE-CELL-036",
        "title": "Sickle Cell Disease Vaso-Occlusive Crisis",
        "description": "Hydroxyurea dose optimization",
        "parsed_criteria": [
            {"type": "inclusion", "category": "demographics", "description": "Age 5 years or older", "attribute": "age", "operator": "greater_than", "value": 5, "unit": "years", "fhir_resource": "Patient", "fhir_path": "Patient.birthDate"},
            {"type": "inclusion", "category": "condition", "description": "Sickle cell disease", "attribute": "diagnosis", "operator": "contains", "value": "sickle cell", "fhir_resource": "Condition", "fhir_path": "Condition.code"},
            {"type": "inclusion", "category": "lab_value", "description": "Hemoglobin 7-10 g/dL", "attribute": "hemoglobin", "operator": "between", "value": [7, 10], "unit": "g/dL", "fhir_resource": "Observation", "fhir_path": "Observation.valueQuantity"},
            {"type": "inclusion", "category": "medication", "description": "On hydroxyurea", "attribute": "medication_name", "operator": "contains", "value": "hydroxyurea", "fhir_resource": "MedicationStatement", "fhir_path": "MedicationStatement.medicationCodeableConcept"}
        ]
    },
    {
        "trial_id": "GASTROPARESIS-037",
        "title": "Diabetic Gastroparesis Management",
        "description": "Prokinetic agent study",
        "parsed_criteria": [
            {"type": "inclusion", "category": "demographics", "description": "Age 18 years or older", "attribute": "age", "operator": "greater_than", "value": 18, "unit": "years", "fhir_resource": "Patient", "fhir_path": "Patient.birthDate"},
            {"type": "inclusion", "category": "condition", "description": "Gastroparesis", "attribute": "diagnosis", "operator": "contains", "value": "gastroparesis", "fhir_resource": "Condition", "fhir_path": "Condition.code"},
            {"type": "inclusion", "category": "condition", "description": "Diabetes mellitus", "attribute": "diagnosis", "operator": "contains", "value": "diabetes", "fhir_resource": "Condition", "fhir_path": "Condition.code"},
            {"type": "inclusion", "category": "diagnostic_report", "description": "Gastric emptying study showing delay", "attribute": "report_type", "operator": "contains", "value": "gastric emptying", "fhir_resource": "DiagnosticReport", "fhir_path": "DiagnosticReport.code"}
        ]
    },
    {
        "trial_id": "NEUROPATHY-038",
        "title": "Diabetic Peripheral Neuropathy Pain",
        "description": "Pregabalin for neuropathic pain",
        "parsed_criteria": [
            {"type": "inclusion", "category": "demographics", "description": "Age 30 years or older", "attribute": "age", "operator": "greater_than", "value": 30, "unit": "years", "fhir_resource": "Patient", "fhir_path": "Patient.birthDate"},
            {"type": "inclusion", "category": "condition", "description": "Diabetic peripheral neuropathy", "attribute": "diagnosis", "operator": "contains", "value": "diabetic neuropathy", "fhir_resource": "Condition", "fhir_path": "Condition.code"},
            {"type": "inclusion", "category": "condition", "description": "Diabetes mellitus", "attribute": "diagnosis", "operator": "contains", "value": "diabetes", "fhir_resource": "Condition", "fhir_path": "Condition.code"},
            {"type": "inclusion", "category": "lab_value", "description": "HbA1c <10%", "attribute": "HbA1c", "operator": "less_than", "value": 10, "unit": "%", "fhir_resource": "Observation", "fhir_path": "Observation.valueQuantity"}
        ]
    },
    {
        "trial_id": "OSTEOARTHRITIS-039",
        "title": "Knee Osteoarthritis Viscosupplementation",
        "description": "Hyaluronic acid injection study",
        "parsed_criteria": [
            {"type": "inclusion", "category": "demographics", "description": "Age 45-75 years", "attribute": "age", "operator": "between", "value": [45, 75], "unit": "years", "fhir_resource": "Patient", "fhir_path": "Patient.birthDate"},
            {"type": "inclusion", "category": "condition", "description": "Knee osteoarthritis", "attribute": "diagnosis", "operator": "contains", "value": "osteoarthritis knee", "fhir_resource": "Condition", "fhir_path": "Condition.code"},
            {"type": "inclusion", "category": "diagnostic_report", "description": "Knee X-ray showing OA changes", "attribute": "report_type", "operator": "contains", "value": "X-ray knee", "fhir_resource": "DiagnosticReport", "fhir_path": "DiagnosticReport.code"},
            {"type": "exclusion", "category": "allergy", "description": "No allergy to hyaluronic acid", "attribute": "allergen", "operator": "not_contains", "value": "hyaluronic acid", "fhir_resource": "AllergyIntolerance", "fhir_path": "AllergyIntolerance.code"}
        ]
    },
    {
        "trial_id": "ADHD-040",
        "title": "Adult ADHD Medication Management",
        "description": "Stimulant vs non-stimulant therapy",
        "parsed_criteria": [
            {"type": "inclusion", "category": "demographics", "description": "Age 18-55 years", "attribute": "age", "operator": "between", "value": [18, 55], "unit": "years", "fhir_resource": "Patient", "fhir_path": "Patient.birthDate"},
            {"type": "inclusion", "category": "condition", "description": "ADHD diagnosis", "attribute": "diagnosis", "operator": "contains", "value": "ADHD", "fhir_resource": "Condition", "fhir_path": "Condition.code"},
            {"type": "inclusion", "category": "medication", "description": "On methylphenidate or atomoxetine", "attribute": "medication_class", "operator": "contains", "value": "methylphenidate", "fhir_resource": "MedicationStatement", "fhir_path": "MedicationStatement.medicationCodeableConcept"},
            {"type": "exclusion", "category": "condition", "description": "No active substance use disorder", "attribute": "diagnosis", "operator": "not_contains", "value": "substance use", "fhir_resource": "Condition", "fhir_path": "Condition.code"}
        ]
    },
    {
        "trial_id": "PNEUMONIA-041",
        "title": "Community-Acquired Pneumonia Treatment",
        "description": "Antibiotic therapy comparison",
        "parsed_criteria": [
            {"type": "inclusion", "category": "demographics", "description": "Age 18 years or older", "attribute": "age", "operator": "greater_than", "value": 18, "unit": "years", "fhir_resource": "Patient", "fhir_path": "Patient.birthDate"},
            {"type": "inclusion", "category": "condition", "description": "Community-acquired pneumonia", "attribute": "diagnosis", "operator": "contains", "value": "pneumonia", "fhir_resource": "Condition", "fhir_path": "Condition.code"},
            {"type": "inclusion", "category": "diagnostic_report", "description": "Chest X-ray showing infiltrate", "attribute": "report_type", "operator": "contains", "value": "chest X-ray", "fhir_resource": "DiagnosticReport", "fhir_path": "DiagnosticReport.code"},
            {"type": "inclusion", "category": "immunization", "description": "Pneumococcal vaccination", "attribute": "vaccine_type", "operator": "contains", "value": "pneumococcal", "fhir_resource": "Immunization", "fhir_path": "Immunization.vaccineCode"}
        ]
    },
    {
        "trial_id": "UTI-042",
        "title": "Recurrent Urinary Tract Infections",
        "description": "Prophylactic antibiotic study",
        "parsed_criteria": [
            {"type": "inclusion", "category": "demographics", "description": "Female gender", "attribute": "gender", "operator": "equals", "value": "female", "fhir_resource": "Patient", "fhir_path": "Patient.gender"},
            {"type": "inclusion", "category": "demographics", "description": "Age 18-65 years", "attribute": "age", "operator": "between", "value": [18, 65], "unit": "years", "fhir_resource": "Patient", "fhir_path": "Patient.birthDate"},
            {"type": "inclusion", "category": "condition", "description": "Recurrent UTI", "attribute": "diagnosis", "operator": "contains", "value": "urinary tract infection", "fhir_resource": "Condition", "fhir_path": "Condition.code"},
            {"type": "exclusion", "category": "allergy", "description": "No allergy to sulfa drugs", "attribute": "allergen", "operator": "not_contains", "value": "sulfonamide", "fhir_resource": "AllergyIntolerance", "fhir_path": "AllergyIntolerance.code"}
        ]
    },
    {
        "trial_id": "ROSACEA-043",
        "title": "Moderate to Severe Rosacea",
        "description": "Topical ivermectin study",
        "parsed_criteria": [
            {"type": "inclusion", "category": "demographics", "description": "Age 18 years or older", "attribute": "age", "operator": "greater_than", "value": 18, "unit": "years", "fhir_resource": "Patient", "fhir_path": "Patient.birthDate"},
            {"type": "inclusion", "category": "condition", "description": "Rosacea", "attribute": "diagnosis", "operator": "contains", "value": "rosacea", "fhir_resource": "Condition", "fhir_path": "Condition.code"},
            {"type": "inclusion", "category": "medication", "description": "Failed topical metronidazole", "attribute": "medication_name", "operator": "contains", "value": "metronidazole", "fhir_resource": "MedicationStatement", "fhir_path": "MedicationStatement.medicationCodeableConcept"},
            {"type": "exclusion", "category": "allergy", "description": "No allergy to ivermectin", "attribute": "allergen", "operator": "not_contains", "value": "ivermectin", "fhir_resource": "AllergyIntolerance", "fhir_path": "AllergyIntolerance.code"}
        ]
    },
    {
        "trial_id": "CELLULITIS-044",
        "title": "Skin and Soft Tissue Infection",
        "description": "Outpatient antibiotic therapy",
        "parsed_criteria": [
            {"type": "inclusion", "category": "demographics", "description": "Age 18 years or older", "attribute": "age", "operator": "greater_than", "value": 18, "unit": "years", "fhir_resource": "Patient", "fhir_path": "Patient.birthDate"},
            {"type": "inclusion", "category": "condition", "description": "Cellulitis", "attribute": "diagnosis", "operator": "contains", "value": "cellulitis", "fhir_resource": "Condition", "fhir_path": "Condition.code"},
            {"type": "inclusion", "category": "lab_value", "description": "WBC <15,000/μL", "attribute": "wbc", "operator": "less_than", "value": 15000, "unit": "/μL", "fhir_resource": "Observation", "fhir_path": "Observation.valueQuantity"},
            {"type": "exclusion", "category": "allergy", "description": "No allergy to beta-lactams", "attribute": "allergen", "operator": "not_contains", "value": "penicillin", "fhir_resource": "AllergyIntolerance", "fhir_path": "AllergyIntolerance.code"}
        ]
    },
    {
        "trial_id": "SHINGLES-045",
        "title": "Herpes Zoster Prevention Study",
        "description": "Recombinant zoster vaccine",
        "parsed_criteria": [
            {"type": "inclusion", "category": "demographics", "description": "Age 50 years or older", "attribute": "age", "operator": "greater_than", "value": 50, "unit": "years", "fhir_resource": "Patient", "fhir_path": "Patient.birthDate"},
            {"type": "exclusion", "category": "condition", "description": "No active shingles", "attribute": "diagnosis", "operator": "not_contains", "value": "herpes zoster", "fhir_resource": "Condition", "fhir_path": "Condition.code"},
            {"type": "exclusion", "category": "immunization", "description": "No prior zoster vaccine", "attribute": "vaccine_type", "operator": "not_contains", "value": "zoster", "fhir_resource": "Immunization", "fhir_path": "Immunization.vaccineCode"},
            {"type": "exclusion", "category": "allergy", "description": "No vaccine allergies", "attribute": "allergen", "operator": "not_contains", "value": "vaccine", "fhir_resource": "AllergyIntolerance", "fhir_path": "AllergyIntolerance.code"}
        ]
    },
    {
        "trial_id": "VERTIGO-046",
        "title": "Benign Paroxysmal Positional Vertigo",
        "description": "Canalith repositioning study",
        "parsed_criteria": [
            {"type": "inclusion", "category": "demographics", "description": "Age 30 years or older", "attribute": "age", "operator": "greater_than", "value": 30, "unit": "years", "fhir_resource": "Patient", "fhir_path": "Patient.birthDate"},
            {"type": "inclusion", "category": "condition", "description": "BPPV diagnosis", "attribute": "diagnosis", "operator": "contains", "value": "vertigo", "fhir_resource": "Condition", "fhir_path": "Condition.code"},
            {"type": "inclusion", "category": "diagnostic_report", "description": "Positive Dix-Hallpike test", "attribute": "report_type", "operator": "contains", "value": "vestibular", "fhir_resource": "DiagnosticReport", "fhir_path": "DiagnosticReport.code"},
            {"type": "exclusion", "category": "condition", "description": "No Meniere's disease", "attribute": "diagnosis", "operator": "not_contains", "value": "Meniere", "fhir_resource": "Condition", "fhir_path": "Condition.code"}
        ]
    },
    {
        "trial_id": "ECZEMA-047",
        "title": "Moderate to Severe Atopic Dermatitis",
        "description": "Dupilumab biologic therapy",
        "parsed_criteria": [
            {"type": "inclusion", "category": "demographics", "description": "Age 12 years or older", "attribute": "age", "operator": "greater_than", "value": 12, "unit": "years", "fhir_resource": "Patient", "fhir_path": "Patient.birthDate"},
            {"type": "inclusion", "category": "condition", "description": "Atopic dermatitis", "attribute": "diagnosis", "operator": "contains", "value": "atopic dermatitis", "fhir_resource": "Condition", "fhir_path": "Condition.code"},
            {"type": "inclusion", "category": "medication", "description": "Failed topical corticosteroids", "attribute": "medication_class", "operator": "contains", "value": "corticosteroid", "fhir_resource": "MedicationStatement", "fhir_path": "MedicationStatement.medicationCodeableConcept"},
            {"type": "exclusion", "category": "allergy", "description": "No allergy to monoclonal antibodies", "attribute": "allergen", "operator": "not_contains", "value": "monoclonal antibody", "fhir_resource": "AllergyIntolerance", "fhir_path": "AllergyIntolerance.code"}
        ]
    },
    {
        "trial_id": "VITAMIN-D-048",
        "title": "Vitamin D Deficiency Treatment",
        "description": "High-dose ergocalciferol study",
        "parsed_criteria": [
            {"type": "inclusion", "category": "demographics", "description": "Age 18 years or older", "attribute": "age", "operator": "greater_than", "value": 18, "unit": "years", "fhir_resource": "Patient", "fhir_path": "Patient.birthDate"},
            {"type": "inclusion", "category": "lab_value", "description": "25-OH Vitamin D <20 ng/mL", "attribute": "vitamin_D", "operator": "less_than", "value": 20, "unit": "ng/mL", "fhir_resource": "Observation", "fhir_path": "Observation.valueQuantity"},
            {"type": "inclusion", "category": "lab_value", "description": "Calcium within normal limits", "attribute": "calcium", "operator": "between", "value": [8.5, 10.5], "unit": "mg/dL", "fhir_resource": "Observation", "fhir_path": "Observation.valueQuantity"},
            {"type": "exclusion", "category": "condition", "description": "No hyperparathyroidism", "attribute": "diagnosis", "operator": "not_contains", "value": "hyperparathyroidism", "fhir_resource": "Condition", "fhir_path": "Condition.code"}
        ]
    },
    {
        "trial_id": "RESTLESS-LEGS-049",
        "title": "Restless Legs Syndrome Treatment",
        "description": "Dopamine agonist therapy",
        "parsed_criteria": [
            {"type": "inclusion", "category": "demographics", "description": "Age 18 years or older", "attribute": "age", "operator": "greater_than", "value": 18, "unit": "years", "fhir_resource": "Patient", "fhir_path": "Patient.birthDate"},
            {"type": "inclusion", "category": "condition", "description": "Restless legs syndrome", "attribute": "diagnosis", "operator": "contains", "value": "restless legs", "fhir_resource": "Condition", "fhir_path": "Condition.code"},
            {"type": "inclusion", "category": "lab_value", "description": "Ferritin >50 ng/mL", "attribute": "ferritin", "operator": "greater_than", "value": 50, "unit": "ng/mL", "fhir_resource": "Observation", "fhir_path": "Observation.valueQuantity"},
            {"type": "exclusion", "category": "medication", "description": "Not on antipsychotics", "attribute": "medication_class", "operator": "not_contains", "value": "antipsychotic", "fhir_resource": "MedicationStatement", "fhir_path": "MedicationStatement.medicationCodeableConcept"}
        ]
    },
    {
        "trial_id": "CLOSTRIDIUM-050",
        "title": "Recurrent C. difficile Infection",
        "description": "Fecal microbiota transplant study",
        "parsed_criteria": [
            {"type": "inclusion", "category": "demographics", "description": "Age 18 years or older", "attribute": "age", "operator": "greater_than", "value": 18, "unit": "years", "fhir_resource": "Patient", "fhir_path": "Patient.birthDate"},
            {"type": "inclusion", "category": "condition", "description": "Recurrent C. difficile infection", "attribute": "diagnosis", "operator": "contains", "value": "clostridium difficile", "fhir_resource": "Condition", "fhir_path": "Condition.code"},
            {"type": "inclusion", "category": "medication", "description": "Failed vancomycin or fidaxomicin", "attribute": "medication_name", "operator": "contains", "value": "vancomycin", "fhir_resource": "MedicationStatement", "fhir_path": "MedicationStatement.medicationCodeableConcept"},
            {"type": "inclusion", "category": "diagnostic_report", "description": "Positive C. diff toxin assay", "attribute": "report_type", "operator": "contains", "value": "stool test", "fhir_resource": "DiagnosticReport", "fhir_path": "DiagnosticReport.code"}
        ]
    }
]

def seed_protocol(protocol):
    """Seed a single protocol into DynamoDB."""
    try:
        item = {
            'trial_id': protocol['trial_id'],
            'parsed_criteria': convert_to_decimal(protocol['parsed_criteria']),
            'title': protocol.get('title', ''),
            'description': protocol.get('description', ''),
            'created_at': datetime.now().isoformat(),
            'ttl': int((datetime.now() + timedelta(days=90)).timestamp())
        }

        table.put_item(Item=item)
        print(f"✅ {protocol['trial_id']:30} - {len(protocol['parsed_criteria'])} criteria")
        return True

    except Exception as e:
        print(f"❌ {protocol['trial_id']:30} - Error: {e}")
        return False

def main():
    print('='*80)
    print('SEEDING 40 ADDITIONAL PROTOCOLS')
    print('='*80)
    print(f'Protocols to seed: {len(PROTOCOLS)}')
    print('='*80)
    print()

    success_count = 0
    for protocol in PROTOCOLS:
        if seed_protocol(protocol):
            success_count += 1

    print()
    print('='*80)
    print(f'✅ Successfully seeded: {success_count}/{len(PROTOCOLS)}')
    print()

    # Verify
    response = table.scan(Select='COUNT')
    print(f'Total protocols in table: {response["Count"]}')
    print('='*80)

if __name__ == '__main__':
    main()
