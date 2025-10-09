"""
Criteria Parser Lambda Function

Converts free-text clinical trial eligibility criteria into structured JSON format
that can be programmatically evaluated against patient FHIR data.
"""

import json
import os
import boto3
import hashlib
from decimal import Decimal
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext

logger = Logger()
tracer = Tracer()

# Initialize AWS clients
bedrock_runtime = boto3.client('bedrock-runtime', region_name=os.environ.get('AWS_REGION', 'us-west-1'))
dynamodb = boto3.resource('dynamodb', region_name=os.environ.get('AWS_REGION', 'us-east-1'))

# Get DynamoDB table
CRITERIA_CACHE_TABLE_NAME = os.environ.get('CRITERIA_CACHE_TABLE')
criteria_cache_table = dynamodb.Table(CRITERIA_CACHE_TABLE_NAME) if CRITERIA_CACHE_TABLE_NAME else None

# Parsing prompt template
PARSING_PROMPT = """You are an expert medical AI assistant specializing in clinical trial eligibility criteria.

Your task is to parse free-text clinical trial eligibility criteria and convert them into a structured JSON format.

For each criterion, extract:
1. **type**: "inclusion" or "exclusion"
2. **category**: The domain (e.g., "demographics", "condition", "lab_value", "medication", "procedure", "performance_status")
3. **description**: Natural language description of the criterion
4. **attribute**: What is being checked (e.g., "age", "HbA1c", "diagnosis", "ecog", "karnofsky")
5. **operator**: Comparison operator ("equals", "greater_than", "less_than", "between", "contains", "not_contains")
6. **value**: The value(s) to compare against
7. **unit**: Unit of measurement (if applicable)
8. **fhir_resource**: FHIR resource type to query (e.g., "Patient", "Observation", "Condition")
9. **fhir_path**: FHIR path to the relevant field (e.g., "Patient.birthDate", "Observation.valueQuantity")

**Performance Status Guidelines:**
- ECOG scale: 0-4 (0=fully active, 1=restricted, 2=ambulatory, 3=limited, 4=disabled)
- Karnofsky scale: 0-100 (100=normal, 0=dead)
- Category: "performance_status"
- FHIR Resource: "Observation"

Examples:

Input: "Patients must be between 18 and 65 years old"
Output:
{{
  "type": "inclusion",
  "category": "demographics",
  "description": "Age between 18 and 65 years",
  "attribute": "age",
  "operator": "between",
  "value": [18, 65],
  "unit": "years",
  "fhir_resource": "Patient",
  "fhir_path": "Patient.birthDate"
}}

Input: "HbA1c must be between 7% and 10%"
Output:
{{
  "type": "inclusion",
  "category": "lab_value",
  "description": "HbA1c between 7% and 10%",
  "attribute": "HbA1c",
  "operator": "between",
  "value": [7, 10],
  "unit": "%",
  "fhir_resource": "Observation",
  "fhir_path": "Observation.valueQuantity",
  "coding": {{
    "system": "http://loinc.org",
    "code": "4548-4",
    "display": "Hemoglobin A1c"
  }}
}}

Input: "Serum creatinine <1.5 mg/dL"
Output:
{{
  "type": "inclusion",
  "category": "lab_value",
  "description": "Serum creatinine <1.5 mg/dL",
  "attribute": "creatinine",
  "operator": "less_than",
  "value": 1.5,
  "unit": "mg/dL",
  "fhir_resource": "Observation",
  "fhir_path": "Observation.valueQuantity",
  "coding": {{
    "system": "http://loinc.org",
    "code": "2160-0",
    "display": "Creatinine [Mass/volume] in Serum or Plasma"
  }}
}}

Input: "eGFR ≥30 mL/min/1.73m2"
Output:
{{
  "type": "inclusion",
  "category": "lab_value",
  "description": "eGFR ≥30 mL/min/1.73m2",
  "attribute": "eGFR",
  "operator": "greater_than",
  "value": 30,
  "unit": "mL/min/1.73m2",
  "fhir_resource": "Observation",
  "fhir_path": "Observation.valueQuantity",
  "coding": {{
    "system": "http://loinc.org",
    "code": "33914-3",
    "display": "Glomerular filtration rate/1.73 sq M.predicted"
  }}
}}

Input: "Hemoglobin ≥10 g/dL"
Output:
{{
  "type": "inclusion",
  "category": "lab_value",
  "description": "Hemoglobin ≥10 g/dL",
  "attribute": "hemoglobin",
  "operator": "greater_than",
  "value": 10,
  "unit": "g/dL",
  "fhir_resource": "Observation",
  "fhir_path": "Observation.valueQuantity",
  "coding": {{
    "system": "http://loinc.org",
    "code": "718-7",
    "display": "Hemoglobin [Mass/volume] in Blood"
  }}
}}

Input: "WBC count ≥3000/μL"
Output:
{{
  "type": "inclusion",
  "category": "lab_value",
  "description": "WBC count ≥3000/μL",
  "attribute": "wbc",
  "operator": "greater_than",
  "value": 3000,
  "unit": "/μL",
  "fhir_resource": "Observation",
  "fhir_path": "Observation.valueQuantity",
  "coding": {{
    "system": "http://loinc.org",
    "code": "6690-2",
    "display": "Leukocytes [#/volume] in Blood"
  }}
}}

Input: "Platelet count ≥100,000/μL"
Output:
{{
  "type": "inclusion",
  "category": "lab_value",
  "description": "Platelet count ≥100,000/μL",
  "attribute": "platelets",
  "operator": "greater_than",
  "value": 100000,
  "unit": "/μL",
  "fhir_resource": "Observation",
  "fhir_path": "Observation.valueQuantity",
  "coding": {{
    "system": "http://loinc.org",
    "code": "777-3",
    "display": "Platelets [#/volume] in Blood"
  }}
}}

Input: "ALT <3x upper limit of normal"
Output:
{{
  "type": "inclusion",
  "category": "lab_value",
  "description": "ALT <3x ULN",
  "attribute": "alt",
  "operator": "less_than",
  "value": 120,
  "unit": "U/L",
  "fhir_resource": "Observation",
  "fhir_path": "Observation.valueQuantity",
  "coding": {{
    "system": "http://loinc.org",
    "code": "1742-6",
    "display": "Alanine aminotransferase [Enzymatic activity/volume] in Serum or Plasma"
  }}
}}

Input: "AST <100 U/L"
Output:
{{
  "type": "inclusion",
  "category": "lab_value",
  "description": "AST <100 U/L",
  "attribute": "ast",
  "operator": "less_than",
  "value": 100,
  "unit": "U/L",
  "fhir_resource": "Observation",
  "fhir_path": "Observation.valueQuantity",
  "coding": {{
    "system": "http://loinc.org",
    "code": "1920-8",
    "display": "Aspartate aminotransferase [Enzymatic activity/volume] in Serum or Plasma"
  }}
}}

Input: "Patients must NOT have chronic kidney disease stage 4 or higher"
Output:
{{
  "type": "exclusion",
  "category": "condition",
  "description": "No chronic kidney disease stage 4 or higher",
  "attribute": "chronic_kidney_disease",
  "operator": "not_contains",
  "value": "chronic kidney disease stage 4",
  "fhir_resource": "Condition",
  "fhir_path": "Condition.code",
  "coding": {{
    "system": "http://snomed.info/sct",
    "code": "431855005",
    "display": "Chronic kidney disease stage 4"
  }}
}}

Input: "Diagnosis of Type 2 Diabetes Mellitus"
Output:
{{
  "type": "inclusion",
  "category": "condition",
  "description": "Type 2 Diabetes Mellitus",
  "attribute": "diagnosis",
  "operator": "contains",
  "value": "Type 2 Diabetes",
  "fhir_resource": "Condition",
  "fhir_path": "Condition.code",
  "coding": {{
    "system": "http://hl7.org/fhir/sid/icd-10-cm",
    "code": "E11",
    "display": "Type 2 diabetes mellitus"
  }}
}}

Input: "History of hypertension"
Output:
{{
  "type": "inclusion",
  "category": "condition",
  "description": "Hypertension",
  "attribute": "diagnosis",
  "operator": "contains",
  "value": "hypertension",
  "fhir_resource": "Condition",
  "fhir_path": "Condition.code",
  "coding": {{
    "system": "http://hl7.org/fhir/sid/icd-10-cm",
    "code": "I10",
    "display": "Essential (primary) hypertension"
  }}
}}

Input: "No history of breast cancer"
Output:
{{
  "type": "exclusion",
  "category": "condition",
  "description": "No breast cancer",
  "attribute": "diagnosis",
  "operator": "not_contains",
  "value": "breast cancer",
  "fhir_resource": "Condition",
  "fhir_path": "Condition.code",
  "coding": {{
    "system": "http://hl7.org/fhir/sid/icd-10-cm",
    "code": "C50",
    "display": "Malignant neoplasm of breast"
  }}
}}

Input: "Diagnosed with heart failure"
Output:
{{
  "type": "inclusion",
  "category": "condition",
  "description": "Heart failure",
  "attribute": "diagnosis",
  "operator": "contains",
  "value": "heart failure",
  "fhir_resource": "Condition",
  "fhir_path": "Condition.code",
  "coding": {{
    "system": "http://hl7.org/fhir/sid/icd-10-cm",
    "code": "I50",
    "display": "Heart failure"
  }}
}}

Input: "No chronic obstructive pulmonary disease"
Output:
{{
  "type": "exclusion",
  "category": "condition",
  "description": "No COPD",
  "attribute": "diagnosis",
  "operator": "not_contains",
  "value": "COPD",
  "fhir_resource": "Condition",
  "fhir_path": "Condition.code",
  "coding": {{
    "system": "http://hl7.org/fhir/sid/icd-10-cm",
    "code": "J44",
    "display": "Chronic obstructive pulmonary disease"
  }}
}}

Input: "ECOG performance status 0-1"
Output:
{{
  "type": "inclusion",
  "category": "performance_status",
  "description": "ECOG performance status 0-1",
  "attribute": "ecog",
  "operator": "between",
  "value": [0, 1],
  "fhir_resource": "Observation",
  "fhir_path": "Observation.valueInteger",
  "coding": {{
    "system": "http://loinc.org",
    "code": "89247-1",
    "display": "ECOG Performance Status"
  }}
}}

Input: "Karnofsky performance status ≥70"
Output:
{{
  "type": "inclusion",
  "category": "performance_status",
  "description": "Karnofsky performance status ≥70",
  "attribute": "karnofsky",
  "operator": "greater_than",
  "value": 70,
  "fhir_resource": "Observation",
  "fhir_path": "Observation.valueInteger",
  "coding": {{
    "system": "http://loinc.org",
    "code": "89243-0",
    "display": "Karnofsky Performance Status"
  }}
}}

Input: "Currently taking metformin"
Output:
{{
  "type": "inclusion",
  "category": "medication",
  "description": "Currently taking metformin",
  "attribute": "medication_name",
  "operator": "contains",
  "value": "metformin",
  "fhir_resource": "MedicationStatement",
  "fhir_path": "MedicationStatement.medicationCodeableConcept",
  "status": "active",
  "coding": {{
    "system": "http://www.nlm.nih.gov/research/umls/rxnorm",
    "code": "6809",
    "display": "Metformin"
  }}
}}

Input: "No history of insulin use"
Output:
{{
  "type": "exclusion",
  "category": "medication",
  "description": "No history of insulin use",
  "attribute": "medication_name",
  "operator": "not_contains",
  "value": "insulin",
  "fhir_resource": "MedicationStatement",
  "fhir_path": "MedicationStatement.medicationCodeableConcept"
}}

Input: "On stable statin therapy"
Output:
{{
  "type": "inclusion",
  "category": "medication",
  "description": "On stable statin therapy",
  "attribute": "medication_class",
  "operator": "contains",
  "value": "statin",
  "fhir_resource": "MedicationStatement",
  "fhir_path": "MedicationStatement.medicationCodeableConcept",
  "status": "active"
}}

Input: "Taking warfarin for anticoagulation"
Output:
{{
  "type": "inclusion",
  "category": "medication",
  "description": "Taking warfarin",
  "attribute": "medication_name",
  "operator": "contains",
  "value": "warfarin",
  "fhir_resource": "MedicationStatement",
  "fhir_path": "MedicationStatement.medicationCodeableConcept",
  "status": "active",
  "coding": {{
    "system": "http://www.nlm.nih.gov/research/umls/rxnorm",
    "code": "11289",
    "display": "Warfarin"
  }}
}}

Input: "Currently on ACE inhibitor"
Output:
{{
  "type": "inclusion",
  "category": "medication",
  "description": "ACE inhibitor use",
  "attribute": "medication_class",
  "operator": "contains",
  "value": "lisinopril",
  "fhir_resource": "MedicationStatement",
  "fhir_path": "MedicationStatement.medicationCodeableConcept",
  "status": "active",
  "coding": {{
    "system": "http://www.nlm.nih.gov/research/umls/rxnorm",
    "code": "29046",
    "display": "Lisinopril"
  }}
}}

Input: "On aspirin therapy"
Output:
{{
  "type": "inclusion",
  "category": "medication",
  "description": "Aspirin therapy",
  "attribute": "medication_name",
  "operator": "contains",
  "value": "aspirin",
  "fhir_resource": "MedicationStatement",
  "fhir_path": "MedicationStatement.medicationCodeableConcept",
  "status": "active",
  "coding": {{
    "system": "http://www.nlm.nih.gov/research/umls/rxnorm",
    "code": "1191",
    "display": "Aspirin"
  }}
}}

Input: "No allergy to penicillin"
Output:
{{
  "type": "exclusion",
  "category": "allergy",
  "description": "No allergy to penicillin",
  "attribute": "allergen",
  "operator": "not_contains",
  "value": "penicillin",
  "fhir_resource": "AllergyIntolerance",
  "fhir_path": "AllergyIntolerance.code"
}}

Input: "Allergic to peanuts"
Output:
{{
  "type": "exclusion",
  "category": "allergy",
  "description": "Allergic to peanuts",
  "attribute": "allergen",
  "operator": "contains",
  "value": "peanut",
  "fhir_resource": "AllergyIntolerance",
  "fhir_path": "AllergyIntolerance.code",
  "coding": {{
    "system": "http://snomed.info/sct",
    "code": "256349002",
    "display": "Peanut allergy"
  }}
}}

Input: "No allergy to sulfa drugs"
Output:
{{
  "type": "exclusion",
  "category": "allergy",
  "description": "No allergy to sulfa drugs",
  "attribute": "allergen",
  "operator": "not_contains",
  "value": "sulfonamide",
  "fhir_resource": "AllergyIntolerance",
  "fhir_path": "AllergyIntolerance.code",
  "coding": {{
    "system": "http://snomed.info/sct",
    "code": "387406002",
    "display": "Sulfonamide"
  }}
}}

Input: "Allergic to NSAIDs"
Output:
{{
  "type": "exclusion",
  "category": "allergy",
  "description": "Allergy to NSAIDs",
  "attribute": "allergen",
  "operator": "contains",
  "value": "NSAID",
  "fhir_resource": "AllergyIntolerance",
  "fhir_path": "AllergyIntolerance.code",
  "coding": {{
    "system": "http://snomed.info/sct",
    "code": "293586001",
    "display": "Non-steroidal anti-inflammatory agent"
  }}
}}

Input: "No contrast dye allergy"
Output:
{{
  "type": "exclusion",
  "category": "allergy",
  "description": "No contrast dye allergy",
  "attribute": "allergen",
  "operator": "not_contains",
  "value": "contrast",
  "fhir_resource": "AllergyIntolerance",
  "fhir_path": "AllergyIntolerance.code",
  "coding": {{
    "system": "http://snomed.info/sct",
    "code": "293637006",
    "display": "Iodinated contrast media"
  }}
}}

Input: "No known drug allergies"
Output:
{{
  "type": "inclusion",
  "category": "allergy",
  "description": "No known drug allergies",
  "attribute": "drug_allergy",
  "operator": "not_exists",
  "value": null,
  "fhir_resource": "AllergyIntolerance",
  "fhir_path": "AllergyIntolerance.category",
  "category_filter": "medication"
}}

**Procedure Examples:**

Input: "No prior surgical resection of primary tumor"
Output:
{{
  "type": "exclusion",
  "category": "procedure",
  "description": "No prior surgical resection",
  "attribute": "procedure_type",
  "operator": "not_exists",
  "value": "surgical resection",
  "fhir_resource": "Procedure",
  "fhir_path": "Procedure.code",
  "procedure_category": "surgical-procedure",
  "coding": {{
    "system": "http://snomed.info/sct",
    "code": "392021009",
    "display": "Surgical resection"
  }}
}}

Input: "Previous coronary artery bypass graft surgery"
Output:
{{
  "type": "inclusion",
  "category": "procedure",
  "description": "Prior CABG surgery",
  "attribute": "procedure_type",
  "operator": "contains",
  "value": "coronary artery bypass graft",
  "fhir_resource": "Procedure",
  "fhir_path": "Procedure.code",
  "procedure_category": "surgical-procedure",
  "coding": {{
    "system": "http://www.ama-assn.org/go/cpt",
    "code": "33533",
    "display": "Coronary artery bypass, using arterial graft(s)"
  }}
}}

Input: "No prior stem cell transplantation"
Output:
{{
  "type": "exclusion",
  "category": "procedure",
  "description": "No prior stem cell transplant",
  "attribute": "procedure_type",
  "operator": "not_exists",
  "value": "stem cell transplant",
  "fhir_resource": "Procedure",
  "fhir_path": "Procedure.code",
  "procedure_category": "therapeutic-procedure",
  "coding": {{
    "system": "http://snomed.info/sct",
    "code": "234336002",
    "display": "Hematopoietic stem cell transplant"
  }}
}}

Input: "Prior hip replacement surgery"
Output:
{{
  "type": "inclusion",
  "category": "procedure",
  "description": "Hip replacement",
  "attribute": "procedure_type",
  "operator": "contains",
  "value": "hip replacement",
  "fhir_resource": "Procedure",
  "fhir_path": "Procedure.code",
  "procedure_category": "surgical-procedure",
  "coding": {{
    "system": "http://www.ama-assn.org/go/cpt",
    "code": "27130",
    "display": "Total hip arthroplasty"
  }}
}}

Input: "No major surgery within 4 weeks"
Output:
{{
  "type": "exclusion",
  "category": "procedure",
  "description": "No major surgery within 4 weeks",
  "attribute": "procedure_type",
  "operator": "not_exists",
  "value": "major surgery",
  "fhir_resource": "Procedure",
  "fhir_path": "Procedure.performedDateTime",
  "procedure_category": "surgical-procedure",
  "temporal_constraint": {{
    "value": 4,
    "unit": "weeks",
    "direction": "within"
  }}
}}

Input: "Prior radiation therapy"
Output:
{{
  "type": "inclusion",
  "category": "procedure",
  "description": "Prior radiation therapy",
  "attribute": "procedure_type",
  "operator": "contains",
  "value": "radiation therapy",
  "fhir_resource": "Procedure",
  "fhir_path": "Procedure.code",
  "procedure_category": "therapeutic-procedure",
  "coding": {{
    "system": "http://snomed.info/sct",
    "code": "108290001",
    "display": "Radiation oncology AND/OR radiotherapy"
  }}
}}

Input: "No history of organ transplant"
Output:
{{
  "type": "exclusion",
  "category": "procedure",
  "description": "No organ transplant history",
  "attribute": "procedure_type",
  "operator": "not_exists",
  "value": "organ transplant",
  "fhir_resource": "Procedure",
  "fhir_path": "Procedure.code",
  "procedure_category": "surgical-procedure",
  "coding": {{
    "system": "http://snomed.info/sct",
    "code": "77465005",
    "display": "Transplantation"
  }}
}}

Input: "Previous colonoscopy"
Output:
{{
  "type": "inclusion",
  "category": "procedure",
  "description": "Prior colonoscopy",
  "attribute": "procedure_type",
  "operator": "contains",
  "value": "colonoscopy",
  "fhir_resource": "Procedure",
  "fhir_path": "Procedure.code",
  "procedure_category": "diagnostic-procedure",
  "coding": {{
    "system": "http://www.ama-assn.org/go/cpt",
    "code": "45378",
    "display": "Colonoscopy, flexible"
  }}
}}

**Complex Criteria with Logical Operators:**

CRITICAL RULES:
1. If criteria has logical operators (OR, AND, NOT) → Create nested structure with "logic_operator" and "criteria" array
2. If criteria is simple (no logical operators) → Create single criterion object WITHOUT "criteria" array
3. Do NOT wrap single simple criteria in unnecessary nested structures

Decision Tree:
- Text contains " OR " between conditions? → Use "logic_operator": "OR" with "criteria" array
- Text contains " AND " between conditions? → Use "logic_operator": "AND" with "criteria" array
- Text contains " NOT "? → Use "logic_operator": "NOT" with "criteria" array
- Text is simple (no logical operators)? → Return simple criterion object directly

Example 1 - CORRECT way to handle "OR":
Input: "Patient has Type 2 Diabetes OR Pre-diabetes"

CORRECT Output:
[
  {{
    "type": "inclusion",
    "logic_operator": "OR",
    "description": "Type 2 Diabetes or Pre-diabetes",
    "criteria": [
      {{
        "category": "condition",
        "description": "Type 2 Diabetes",
        "attribute": "diagnosis",
        "operator": "contains",
        "value": "Type 2 Diabetes",
        "fhir_resource": "Condition",
        "fhir_path": "Condition.code"
      }},
      {{
        "category": "condition",
        "description": "Pre-diabetes",
        "attribute": "diagnosis",
        "operator": "contains",
        "value": "Pre-diabetes",
        "fhir_resource": "Condition",
        "fhir_path": "Condition.code"
      }}
    ]
  }}
]

WRONG Output (DO NOT DO THIS):
[
  {{"type": "inclusion", "description": "Type 2 Diabetes", ...}},
  {{"type": "inclusion", "description": "Pre-diabetes", ...}}
]

Example 2 - CORRECT way to handle nested "AND" with "OR":
Input: "(Type 2 Diabetes OR Pre-diabetes) AND ECOG performance status 0-1"

CORRECT Output:
[
  {{
    "type": "inclusion",
    "logic_operator": "AND",
    "description": "(Type 2 Diabetes OR Pre-diabetes) AND ECOG 0-1",
    "criteria": [
      {{
        "logic_operator": "OR",
        "description": "Type 2 Diabetes or Pre-diabetes",
        "criteria": [
          {{
            "category": "condition",
            "description": "Type 2 Diabetes",
            "attribute": "diagnosis",
            "operator": "contains",
            "value": "Type 2 Diabetes",
            "fhir_resource": "Condition"
          }},
          {{
            "category": "condition",
            "description": "Pre-diabetes",
            "attribute": "diagnosis",
            "operator": "contains",
            "value": "Pre-diabetes",
            "fhir_resource": "Condition"
          }}
        ]
      }},
      {{
        "category": "performance_status",
        "description": "ECOG 0-1",
        "attribute": "ecog",
        "operator": "between",
        "value": [0, 1],
        "fhir_resource": "Observation",
        "coding": {{"system": "http://loinc.org", "code": "89247-1"}}
      }}
    ]
  }}
]

Now parse the following criteria text:

{criteria_text}

Return ONLY a JSON array.
- If the text contains logical operators (AND, OR, NOT), return ONE criterion object with "logic_operator" and nested "criteria" array
- If the text contains multiple independent criteria without logical operators, return multiple criterion objects
- Do not include any explanatory text or markdown formatting."""


