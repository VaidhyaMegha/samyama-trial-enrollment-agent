#!/usr/bin/env python3
"""
Seed protocol data into DynamoDB for testing
"""

import boto3
from datetime import datetime

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

# Get table name from CloudFormation stack
cfn = boto3.client('cloudformation', region_name='us-east-1')
response = cfn.describe_stacks(StackName='TrialEnrollmentAgentStack')
outputs = {o['OutputKey']: o['OutputValue'] for o in response['Stacks'][0]['Outputs']}
table_name = outputs['CriteriaCacheTableName']

table = dynamodb.Table(table_name)

# Test protocol data
protocols = [
    {
        'trial_id': 'ONCOLOGY-2024-001',
        'title': 'Phase III Oncology Trial for Advanced Melanoma',
        'disease': 'Melanoma',
        'phase': 'Phase III',
        'status': 'Active',
        'enrollment_target': 150,
        'enrollment_current': 78,
        'processed_at': datetime.now().isoformat(),
        'raw_criteria_text': '''
Inclusion Criteria:
- Age >= 18 years and <= 75 years
- ECOG performance status 0-2
- Confirmed diagnosis of advanced melanoma (Stage III or IV)
- Adequate bone marrow function (Hemoglobin >= 9 g/dL, Platelets >= 100 x10^9/L)
- No prior immunotherapy

Exclusion Criteria:
- Pregnant or breastfeeding
- Active infection requiring systemic therapy
- Prior malignancy within 5 years
- History of autoimmune disease
        ''',
        'parsed_criteria': {
            'inclusion': [
                {'text': 'Age >= 18 years and <= 75 years', 'type': 'AGE'},
                {'text': 'ECOG performance status 0-2', 'type': 'PERFORMANCE_STATUS'},
                {'text': 'Confirmed diagnosis of advanced melanoma', 'type': 'DIAGNOSIS'},
                {'text': 'Adequate bone marrow function', 'type': 'LAB_VALUE'},
                {'text': 'No prior immunotherapy', 'type': 'TREATMENT_HISTORY'}
            ],
            'exclusion': [
                {'text': 'Pregnant or breastfeeding', 'type': 'PREGNANCY'},
                {'text': 'Active infection', 'type': 'INFECTION'},
                {'text': 'Prior malignancy within 5 years', 'type': 'HISTORY'},
                {'text': 'History of autoimmune disease', 'type': 'HISTORY'}
            ]
        },
        'metadata': {
            'sponsor': 'Memorial Sloan Kettering',
            'pi': 'Dr. Emily Rodriguez',
            'location': 'Multiple sites'
        }
    },
    {
        'trial_id': 'CARDIO-2024-015',
        'title': 'Cardiovascular Study for Heart Failure',
        'disease': 'Heart Failure',
        'phase': 'Phase II',
        'status': 'Active',
        'enrollment_target': 100,
        'enrollment_current': 45,
        'processed_at': datetime.now().isoformat(),
        'raw_criteria_text': '''
Inclusion Criteria:
- Age >= 40 years
- Diagnosis of chronic heart failure (NYHA Class II-III)
- Left ventricular ejection fraction <= 40%
- On stable heart failure medication for at least 3 months

Exclusion Criteria:
- Recent myocardial infarction (within 3 months)
- Uncontrolled hypertension (BP > 160/100)
- Severe renal impairment (eGFR < 30)
        ''',
        'parsed_criteria': {
            'inclusion': [
                {'text': 'Age >= 40 years', 'type': 'AGE'},
                {'text': 'Diagnosis of chronic heart failure', 'type': 'DIAGNOSIS'},
                {'text': 'LVEF <= 40%', 'type': 'LAB_VALUE'},
                {'text': 'Stable medication for 3 months', 'type': 'MEDICATION'}
            ],
            'exclusion': [
                {'text': 'Recent MI within 3 months', 'type': 'HISTORY'},
                {'text': 'Uncontrolled hypertension', 'type': 'VITAL_SIGN'},
                {'text': 'Severe renal impairment', 'type': 'LAB_VALUE'}
            ]
        },
        'metadata': {
            'sponsor': 'Cleveland Clinic',
            'pi': 'Dr. Michael Chen',
            'location': 'Cleveland, OH'
        }
    },
    {
        'trial_id': 'NEURO-2024-008',
        'title': "Neurology Research Protocol for Alzheimer's Disease",
        'disease': "Alzheimer's",
        'phase': 'Phase I',
        'status': 'Recruiting',
        'enrollment_target': 50,
        'enrollment_current': 12,
        'processed_at': datetime.now().isoformat(),
        'raw_criteria_text': '''
Inclusion Criteria:
- Age >= 60 years and <= 85 years
- Diagnosis of mild to moderate Alzheimer's disease
- MMSE score between 15-26
- Caregiver available to accompany patient
- Willing to undergo brain MRI

Exclusion Criteria:
- Other forms of dementia
- History of stroke
- Current use of memantine or donepezil
- Claustrophobia or MRI contraindications
        ''',
        'parsed_criteria': {
            'inclusion': [
                {'text': 'Age 60-85 years', 'type': 'AGE'},
                {'text': 'Alzheimer\'s disease diagnosis', 'type': 'DIAGNOSIS'},
                {'text': 'MMSE 15-26', 'type': 'COGNITIVE_TEST'},
                {'text': 'Caregiver available', 'type': 'SUPPORT'},
                {'text': 'Willing for MRI', 'type': 'PROCEDURE'}
            ],
            'exclusion': [
                {'text': 'Other dementia types', 'type': 'DIAGNOSIS'},
                {'text': 'History of stroke', 'type': 'HISTORY'},
                {'text': 'Using memantine or donepezil', 'type': 'MEDICATION'},
                {'text': 'MRI contraindications', 'type': 'PROCEDURE'}
            ]
        },
        'metadata': {
            'sponsor': 'Johns Hopkins University',
            'pi': 'Dr. Sarah Johnson',
            'location': 'Baltimore, MD'
        }
    },
    {
        'trial_id': 'DIABETES-2024-023',
        'title': 'Type 2 Diabetes Management with Novel GLP-1 Analog',
        'disease': 'Type 2 Diabetes',
        'phase': 'Phase III',
        'status': 'Active',
        'enrollment_target': 200,
        'enrollment_current': 156,
        'processed_at': datetime.now().isoformat(),
        'raw_criteria_text': '''
Inclusion Criteria:
- Age >= 18 years
- Diagnosed with Type 2 Diabetes for at least 1 year
- HbA1c between 7.5% and 11%
- BMI >= 25 kg/m²
- On stable metformin dose for 3 months

Exclusion Criteria:
- Type 1 Diabetes
- History of diabetic ketoacidosis
- Severe diabetic complications (retinopathy, nephropathy)
- Pancreatitis history
        ''',
        'parsed_criteria': {
            'inclusion': [
                {'text': 'Age >= 18 years', 'type': 'AGE'},
                {'text': 'Type 2 Diabetes >= 1 year', 'type': 'DIAGNOSIS'},
                {'text': 'HbA1c 7.5-11%', 'type': 'LAB_VALUE'},
                {'text': 'BMI >= 25', 'type': 'VITAL_SIGN'},
                {'text': 'Stable metformin 3 months', 'type': 'MEDICATION'}
            ],
            'exclusion': [
                {'text': 'Type 1 Diabetes', 'type': 'DIAGNOSIS'},
                {'text': 'Diabetic ketoacidosis history', 'type': 'HISTORY'},
                {'text': 'Severe complications', 'type': 'COMPLICATION'},
                {'text': 'Pancreatitis history', 'type': 'HISTORY'}
            ]
        },
        'metadata': {
            'sponsor': 'Novo Nordisk',
            'pi': 'Dr. David Kim',
            'location': 'Multiple sites nationwide'
        }
    },
    {
        'trial_id': 'RESPIRATORY-2024-011',
        'title': 'COPD Treatment with Inhaled Corticosteroid Combination',
        'disease': 'COPD',
        'phase': 'Phase II',
        'status': 'Active',
        'enrollment_target': 80,
        'enrollment_current': 34,
        'processed_at': datetime.now().isoformat(),
        'raw_criteria_text': '''
Inclusion Criteria:
- Age >= 40 years
- Confirmed COPD diagnosis (FEV1/FVC < 0.7)
- FEV1 between 30-80% predicted
- Current or former smoker (>= 10 pack-years)
- At least 1 COPD exacerbation in past year

Exclusion Criteria:
- Asthma diagnosis
- Active tuberculosis or lung infection
- Lung cancer or other malignancy
- Long-term oxygen therapy dependency
        ''',
        'parsed_criteria': {
            'inclusion': [
                {'text': 'Age >= 40 years', 'type': 'AGE'},
                {'text': 'COPD confirmed', 'type': 'DIAGNOSIS'},
                {'text': 'FEV1 30-80% predicted', 'type': 'PULMONARY_FUNCTION'},
                {'text': 'Smoking history >= 10 pack-years', 'type': 'HISTORY'},
                {'text': '1+ exacerbation past year', 'type': 'HISTORY'}
            ],
            'exclusion': [
                {'text': 'Asthma diagnosis', 'type': 'DIAGNOSIS'},
                {'text': 'Active TB or lung infection', 'type': 'INFECTION'},
                {'text': 'Lung cancer', 'type': 'DIAGNOSIS'},
                {'text': 'Long-term oxygen dependency', 'type': 'TREATMENT'}
            ]
        },
        'metadata': {
            'sponsor': 'GlaxoSmithKline',
            'pi': 'Dr. Linda Martinez',
            'location': 'Boston, MA and surrounding areas'
        }
    }
]

print("Seeding protocols into DynamoDB...")
print(f"Target table: {table_name}")

for protocol in protocols:
    try:
        table.put_item(Item=protocol)
        print(f"✅ Added: {protocol['trial_id']} - {protocol['title']}")
    except Exception as e:
        print(f"❌ Error adding {protocol['trial_id']}: {str(e)}")

print(f"\n✅ Seeded {len(protocols)} protocols successfully!")
print(f"\nYou can now test the frontend with these protocols:")
for p in protocols:
    print(f"  - {p['trial_id']}: {p['title']}")
