"""
Create complete FHIR bundles for 30 patients and post to HealthLake
"""
import sys
sys.path.append('scripts')

from seed_healthlake_patients import PATIENTS, make_signed_request, FHIR_ENDPOINT, calculate_birth_date
import json
import uuid
from datetime import datetime, timedelta, timezone

def create_patient_bundle(patient_data):
    """Create a complete FHIR transaction bundle for a patient with all resources."""
    bundle_entries = []
    patient_id = f"patient-{patient_data['identifier']}"
    
    # 1. Patient resource
    patient_resource = {
        "fullUrl": f"urn:uuid:{patient_id}",
        "resource": {
            "resourceType": "Patient",
            "id": patient_id,
            "identifier": [{
                "system": "http://hospital.org/patients",
                "value": patient_data['identifier']
            }],
            "name": [{
                "family": patient_data['family_name'],
                "given": [patient_data['given_name']],
                "text": f"{patient_data['given_name']} {patient_data['family_name']}"
            }],
            "gender": patient_data['gender'],
            "birthDate": calculate_birth_date(patient_data['age'])
        },
        "request": {
            "method": "PUT",
            "url": f"Patient/{patient_id}"
        }
    }
    bundle_entries.append(patient_resource)
    
    # 2. Condition resources
    for idx, condition in enumerate(patient_data.get('conditions', [])):
        condition_id = f"condition-{patient_data['identifier']}-{idx}"
        condition_resource = {
            "fullUrl": f"urn:uuid:{condition_id}",
            "resource": {
                "resourceType": "Condition",
                "id": condition_id,
                "subject": {
                    "reference": f"Patient/{patient_id}"
                },
                "code": {
                    "coding": [{
                        "system": f"http://hl7.org/fhir/sid/{condition['system'].lower()}",
                        "code": condition['code'],
                        "display": condition['display']
                    }],
                    "text": condition['display']
                },
                "clinicalStatus": {
                    "coding": [{
                        "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                        "code": "active"
                    }]
                },
                "recordedDate": datetime.now(timezone.utc).isoformat()
            },
            "request": {
                "method": "PUT",
                "url": f"Condition/{condition_id}"
            }
        }
        bundle_entries.append(condition_resource)
    
    # 3. Observation resources
    for idx, observation in enumerate(patient_data.get('observations', [])):
        obs_id = f"observation-{patient_data['identifier']}-{idx}"
        obs_resource = {
            "fullUrl": f"urn:uuid:{obs_id}",
            "resource": {
                "resourceType": "Observation",
                "id": obs_id,
                "status": "final",
                "subject": {
                    "reference": f"Patient/{patient_id}"
                },
                "code": {
                    "coding": [{
                        "system": f"http://{observation['system'].lower()}.org" if observation['system'] == 'LOINC' else observation['system'],
                        "code": observation['code'],
                        "display": observation['display']
                    }],
                    "text": observation['display']
                },
                "effectiveDateTime": datetime.now(timezone.utc).isoformat()
            },
            "request": {
                "method": "PUT",
                "url": f"Observation/{obs_id}"
            }
        }
        
        # Add value if present
        if 'value' in observation:
            if observation.get('unit'):
                obs_resource['resource']['valueQuantity'] = {
                    "value": observation['value'],
                    "unit": observation['unit']
                }
            else:
                obs_resource['resource']['valueInteger'] = observation['value']
        
        bundle_entries.append(obs_resource)
    
    # 4. MedicationStatement resources
    for idx, medication in enumerate(patient_data.get('medications', [])):
        med_id = f"medication-{patient_data['identifier']}-{idx}"
        med_resource = {
            "fullUrl": f"urn:uuid:{med_id}",
            "resource": {
                "resourceType": "MedicationStatement",
                "id": med_id,
                "status": "active",
                "subject": {
                    "reference": f"Patient/{patient_id}"
                },
                "medicationCodeableConcept": {
                    "coding": [{
                        "system": f"http://www.nlm.nih.gov/research/umls/{medication.get('system', 'RxNorm').lower()}",
                        "code": medication.get('code', ''),
                        "display": medication['name']
                    }],
                    "text": medication['name']
                },
                "effectiveDateTime": datetime.now(timezone.utc).isoformat()
            },
            "request": {
                "method": "PUT",
                "url": f"MedicationStatement/{med_id}"
            }
        }
        bundle_entries.append(med_resource)
    
    # 5. AllergyIntolerance resources
    for idx, allergy in enumerate(patient_data.get('allergies', [])):
        allergy_id = f"allergy-{patient_data['identifier']}-{idx}"
        allergy_resource = {
            "fullUrl": f"urn:uuid:{allergy_id}",
            "resource": {
                "resourceType": "AllergyIntolerance",
                "id": allergy_id,
                "patient": {
                    "reference": f"Patient/{patient_id}"
                },
                "code": {
                    "coding": [{
                        "system": f"http://snomed.info/sct",
                        "code": allergy['code'],
                        "display": allergy['display']
                    }],
                    "text": allergy['display']
                },
                "clinicalStatus": {
                    "coding": [{
                        "system": "http://terminology.hl7.org/CodeSystem/allergyintolerance-clinical",
                        "code": "active"
                    }]
                },
                "recordedDate": datetime.now(timezone.utc).isoformat()
            },
            "request": {
                "method": "PUT",
                "url": f"AllergyIntolerance/{allergy_id}"
            }
        }
        bundle_entries.append(allergy_resource)
    
    # 6. Procedure resources
    for idx, procedure in enumerate(patient_data.get('procedures', [])):
        proc_id = f"procedure-{patient_data['identifier']}-{idx}"
        proc_resource = {
            "fullUrl": f"urn:uuid:{proc_id}",
            "resource": {
                "resourceType": "Procedure",
                "id": proc_id,
                "status": "completed",
                "subject": {
                    "reference": f"Patient/{patient_id}"
                },
                "code": {
                    "coding": [{
                        "system": f"http://www.ama-assn.org/{procedure.get('system', 'CPT').lower()}",
                        "code": procedure['code'],
                        "display": procedure['display']
                    }],
                    "text": procedure['display']
                },
                "performedDateTime": (datetime.now(timezone.utc) - timedelta(days=180)).isoformat()
            },
            "request": {
                "method": "PUT",
                "url": f"Procedure/{proc_id}"
            }
        }
        bundle_entries.append(proc_resource)
    
    # 7. Immunization resources
    for idx, immunization in enumerate(patient_data.get('immunizations', [])):
        imm_id = f"immunization-{patient_data['identifier']}-{idx}"
        imm_resource = {
            "fullUrl": f"urn:uuid:{imm_id}",
            "resource": {
                "resourceType": "Immunization",
                "id": imm_id,
                "status": "completed",
                "patient": {
                    "reference": f"Patient/{patient_id}"
                },
                "vaccineCode": {
                    "coding": [{
                        "system": "http://hl7.org/fhir/sid/cvx",
                        "display": immunization
                    }],
                    "text": immunization
                },
                "occurrenceDateTime": (datetime.now(timezone.utc) - timedelta(days=90)).isoformat()
            },
            "request": {
                "method": "PUT",
                "url": f"Immunization/{imm_id}"
            }
        }
        bundle_entries.append(imm_resource)
    
    # 8. FamilyMemberHistory resources
    for idx, family_history in enumerate(patient_data.get('family_history', [])):
        fh_id = f"familyhistory-{patient_data['identifier']}-{idx}"
        fh_resource = {
            "fullUrl": f"urn:uuid:{fh_id}",
            "resource": {
                "resourceType": "FamilyMemberHistory",
                "id": fh_id,
                "status": "completed",
                "patient": {
                    "reference": f"Patient/{patient_id}"
                },
                "relationship": {
                    "text": family_history.get('relation', 'family member')
                },
                "condition": [{
                    "code": {
                        "text": family_history.get('condition', '')
                    }
                }]
            },
            "request": {
                "method": "PUT",
                "url": f"FamilyMemberHistory/{fh_id}"
            }
        }
        bundle_entries.append(fh_resource)
    
    # 9. DiagnosticReport resources
    for idx, report in enumerate(patient_data.get('diagnostic_reports', [])):
        dr_id = f"diagnosticreport-{patient_data['identifier']}-{idx}"
        dr_resource = {
            "fullUrl": f"urn:uuid:{dr_id}",
            "resource": {
                "resourceType": "DiagnosticReport",
                "id": dr_id,
                "status": "final",
                "subject": {
                    "reference": f"Patient/{patient_id}"
                },
                "code": {
                    "coding": [{
                        "system": f"http://www.ama-assn.org/{report.get('system', 'CPT').lower()}",
                        "code": report['code'],
                        "display": report['display']
                    }],
                    "text": report['display']
                },
                "effectiveDateTime": (datetime.now(timezone.utc) - timedelta(days=60)).isoformat()
            },
            "request": {
                "method": "PUT",
                "url": f"DiagnosticReport/{dr_id}"
            }
        }
        bundle_entries.append(dr_resource)
    
    # 10. CarePlan resource
    if patient_data.get('care_plan'):
        cp_id = f"careplan-{patient_data['identifier']}"
        cp_resource = {
            "fullUrl": f"urn:uuid:{cp_id}",
            "resource": {
                "resourceType": "CarePlan",
                "id": cp_id,
                "status": "active",
                "intent": "plan",
                "subject": {
                    "reference": f"Patient/{patient_id}"
                },
                "description": patient_data['care_plan'],
                "created": datetime.now(timezone.utc).isoformat()
            },
            "request": {
                "method": "PUT",
                "url": f"CarePlan/{cp_id}"
            }
        }
        bundle_entries.append(cp_resource)
    
    # 11. Encounter resource
    enc_id = f"encounter-{patient_data['identifier']}"
    enc_resource = {
        "fullUrl": f"urn:uuid:{enc_id}",
        "resource": {
            "resourceType": "Encounter",
            "id": enc_id,
            "status": "finished",
            "class": {
                "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
                "code": "AMB",
                "display": "ambulatory"
            },
            "subject": {
                "reference": f"Patient/{patient_id}"
            },
            "period": {
                "start": (datetime.now(timezone.utc) - timedelta(days=30)).isoformat(),
                "end": (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
            }
        },
        "request": {
            "method": "PUT",
            "url": f"Encounter/{enc_id}"
        }
    }
    bundle_entries.append(enc_resource)
    
    # Create the bundle
    bundle = {
        "resourceType": "Bundle",
        "type": "transaction",
        "entry": bundle_entries
    }
    
    return bundle

def seed_patient(patient_data):
    """Create a patient with all related resources in HealthLake."""
    try:
        bundle = create_patient_bundle(patient_data)
        
        # Post the bundle to HealthLake
        response = make_signed_request(
            'POST',
            FHIR_ENDPOINT,
            data=json.dumps(bundle)
        )
        
        if response.status_code in [200, 201]:
            result_bundle = response.json()
            resource_count = len(result_bundle.get('entry', []))
            return True, resource_count
        else:
            return False, f"HTTP {response.status_code}: {response.text[:200]}"
            
    except Exception as e:
        return False, str(e)

def main():
    print('='*80)
    print('SEEDING HEALTHLAKE WITH 30 COMPREHENSIVE PATIENTS')
    print('='*80)
    print()
    print(f'Total patients to create: {len(PATIENTS)}')
    print('Each patient includes all 11 FHIR resource types')
    print()
    print('='*80)
    print()
    
    success_count = 0
    fail_count = 0
    
    for idx, patient in enumerate(PATIENTS, 1):
        patient_name = f"{patient['given_name']} {patient['family_name']}"
        print(f"[{idx}/{len(PATIENTS)}] Creating patient: {patient_name} ({patient['identifier']})")
        
        success, result = seed_patient(patient)
        
        if success:
            print(f"  ✅ Created {result} FHIR resources")
            success_count += 1
        else:
            print(f"  ❌ Error: {result}")
            fail_count += 1
        
        print()
    
    print('='*80)
    print('SEEDING COMPLETE')
    print('='*80)
    print(f'✅ Successfully created: {success_count}/{len(PATIENTS)} patients')
    if fail_count > 0:
        print(f'❌ Failed: {fail_count}/{len(PATIENTS)} patients')
    print('='*80)

if __name__ == '__main__':
    main()