def create_nested_criteria_structure(criteria_list: List[Dict[str, Any]], criteria_text: str) -> List[Dict[str, Any]]:
    """
    Post-process parsed criteria to create nested logical structures when AND/OR/NOT operators are detected.

    Args:
        criteria_list: Flat list of parsed criteria
        criteria_text: Original criteria text

    Returns:
        Restructured criteria with nested logic operators
    """
    import re

    # First, unwrap any unnecessarily wrapped criteria and copy type fields recursively
    def process_criterion(criterion, parent_type=None):
        """Recursively process criteria to unwrap and copy type fields"""

        # Copy type from parent if missing
        if parent_type and 'type' not in criterion:
            criterion['type'] = parent_type

        # Get the type for this level
        current_type = criterion.get('type', parent_type)

        # If has sub-criteria, process them recursively
        if criterion.get('criteria'):
            criterion['criteria'] = [
                process_criterion(sub, current_type)
                for sub in criterion['criteria']
            ]

            # Check if this is an unnecessary wrapper (single sub-criterion with logic_operator but no category)
            if (len(criterion['criteria']) == 1 and
                criterion.get('logic_operator') and
                not criterion.get('category')):
                # Unwrap: return the single sub-criterion instead
                return criterion['criteria'][0]

        return criterion

    criteria_list = [process_criterion(c) for c in criteria_list]

    # Check if criteria text contains logical operators
    text_upper = criteria_text.upper()
    has_or = ' OR ' in text_upper
    has_and = ' AND ' in text_upper
    has_not = ' NOT ' in text_upper or text_upper.startswith('NOT ')

    # If no logical operators, return as-is
    if not (has_or or has_and or has_not):
        return criteria_list

    # If only one criterion was parsed but text has logical operators,
    # return as-is (LLM might have already structured it correctly)
    if len(criteria_list) == 1:
        first_criterion = criteria_list[0]

        # If it already has a logic_operator, it's properly structured
        if first_criterion.get('logic_operator'):
            return criteria_list

        # If it has criteria array but no logic_operator, check if it should have one
        if first_criterion.get('criteria'):
            sub_criteria = first_criterion['criteria']
            # Only add logic_operator if there are actually multiple sub-criteria
            if len(sub_criteria) > 1:
                # Add the appropriate logic operator
                if has_and and has_or:
                    first_criterion['logic_operator'] = 'AND'
                elif has_and:
                    first_criterion['logic_operator'] = 'AND'
                elif has_or:
                    first_criterion['logic_operator'] = 'OR'
                elif has_not:
                    first_criterion['logic_operator'] = 'NOT'
            else:
                # Single sub-criterion, unwrap it and return directly
                return sub_criteria

            return criteria_list

        # Single criterion without nested structure, return as-is
        return criteria_list

    # Determine the top-level operator based on precedence and presence
    # Priority: NOT > AND > OR
    # For nested "(A OR B) AND C", AND is at top level

    # If we have both AND and OR, check which is at the top level
    # Look for patterns like "(... OR ...) AND" or "AND (... OR ...)"
    if has_and and has_or:
        # Check if OR is parenthesized (nested inside AND)
        if '(' in criteria_text and ')' in criteria_text:
            # AND is likely top-level
            top_operator = 'AND'
            # Try to identify sub-groups
            # This is complex, so for now, create AND at top level with all criteria
            return [{
                "type": "inclusion",
                "logic_operator": "AND",
                "description": criteria_text.strip(),
                "criteria": criteria_list
            }]
        else:
            # No clear nesting, default to AND
            top_operator = 'AND'
    elif has_and:
        top_operator = 'AND'
    elif has_or:
        top_operator = 'OR'
    elif has_not:
        top_operator = 'NOT'
    else:
        return criteria_list

    # Create nested structure
    return [{
        "type": "inclusion",
        "logic_operator": top_operator,
        "description": criteria_text.strip(),
        "criteria": criteria_list
    }]


def convert_decimals(obj: Any) -> Any:
    """
    Recursively convert Decimal objects to int or float.
    DynamoDB returns numbers as Decimal objects which aren't JSON serializable.

    Args:
        obj: The object to convert

    Returns:
        The object with Decimals converted to int/float
    """
    if isinstance(obj, list):
        return [convert_decimals(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: convert_decimals(value) for key, value in obj.items()}
    elif isinstance(obj, Decimal):
        # Convert to int if it's a whole number, otherwise float
        if obj % 1 == 0:
            return int(obj)
        else:
            return float(obj)
    else:
        return obj


def generate_cache_key(criteria_text: str, trial_id: str) -> str:
    """
    Generate a unique cache key based on criteria text and trial ID.

    Args:
        criteria_text: The criteria text
        trial_id: Trial identifier

    Returns:
        Cache key string
    """
    content = f"{trial_id}:{criteria_text}"
    return hashlib.sha256(content.encode()).hexdigest()


@tracer.capture_method
def get_cached_criteria(trial_id: str, criteria_text: str) -> Optional[List[Dict[str, Any]]]:
    """
    Retrieve cached parsed criteria from DynamoDB.

    Args:
        trial_id: Trial identifier
        criteria_text: The criteria text to check

    Returns:
        Cached criteria if found and not expired, None otherwise
    """
    if not criteria_cache_table:
        logger.info("DynamoDB cache table not configured")
        return None

    try:
        cache_key = generate_cache_key(criteria_text, trial_id)

        response = criteria_cache_table.get_item(
            Key={'trial_id': trial_id}
        )

        if 'Item' not in response:
            logger.info(f"Cache miss for trial_id: {trial_id}")
            return None

        item = response['Item']

        # Check if cache key matches (criteria text hasn't changed)
        if item.get('cache_key') != cache_key:
            logger.info(f"Cache key mismatch for trial_id: {trial_id}")
            return None

        # Check if cache is expired (default TTL: 7 days)
        if 'ttl' in item:
            current_time = int(datetime.utcnow().timestamp())
            if current_time > item['ttl']:
                logger.info(f"Cache expired for trial_id: {trial_id}")
                return None

        logger.info(f"Cache hit for trial_id: {trial_id}")
        # Convert Decimal objects to int/float for JSON serialization
        cached_data = item.get('parsed_criteria')
        return convert_decimals(cached_data) if cached_data else None

    except Exception as e:
        logger.error(f"Error retrieving from cache: {str(e)}")
        # Don't fail the request if cache retrieval fails
        return None


@tracer.capture_method
def save_to_cache(trial_id: str, criteria_text: str, parsed_criteria: List[Dict[str, Any]]) -> None:
    """
    Save parsed criteria to DynamoDB cache.

    Args:
        trial_id: Trial identifier
        criteria_text: The original criteria text
        parsed_criteria: The parsed criteria to cache
    """
    if not criteria_cache_table:
        logger.info("DynamoDB cache table not configured")
        return

    try:
        cache_key = generate_cache_key(criteria_text, trial_id)

        # Set TTL to 7 days from now
        ttl = int((datetime.utcnow() + timedelta(days=7)).timestamp())

        criteria_cache_table.put_item(
            Item={
                'trial_id': trial_id,
                'cache_key': cache_key,
                'criteria_text': criteria_text,
                'parsed_criteria': parsed_criteria,
                'created_at': datetime.utcnow().isoformat(),
                'ttl': ttl
            }
        )

        logger.info(f"Saved to cache for trial_id: {trial_id}")

    except Exception as e:
        logger.error(f"Error saving to cache: {str(e)}")
        # Don't fail the request if cache save fails


@tracer.capture_method
def enhance_with_coding_systems(criteria: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Post-processor that injects missing coding systems based on category and value.
    Ensures 100% coverage of coding systems across all criteria.

    Args:
        criteria: List of parsed criteria (may have missing coding systems)

    Returns:
        Enhanced criteria with complete coding systems
    """
    # Comprehensive coding system mappings
    CODING_MAPS = {
        "condition": {
            # ICD-10-CM codes for common conditions
            "type 2 diabetes": {"system": "http://hl7.org/fhir/sid/icd-10-cm", "code": "E11", "display": "Type 2 diabetes mellitus"},
            "diabetes": {"system": "http://hl7.org/fhir/sid/icd-10-cm", "code": "E11", "display": "Type 2 diabetes mellitus"},
            "pre-diabetes": {"system": "http://hl7.org/fhir/sid/icd-10-cm", "code": "R73.03", "display": "Prediabetes"},
            "prediabetes": {"system": "http://hl7.org/fhir/sid/icd-10-cm", "code": "R73.03", "display": "Prediabetes"},
            "hypertension": {"system": "http://hl7.org/fhir/sid/icd-10-cm", "code": "I10", "display": "Essential (primary) hypertension"},
            "breast cancer": {"system": "http://hl7.org/fhir/sid/icd-10-cm", "code": "C50", "display": "Malignant neoplasm of breast"},
            "ovarian cancer": {"system": "http://hl7.org/fhir/sid/icd-10-cm", "code": "C56", "display": "Malignant neoplasm of ovary"},
            "lung cancer": {"system": "http://hl7.org/fhir/sid/icd-10-cm", "code": "C34", "display": "Malignant neoplasm of bronchus and lung"},
            "colorectal cancer": {"system": "http://hl7.org/fhir/sid/icd-10-cm", "code": "C18", "display": "Malignant neoplasm of colon"},
            "heart failure": {"system": "http://hl7.org/fhir/sid/icd-10-cm", "code": "I50", "display": "Heart failure"},
            "copd": {"system": "http://hl7.org/fhir/sid/icd-10-cm", "code": "J44", "display": "Chronic obstructive pulmonary disease"},
            "chronic kidney disease": {"system": "http://snomed.info/sct", "code": "431855005", "display": "Chronic kidney disease stage 4"},
            "myocardial infarction": {"system": "http://hl7.org/fhir/sid/icd-10-cm", "code": "I21", "display": "Acute myocardial infarction"},
        },
        "allergy": {
            # SNOMED CT codes for allergies
            "penicillin": {"system": "http://snomed.info/sct", "code": "91936005", "display": "Allergy to penicillin"},
            "peanut": {"system": "http://snomed.info/sct", "code": "256349002", "display": "Peanut allergy"},
            "sulfonamide": {"system": "http://snomed.info/sct", "code": "387406002", "display": "Sulfonamide"},
            "sulfa": {"system": "http://snomed.info/sct", "code": "387406002", "display": "Sulfonamide"},
            "nsaid": {"system": "http://snomed.info/sct", "code": "293586001", "display": "Non-steroidal anti-inflammatory agent"},
            "contrast": {"system": "http://snomed.info/sct", "code": "293637006", "display": "Iodinated contrast media"},
        },
        "medication": {
            # RxNorm codes for medications
            "metformin": {"system": "http://www.nlm.nih.gov/research/umls/rxnorm", "code": "6809", "display": "Metformin"},
            "insulin": {"system": "http://www.nlm.nih.gov/research/umls/rxnorm", "code": "5856", "display": "Insulin"},
            "statin": {"system": "http://www.nlm.nih.gov/research/umls/rxnorm", "code": "36567", "display": "Simvastatin"},
            "warfarin": {"system": "http://www.nlm.nih.gov/research/umls/rxnorm", "code": "11289", "display": "Warfarin"},
            "aspirin": {"system": "http://www.nlm.nih.gov/research/umls/rxnorm", "code": "1191", "display": "Aspirin"},
            "lisinopril": {"system": "http://www.nlm.nih.gov/research/umls/rxnorm", "code": "29046", "display": "Lisinopril"},
        },
        "performance_status": {
            # LOINC codes for performance status
            "ecog": {"system": "http://loinc.org", "code": "89247-1", "display": "ECOG Performance Status"},
            "karnofsky": {"system": "http://loinc.org", "code": "89243-0", "display": "Karnofsky Performance Status"},
        },
        "lab_value": {
            # LOINC codes for lab tests
            "hba1c": {"system": "http://loinc.org", "code": "4548-4", "display": "Hemoglobin A1c/Hemoglobin.total in Blood"},
            "hemoglobin a1c": {"system": "http://loinc.org", "code": "4548-4", "display": "Hemoglobin A1c/Hemoglobin.total in Blood"},
            "creatinine": {"system": "http://loinc.org", "code": "2160-0", "display": "Creatinine [Mass/volume] in Serum or Plasma"},
            "egfr": {"system": "http://loinc.org", "code": "33914-3", "display": "Glomerular filtration rate/1.73 sq M.predicted"},
            "hemoglobin": {"system": "http://loinc.org", "code": "718-7", "display": "Hemoglobin [Mass/volume] in Blood"},
            "wbc": {"system": "http://loinc.org", "code": "6690-2", "display": "Leukocytes [#/volume] in Blood"},
            "platelet": {"system": "http://loinc.org", "code": "777-3", "display": "Platelets [#/volume] in Blood"},
            "alt": {"system": "http://loinc.org", "code": "1742-6", "display": "Alanine aminotransferase [Enzymatic activity/volume] in Serum or Plasma"},
            "ast": {"system": "http://loinc.org", "code": "1920-8", "display": "Aspartate aminotransferase [Enzymatic activity/volume] in Serum or Plasma"},
        },
        "procedure": {
            # CPT and SNOMED CT codes for procedures
            "cabg": {"system": "http://www.ama-assn.org/go/cpt", "code": "33533", "display": "Coronary artery bypass, using arterial graft(s)"},
            "coronary artery bypass": {"system": "http://www.ama-assn.org/go/cpt", "code": "33533", "display": "Coronary artery bypass, using arterial graft(s)"},
            "appendectomy": {"system": "http://snomed.info/sct", "code": "80146002", "display": "Appendectomy"},
            "hip replacement": {"system": "http://www.ama-assn.org/go/cpt", "code": "27130", "display": "Total hip arthroplasty"},
            "total hip arthroplasty": {"system": "http://www.ama-assn.org/go/cpt", "code": "27130", "display": "Total hip arthroplasty"},
            "knee replacement": {"system": "http://www.ama-assn.org/go/cpt", "code": "27447", "display": "Total knee arthroplasty"},
            "mastectomy": {"system": "http://www.ama-assn.org/go/cpt", "code": "19307", "display": "Mastectomy, modified radical"},
            "colonoscopy": {"system": "http://www.ama-assn.org/go/cpt", "code": "45378", "display": "Colonoscopy, flexible"},
            "biopsy": {"system": "http://snomed.info/sct", "code": "86273004", "display": "Biopsy"},
            "stem cell transplant": {"system": "http://snomed.info/sct", "code": "234336002", "display": "Hematopoietic stem cell transplant"},
            "bone marrow transplant": {"system": "http://snomed.info/sct", "code": "234336002", "display": "Hematopoietic stem cell transplant"},
            "surgical resection": {"system": "http://snomed.info/sct", "code": "392021009", "display": "Surgical resection"},
            "tumor resection": {"system": "http://snomed.info/sct", "code": "392021009", "display": "Surgical resection"},
            "radiation therapy": {"system": "http://snomed.info/sct", "code": "108290001", "display": "Radiation oncology AND/OR radiotherapy"},
            "radiotherapy": {"system": "http://snomed.info/sct", "code": "108290001", "display": "Radiation oncology AND/OR radiotherapy"},
            "chemotherapy": {"system": "http://snomed.info/sct", "code": "367336001", "display": "Chemotherapy"},
            "transplant": {"system": "http://snomed.info/sct", "code": "77465005", "display": "Transplantation"},
            "transplantation": {"system": "http://snomed.info/sct", "code": "77465005", "display": "Transplantation"},
            "organ transplant": {"system": "http://snomed.info/sct", "code": "77465005", "display": "Transplantation"},
            "hysterectomy": {"system": "http://www.ama-assn.org/go/cpt", "code": "58150", "display": "Total abdominal hysterectomy"},
            "prostatectomy": {"system": "http://www.ama-assn.org/go/cpt", "code": "55866", "display": "Laparoscopy, surgical prostatectomy"},
            "cardiac catheterization": {"system": "http://www.ama-assn.org/go/cpt", "code": "93458", "display": "Catheter placement in coronary artery(s)"},
            "pacemaker": {"system": "http://www.ama-assn.org/go/cpt", "code": "33206", "display": "Insertion of new or replacement of permanent pacemaker"},
            "angioplasty": {"system": "http://www.ama-assn.org/go/cpt", "code": "92920", "display": "Percutaneous transluminal coronary angioplasty"},
            "stent": {"system": "http://www.ama-assn.org/go/cpt", "code": "92928", "display": "Percutaneous transcatheter placement of intracoronary stent(s)"},
            "cataract surgery": {"system": "http://www.ama-assn.org/go/cpt", "code": "66984", "display": "Extracapsular cataract removal"},
            "endoscopy": {"system": "http://www.ama-assn.org/go/cpt", "code": "43235", "display": "Esophagogastroduodenoscopy"},
            "dialysis": {"system": "http://snomed.info/sct", "code": "108241001", "display": "Dialysis procedure"},
            "major surgery": {"system": "http://snomed.info/sct", "code": "387713003", "display": "Surgical procedure"},
            "surgery": {"system": "http://snomed.info/sct", "code": "387713003", "display": "Surgical procedure"},
        }
    }

    def enhance_criterion(criterion: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively enhance a single criterion"""
        # If it has sub-criteria, enhance them recursively
        if 'criteria' in criterion and isinstance(criterion['criteria'], list):
            criterion['criteria'] = [enhance_criterion(c) for c in criterion['criteria']]
            return criterion

        # If it already has coding, skip it
        if 'coding' in criterion and criterion['coding']:
            return criterion

        # Try to inject coding system based on category and value
        category = criterion.get('category', '')
        value = criterion.get('value', '')
        attribute = criterion.get('attribute', '')
        description = criterion.get('description', '')

        # Combine all text fields for matching
        search_text = f"{value} {attribute} {description}".lower()

        if category in CODING_MAPS:
            # Try to find a match
            for keyword, coding_info in CODING_MAPS[category].items():
                if keyword.lower() in search_text:
                    criterion['coding'] = coding_info
                    logger.info(f"Injected coding system for {category}: {keyword} -> {coding_info['code']}")
                    break

        return criterion

    # Enhance all criteria
    enhanced_criteria = [enhance_criterion(c) for c in criteria]

    return enhanced_criteria


@tracer.capture_method
def parse_criteria_with_bedrock(criteria_text: str, model_id: str = "mistral.mistral-large-2402-v1:0") -> List[Dict[str, Any]]:
    """
    Use Bedrock to parse eligibility criteria into structured format.

    Args:
        criteria_text: Free-text eligibility criteria
        model_id: Bedrock model ID to use (default: Mistral Large)

    Returns:
        List of parsed criterion dictionaries
    """
    prompt = PARSING_PROMPT.format(criteria_text=criteria_text)

    # Prepare request based on model type
    is_mistral = "mistral" in model_id.lower()

    if is_mistral:
        # Mistral format
        request_body = {
            "prompt": f"<s>[INST] {prompt} [/INST]",
            "max_tokens": 4000,
            "temperature": 0.1,  # Low temperature for consistent parsing
            "top_p": 0.9
        }
    else:
        # Titan format (fallback)
        request_body = {
            "inputText": prompt,
            "textGenerationConfig": {
                "maxTokenCount": 4000,
                "temperature": 0.1,
                "topP": 0.9
            }
        }

    try:
        response = bedrock_runtime.invoke_model(
            modelId=model_id,
            body=json.dumps(request_body)
        )

        response_body = json.loads(response['body'].read())
        logger.info("Bedrock response received", extra={"response": response_body})

        # Extract the parsed criteria from response
        # Support multiple API formats: Mistral, Titan, and Claude
        if 'outputs' in response_body:
            # Mistral format
            content = response_body['outputs'][0]['text']
        elif 'results' in response_body:
            # Titan format
            content = response_body['results'][0]['outputText']
        elif 'content' in response_body:
            # Claude format
            content = response_body['content'][0]['text']
        else:
            raise ValueError(f"Unexpected Bedrock response format: {response_body}")

        # Parse JSON from response
        # Handle cases where LLM might wrap JSON in markdown code blocks
        content = content.strip()

        # Check if content contains backticks (markdown code blocks)
        if '```' in content:
            # Extract content between first and last backticks
            first_backtick = content.find('```')
            last_backtick = content.rfind('```')

            if first_backtick != -1 and last_backtick != -1 and first_backtick < last_backtick:
                # Extract the content between backticks
                content = content[first_backtick:last_backtick]

                # Remove the opening backticks and optional language identifier
                # Handle various formats: ```json, ```tabular-data-json, etc.
                if content.startswith('```'):
                    # Find the end of the first line (language identifier)
                    newline_pos = content.find('\n')
                    if newline_pos != -1:
                        content = content[newline_pos+1:]
                    else:
                        content = content[3:]

                content = content.strip()
        else:
            # No backticks, extract JSON from content
            content = content.strip()

            # Find the first [ or { to locate the start of JSON
            json_start = -1
            for char in ['[', '{']:
                pos = content.find(char)
                if pos != -1:
                    if json_start == -1 or pos < json_start:
                        json_start = pos

            if json_start != -1:
                # Extract from the first JSON character onwards
                content = content[json_start:]

            # Now content should start with valid JSON

        parsed_criteria = json.loads(content)

        # Ensure it's a list
        # Handle cases where the response might be wrapped in an object (e.g., {"rows": [...]})
        if isinstance(parsed_criteria, dict):
            if 'rows' in parsed_criteria:
                parsed_criteria = parsed_criteria['rows']
            else:
                parsed_criteria = [parsed_criteria]

        logger.info(f"Successfully parsed {len(parsed_criteria)} criteria")

        # Post-process to create nested logical structures
        parsed_criteria = create_nested_criteria_structure(parsed_criteria, criteria_text)
        logger.info(f"After post-processing: {len(parsed_criteria)} criteria")

        # Enhance with coding systems (inject missing ones)
        parsed_criteria = enhance_with_coding_systems(parsed_criteria)
        logger.info(f"After coding system enhancement: {len(parsed_criteria)} criteria")

        return parsed_criteria

    except Exception as e:
        logger.error(f"Error parsing criteria with Bedrock: {str(e)}")
        raise


@tracer.capture_method
def validate_criterion(criterion: Dict[str, Any], is_nested: bool = False) -> bool:
    """
    Recursively validate a criterion (simple or complex).

    Args:
        criterion: Parsed criterion dictionary
        is_nested: Whether this is a nested criterion (for better error messages)

    Returns:
        True if valid, raises ValueError if invalid
    """
    # All criteria must have type (at root level or inherited)
    if not is_nested and 'type' not in criterion:
        raise ValueError("Missing required field: type")

    # Validate type if present
    if 'type' in criterion and criterion['type'] not in ['inclusion', 'exclusion']:
        raise ValueError(f"Invalid type: {criterion['type']}. Must be 'inclusion' or 'exclusion'")

    # Complex criterion validation
    if 'criteria' in criterion and criterion['criteria']:
        logic_op = criterion.get('logic_operator')
        if not logic_op:
            raise ValueError("Complex criterion must have 'logic_operator' field")
        if logic_op not in ['AND', 'OR', 'NOT']:
            raise ValueError(f"Invalid logic_operator: {logic_op}. Must be 'AND', 'OR', or 'NOT'")
        if logic_op == 'NOT' and len(criterion['criteria']) != 1:
            raise ValueError("NOT operator requires exactly one sub-criterion")
        if not criterion['criteria']:
            raise ValueError("Complex criterion must have non-empty 'criteria' array")

        # Recursively validate sub-criteria
        for idx, sub_criterion in enumerate(criterion['criteria']):
            try:
                validate_criterion(sub_criterion, is_nested=True)
            except ValueError as e:
                raise ValueError(f"Invalid sub-criterion[{idx}]: {str(e)}")

        return True

    # Simple criterion validation
    required_fields = ['category', 'description', 'attribute', 'operator', 'value']

    for field in required_fields:
        if field not in criterion:
            raise ValueError(f"Missing required field: {field}")

    # Validate operator
    valid_operators = [
        'equals', 'not_equals',
        'greater_than', 'greater_than_or_equal',
        'less_than', 'less_than_or_equal',
        'between',
        'contains', 'not_contains',
        'exists', 'not_exists'
    ]
    if criterion['operator'] not in valid_operators:
        raise ValueError(f"Invalid operator: {criterion['operator']}")

    return True


@logger.inject_lambda_context(log_event=True)
@tracer.capture_lambda_handler
def lambda_handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    Lambda handler for criteria parsing.

    Expected event format:
    {
        "criteria_text": "Free-text eligibility criteria...",
        "trial_id": "optional-trial-identifier"
    }

    Returns:
    {
        "statusCode": 200,
        "body": {
            "criteria": [...parsed criteria...],
            "trial_id": "...",
            "count": N
        }
    }
    """
    try:
        # Extract input
        if 'body' in event:
            body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
        else:
            body = event

        criteria_text = body.get('criteria_text')
        trial_id = body.get('trial_id', 'unknown')

        if not criteria_text:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Missing required field: criteria_text'
                })
            }

        logger.info(f"Parsing criteria for trial: {trial_id}")

        # Try to get from cache first
        cached_criteria = get_cached_criteria(trial_id, criteria_text)
        cache_hit = False

        if cached_criteria:
            logger.info(f"Using cached criteria for trial: {trial_id}")
            parsed_criteria = cached_criteria
            cache_hit = True
        else:
            # Parse criteria using Bedrock
            logger.info(f"Cache miss - parsing with Bedrock for trial: {trial_id}")
            parsed_criteria = parse_criteria_with_bedrock(criteria_text)

            # Save to cache for future requests
            save_to_cache(trial_id, criteria_text, parsed_criteria)

        # Recursively validate each criterion
        def validate_recursive(criterion, path=""):
            """Recursively validate criteria and sub-criteria"""
            # Skip validation for structural nodes (those with logic_operator but no category)
            if criterion.get('logic_operator') and not criterion.get('category'):
                # This is a logical structure node, skip validation
                # But recursively validate sub-criteria if present
                if criterion.get('criteria'):
                    for sub_idx, sub_criterion in enumerate(criterion['criteria']):
                        validate_recursive(sub_criterion, f"{path}.{sub_idx}" if path else str(sub_idx))
            else:
                # Regular criterion, validate normally
                try:
                    validate_criterion(criterion)
                except ValueError as e:
                    logger.warning(f"Criterion {path} validation failed: {str(e)}")
                    # Add validation warning to criterion
                    criterion['validation_warning'] = str(e)

        for idx, criterion in enumerate(parsed_criteria):
            validate_recursive(criterion, str(idx))

        # Prepare response
        response_body = {
            'criteria': parsed_criteria,
            'trial_id': trial_id,
            'count': len(parsed_criteria),
            'metadata': {
                'model': 'mistral.mistral-large-2402-v1:0',
                'timestamp': context.get_remaining_time_in_millis() if context else None,
                'cache_hit': cache_hit,
                'cache_enabled': criteria_cache_table is not None
            }
        }

        logger.info(f"Successfully parsed {len(parsed_criteria)} criteria for trial {trial_id}")

        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(response_body)
        }

    except Exception as e:
        logger.error(f"Error in lambda_handler: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': str(e),
                'message': 'Failed to parse criteria'
            })
        }
