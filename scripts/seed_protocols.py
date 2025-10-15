"""
Seed Script for Clinical Trial Protocols
Generates 40 realistic clinical trial protocols and sends them to parse-criteria API
Each protocol includes criteria covering all 11 FHIR resources:
1. Patient (demographics)
2. Condition (diagnoses)
3. Observation (labs, vitals, performance status)
4. MedicationRequest/MedicationStatement
5. Procedure
6. AllergyIntolerance
7. DiagnosticReport
8. Immunization
9. FamilyMemberHistory
10. CarePlan
11. DocumentReference
"""

import json
import os
import time
import requests
from typing import Dict, List

# API Configuration
API_URL = "https://gt7dlyqj78.execute-api.us-east-1.amazonaws.com/prod/parse-criteria"

# Get token from environment or use get_jwt_token.py --role studyadmin
# Token expires in 60 minutes - set via: export ACCESS_TOKEN=$(python get_jwt_token.py --role studyadmin)
ACCESS_TOKEN = os.getenv('ACCESS_TOKEN')

if not ACCESS_TOKEN:
    print("ERROR: ACCESS_TOKEN environment variable not set!")
    print("Please run: export ACCESS_TOKEN=$(python get_jwt_token.py --role studyadmin)")
    exit(1)

# 40 Clinical Trial Protocols with comprehensive FHIR coverage
PROTOCOLS = [
    {
        "trial_id": "ONCO-2024-001",
        "title": "Phase III Trial for Advanced Non-Small Cell Lung Cancer",
        "criteria_text": """
Inclusion Criteria:
- Age between 18 and 75 years
- Histologically confirmed non-small cell lung cancer (NSCLC) Stage IIIB or IV
- ECOG performance status 0-1
- Adequate bone marrow function: Hemoglobin ≥9 g/dL, WBC ≥3000/μL, Platelet count ≥100,000/μL
- Adequate renal function: Serum creatinine ≤1.5 mg/dL or eGFR ≥60 mL/min/1.73m2
- Adequate hepatic function: Total bilirubin ≤1.5x ULN, AST and ALT ≤2.5x ULN
- Currently taking carboplatin or cisplatin chemotherapy
- Prior surgical resection documented within 6 months
- Up-to-date influenza vaccination
- Documented pathology report from diagnostic biopsy
- Active treatment plan documented

Exclusion Criteria:
- Known allergy to platinum-based chemotherapy agents
- History of interstitial lung disease
- Active brain metastases
- Pregnant or breastfeeding
- History of cardiac disease within last 6 months
- Family history of sudden cardiac death before age 50
"""
    },
    {
        "trial_id": "CARDIO-2024-002",
        "title": "Heart Failure with Reduced Ejection Fraction Study",
        "criteria_text": """
Inclusion Criteria:
- Age 40 years or older
- Diagnosed with chronic heart failure (NYHA Class II-III)
- Left ventricular ejection fraction ≤40% documented by echocardiogram
- On stable dose of ACE inhibitor or ARB for at least 3 months
- NT-proBNP >300 pg/mL or BNP >100 pg/mL
- Blood pressure: Systolic BP 90-160 mmHg
- Serum potassium between 3.5-5.0 mEq/L
- Currently taking beta-blocker medication
- Documented cardiac catheterization procedure within 12 months
- No known allergy to contrast dye
- Current cardiac rehabilitation care plan in place

Exclusion Criteria:
- Recent myocardial infarction (within 3 months)
- eGFR <30 mL/min/1.73m2
- History of ventricular arrhythmia
- Implanted cardiac device (pacemaker or ICD)
- Allergy to ACE inhibitors or ARBs
"""
    },
    {
        "trial_id": "DIABETES-2024-003",
        "title": "Type 2 Diabetes Mellitus with Obesity Management",
        "criteria_text": """
Inclusion Criteria:
- Age between 25 and 70 years
- Male or female gender
- Diagnosed with Type 2 Diabetes Mellitus for at least 1 year
- HbA1c between 7.5% and 11%
- BMI ≥30 kg/m2
- Fasting glucose between 126-300 mg/dL
- Currently on metformin therapy for at least 3 months
- C-peptide level >1.0 ng/mL
- Thyroid stimulating hormone (TSH) within normal range
- Total cholesterol <240 mg/dL
- LDL cholesterol <160 mg/dL
- Triglycerides <500 mg/dL
- Documented diabetes care plan with endocrinologist
- Completed hepatitis B vaccination series
- Recent ophthalmology exam report (diabetic retinopathy screening)

Exclusion Criteria:
- Type 1 Diabetes Mellitus diagnosis
- History of diabetic ketoacidosis
- Severe hypoglycemia events in past 6 months
- Known allergy to metformin or sulfonylureas
- Active foot ulcers or amputation
- Family history of Multiple Endocrine Neoplasia type 2
- Currently taking insulin therapy
- Liver function tests: ALT or AST >3x ULN
"""
    },
    {
        "trial_id": "NEURO-2024-004",
        "title": "Early Parkinson's Disease Neuroprotection Study",
        "criteria_text": """
Inclusion Criteria:
- Age 30-80 years
- Diagnosed with Parkinson's disease within past 2 years
- Hoehn and Yahr stage 1-2
- MoCA score ≥24 points
- Currently on levodopa/carbidopa medication
- Adequate dopamine transporter uptake on DaTscan imaging
- Normal vitamin B12 levels: >200 pg/mL
- Folate level >3 ng/mL
- Complete blood count within normal limits
- Documented neurology care plan
- Brain MRI report excluding other causes
- Completed pneumococcal vaccination

Exclusion Criteria:
- Secondary or atypical Parkinsonism
- Prior brain surgery or deep brain stimulation
- Known allergy to levodopa
- History of psychosis or dementia
- Significant depression: PHQ-9 score >15
- Family history of early-onset Parkinson's (before age 40)
- Current use of dopamine-blocking medications
"""
    },
    {
        "trial_id": "RHEUM-2024-005",
        "title": "Rheumatoid Arthritis Biologic Therapy Trial",
        "criteria_text": """
Inclusion Criteria:
- Age 18-75 years
- Diagnosed with Rheumatoid Arthritis meeting ACR/EULAR criteria
- Active disease: DAS28-CRP >3.2
- RF (Rheumatoid Factor) positive >20 IU/mL or Anti-CCP antibody positive >20 U/mL
- ESR (Erythrocyte Sedimentation Rate) ≥28 mm/hr or CRP ≥10 mg/L
- Inadequate response to methotrexate for at least 3 months
- Currently on stable DMARD therapy
- Adequate bone marrow: WBC ≥3500/μL, Platelets ≥150,000/μL
- Liver function: ALT and AST ≤2x ULN
- Negative QuantiFERON-TB Gold test or documented latent TB treatment
- Hepatitis B and C screening negative
- Up-to-date with MMR and varicella vaccinations
- Recent joint X-ray or ultrasound diagnostic report
- Active rheumatology care plan

Exclusion Criteria:
- Known allergy to biologic agents (TNF inhibitors, IL-6 inhibitors)
- Active infection requiring antibiotics
- History of lymphoma or solid organ malignancy (except treated skin cancer)
- Significant immunodeficiency documented
- Family history of autoimmune disease with severe complications
"""
    },
    {
        "trial_id": "NEPHRO-2024-006",
        "title": "Chronic Kidney Disease Progression Study",
        "criteria_text": """
Inclusion Criteria:
- Age 30-80 years
- Chronic Kidney Disease Stage 3b or 4
- eGFR between 15-44 mL/min/1.73m2
- Serum creatinine 2.0-5.0 mg/dL
- Proteinuria: Urine protein >500 mg/24hr or UACR >300 mg/g
- Blood pressure controlled: <140/90 mmHg
- Hemoglobin 9-12 g/dL (anemia of CKD)
- Serum albumin ≥3.0 g/dL
- Calcium level 8.5-10.5 mg/dL
- Phosphorus ≤5.5 mg/dL
- PTH (Parathyroid Hormone) 150-600 pg/mL
- Currently on ACE inhibitor or ARB therapy
- Documented nephrology care plan
- Recent renal ultrasound report

Exclusion Criteria:
- Known allergy to ACE inhibitors or ARBs
- Active kidney stones documented on imaging
- Acute kidney injury within past 3 months
- History of kidney transplantation
- Polycystic kidney disease diagnosis
- Currently on dialysis treatment
- Family history of hereditary nephritis
"""
    },
    {
        "trial_id": "HEPATO-2024-007",
        "title": "Non-Alcoholic Fatty Liver Disease (NAFLD) Study",
        "criteria_text": """
Inclusion Criteria:
- Age 25-70 years
- BMI ≥28 kg/m2
- Diagnosed with NAFLD via liver biopsy or imaging
- FibroScan liver stiffness 7-12 kPa (F2-F3 fibrosis)
- ALT (Alanine Aminotransferase) 40-120 U/L
- AST (Aspartate Aminotransferase) 35-100 U/L
- Fasting glucose ≤126 mg/dL or HbA1c <6.5%
- Total cholesterol 180-300 mg/dL
- Triglycerides 150-500 mg/dL
- Platelet count ≥150,000/μL
- INR (International Normalized Ratio) ≤1.2
- Albumin ≥3.5 g/dL
- No current hepatotoxic medications
- Hepatitis A and B vaccination completed
- Documented liver biopsy pathology report
- Active hepatology care plan

Exclusion Criteria:
- Known alcohol use disorder (>20g/day for females, >30g/day for males)
- Viral hepatitis B or C infection documented
- Hemochromatosis or Wilson's disease
- Autoimmune hepatitis diagnosis
- History of decompensated cirrhosis
- Known allergy to statins or fibrates
- Family history of hereditary liver disease
"""
    },
    {
        "trial_id": "ENDO-2024-008",
        "title": "Thyroid Cancer Post-Surgical Follow-up Study",
        "criteria_text": """
Inclusion Criteria:
- Age 18-75 years
- Histologically confirmed papillary or follicular thyroid cancer
- Post-total thyroidectomy (documented surgical procedure)
- TSH level >30 mIU/L (for RAI preparation) or <0.1 mIU/L (for suppression)
- Thyroglobulin level measurable
- Adequate bone marrow: WBC ≥3000/μL
- Adequate renal function: Creatinine ≤1.5 mg/dL
- Negative pregnancy test for females
- Recent whole body iodine scan diagnostic report
- Current endocrinology care plan
- Up-to-date tetanus vaccination

Exclusion Criteria:
- Anaplastic or medullary thyroid cancer
- Known iodine allergy
- Active hyperthyroidism or thyroid storm history
- Pregnancy or breastfeeding
- Prior radioactive iodine treatment >2 times
- Family history of multiple endocrine neoplasia syndromes
- Significant cardiac arrhythmias documented
"""
    },
    {
        "trial_id": "PULMO-2024-009",
        "title": "Severe Asthma Biologic Therapy Study",
        "criteria_text": """
Inclusion Criteria:
- Age 18-65 years
- Physician-diagnosed severe persistent asthma
- FEV1 (Forced Expiratory Volume) <80% predicted
- FEV1/FVC ratio <0.70
- Bronchodilator reversibility ≥12% and ≥200 mL
- Blood eosinophil count ≥300 cells/μL
- IgE level 30-700 IU/mL
- FeNO (Fractional exhaled Nitric Oxide) >25 ppb
- Currently on high-dose inhaled corticosteroids
- Currently on long-acting beta-agonist (LABA)
- At least 2 asthma exacerbations in past year requiring oral corticosteroids
- Documented pulmonary function test (spirometry) report
- Active pulmonology care plan
- Influenza vaccination current

Exclusion Criteria:
- Known allergy to monoclonal antibodies
- Chronic obstructive pulmonary disease (COPD) diagnosis
- Active smoking (current or quit <6 months ago)
- History of anaphylaxis
- Significant bronchiectasis on CT scan
- Parasitic infection documented
- Family history of severe drug allergies
"""
    },
    {
        "trial_id": "GASTRO-2024-010",
        "title": "Inflammatory Bowel Disease Maintenance Study",
        "criteria_text": """
Inclusion Criteria:
- Age 18-70 years
- Diagnosed with Crohn's disease or ulcerative colitis
- Moderate to severe disease activity: Mayo score 6-12 (UC) or CDAI 220-450 (Crohn's)
- C-reactive protein (CRP) ≥5 mg/L
- Fecal calprotectin >250 μg/g
- Hemoglobin 9-13 g/dL (anemia due to IBD)
- Albumin ≥2.8 g/dL
- Currently on stable dose of 5-ASA or azathioprine
- Adequate bone marrow function: WBC ≥3500/μL
- Recent colonoscopy with biopsy diagnostic report
- Active gastroenterology care plan
- Hepatitis B vaccination completed

Exclusion Criteria:
- Known allergy to anti-TNF agents or JAK inhibitors
- Active Clostridium difficile infection
- Intestinal abscess or stricture documented
- Prior bowel surgery for stricture or perforation
- History of colonic dysplasia or cancer
- Tuberculosis: positive QuantiFERON test without completed treatment
- Family history of inflammatory bowel disease with complications
"""
    },
    {
        "trial_id": "HEME-2024-011",
        "title": "Multiple Myeloma Maintenance Therapy Trial",
        "criteria_text": """
Inclusion Criteria:
- Age 40-80 years
- Diagnosed with multiple myeloma per IMWG criteria
- Post-autologous stem cell transplant (documented procedure)
- M-protein detectable in serum or urine
- Serum free light chain ratio abnormal (if non-secretory)
- Hemoglobin ≥8 g/dL
- Platelet count ≥75,000/μL
- Absolute neutrophil count ≥1000/μL
- Creatinine clearance ≥30 mL/min
- Calcium ≤11 mg/dL
- Currently on lenalidomide maintenance therapy
- ECOG performance status 0-2
- Bone marrow biopsy diagnostic report within 6 months
- Active hematology-oncology care plan
- Pneumococcal and influenza vaccinations up-to-date

Exclusion Criteria:
- Known allergy to lenalidomide or thalidomide
- Active plasma cell leukemia
- Peripheral neuropathy grade ≥3
- Prior allogeneic stem cell transplant
- Deep vein thrombosis within past 6 months
- Family history of thrombophilia
- Currently pregnant or breastfeeding
"""
    },
    {
        "trial_id": "IMMUNO-2024-012",
        "title": "Systemic Lupus Erythematosus Biologic Study",
        "criteria_text": """
Inclusion Criteria:
- Age 18-65 years
- Diagnosed with Systemic Lupus Erythematosus (ACR or SLICC criteria)
- Active disease: SLEDAI score ≥6
- Positive ANA (Antinuclear Antibody) titer ≥1:80
- Anti-dsDNA antibody positive or anti-Smith antibody positive
- Complement C3 <90 mg/dL or C4 <10 mg/dL
- Proteinuria: UPCR 0.5-6.0 g/g
- Currently on stable dose of prednisone ≤20 mg/day
- On hydroxychloroquine or immunosuppressant therapy
- Adequate bone marrow: WBC ≥2500/μL, Platelets ≥50,000/μL
- Negative pregnancy test
- Recent echocardiogram report (to exclude cardiac involvement)
- Active rheumatology care plan
- MMR vaccination documented

Exclusion Criteria:
- Known allergy to rituximab or belimumab
- Active lupus nephritis Class V
- CNS lupus with seizures or psychosis
- Severe thrombocytopenia: Platelets <30,000/μL
- History of severe infections requiring hospitalization
- Live vaccines within past 4 weeks
- Family history of autoimmune disease with early mortality
"""
    },
    {
        "trial_id": "DERM-2024-013",
        "title": "Moderate to Severe Psoriasis Systemic Therapy",
        "criteria_text": """
Inclusion Criteria:
- Age 18-70 years
- Plaque psoriasis for at least 6 months
- BSA (Body Surface Area) involvement ≥10%
- PASI (Psoriasis Area and Severity Index) score ≥12
- sPGA (static Physician Global Assessment) score ≥3
- Failed topical therapy for at least 3 months
- Adequate bone marrow: WBC ≥3500/μL
- Adequate hepatic function: ALT and AST <2x ULN
- Negative QuantiFERON-TB Gold test
- Currently on systemic therapy (methotrexate or cyclosporine)
- Recent skin biopsy diagnostic report confirming psoriasis
- Active dermatology care plan
- Hepatitis B vaccination completed

Exclusion Criteria:
- Known allergy to biologic agents (anti-IL17, anti-IL23)
- Guttate, pustular, or erythrodermic psoriasis
- Active infection requiring systemic antibiotics
- History of malignancy (except treated basal cell carcinoma)
- Tuberculosis: untreated latent or active disease
- Currently pregnant or breastfeeding
- Family history of severe psoriatic arthritis
"""
    },
    {
        "trial_id": "INFECT-2024-014",
        "title": "Chronic Hepatitis C Direct-Acting Antiviral Study",
        "criteria_text": """
Inclusion Criteria:
- Age 18-75 years
- Chronic Hepatitis C infection (HCV RNA detectable)
- HCV genotype 1, 2, or 3
- Treatment-naive or prior interferon failure
- HCV RNA viral load >10,000 IU/mL
- Liver fibrosis stage F0-F3 (FibroScan <12.5 kPa)
- ALT ≤10x ULN
- Total bilirubin ≤2x ULN
- Albumin ≥3.0 g/dL
- INR ≤1.5
- Platelet count ≥75,000/μL
- Creatinine clearance ≥50 mL/min
- Negative HIV antibody test
- Recent liver biopsy or elastography diagnostic report
- Active hepatology care plan
- Hepatitis A and B vaccination documented

Exclusion Criteria:
- Known allergy to direct-acting antivirals
- Decompensated cirrhosis: ascites, hepatic encephalopathy, variceal bleeding
- Hepatocellular carcinoma documented
- Co-infection with Hepatitis B or HIV
- Significant cardiac disease: QTc prolongation >500 ms
- Currently on prohibited drug interactions
- Family history of cirrhosis with hepatocellular carcinoma
"""
    },
    {
        "trial_id": "GERI-2024-015",
        "title": "Alzheimer's Disease Early Intervention Study",
        "criteria_text": """
Inclusion Criteria:
- Age 60-85 years
- Diagnosed with mild cognitive impairment (MCI) or mild Alzheimer's dementia
- MMSE (Mini-Mental State Exam) score 18-26
- MoCA (Montreal Cognitive Assessment) score 15-24
- Positive amyloid PET scan or CSF biomarkers (Aβ42 <600 pg/mL, tau >300 pg/mL)
- CDR (Clinical Dementia Rating) 0.5 or 1
- Adequate visual and auditory function for testing
- Reliable caregiver available
- Currently on stable dose of cholinesterase inhibitor (donepezil or rivastigmine)
- Brain MRI diagnostic report excluding other causes
- Active neurology or geriatrics care plan
- Pneumococcal vaccination documented

Exclusion Criteria:
- Known allergy to amyloid-targeting antibodies
- Other causes of dementia: vascular, Lewy body, frontotemporal
- Significant depression: GDS >10
- History of seizures or epilepsy
- Recent stroke or TIA within 6 months
- MRI contraindications: pacemaker, metal implants
- Family history of autosomal dominant Alzheimer's disease
- Currently on memantine therapy
"""
    },
    {
        "trial_id": "ORTHO-2024-016",
        "title": "Osteoarthritis Knee Joint Injection Study",
        "criteria_text": """
Inclusion Criteria:
- Age 45-75 years
- Diagnosed with knee osteoarthritis (Kellgren-Lawrence grade 2-3)
- Knee pain: VAS (Visual Analog Scale) ≥40/100
- WOMAC (Western Ontario McMaster) pain subscale ≥7
- Failed conservative management: PT, NSAIDs for at least 3 months
- BMI <40 kg/m2
- Adequate ambulation: able to walk 50 feet without assistive device
- Recent knee X-ray diagnostic report
- Active orthopedic care plan

Exclusion Criteria:
- Known allergy to hyaluronic acid or corticosteroids
- Intra-articular injection within past 3 months
- Active knee joint infection
- History of knee surgery within past 6 months
- Inflammatory arthritis: rheumatoid arthritis, gout
- Coagulopathy or on anticoagulation therapy
- Documented knee joint replacement planned within 6 months
"""
    },
    {
        "trial_id": "PSYCH-2024-017",
        "title": "Major Depressive Disorder Treatment-Resistant Study",
        "criteria_text": """
Inclusion Criteria:
- Age 18-65 years
- Diagnosed with Major Depressive Disorder per DSM-5 criteria
- Current major depressive episode ≥2 years
- HAM-D (Hamilton Depression Rating Scale) score ≥20
- PHQ-9 (Patient Health Questionnaire) score ≥15
- Failed at least 2 adequate trials of antidepressants
- Currently on stable SSRI or SNRI for at least 6 weeks
- No active suicidal ideation (C-SSRS score <4)
- Thyroid function tests normal: TSH 0.5-5.0 mIU/L
- Vitamin B12 and folate levels adequate
- Active psychiatry care plan
- Documented psychiatric evaluation report

Exclusion Criteria:
- Known allergy to ketamine or esketamine
- Bipolar disorder or schizoaffective disorder diagnosis
- Active substance use disorder (except tobacco)
- History of psychosis
- Uncontrolled hypertension: BP >160/100 mmHg
- Increased intracranial pressure or recent head injury
- Family history of suicide completion
- Currently pregnant or breastfeeding
"""
    },
    {
        "trial_id": "REPRO-2024-018",
        "title": "Polycystic Ovary Syndrome (PCOS) Fertility Study",
        "criteria_text": """
Inclusion Criteria:
- Age 18-40 years
- Female gender
- Diagnosed with PCOS (Rotterdam criteria)
- BMI 25-40 kg/m2
- Oligo-ovulation or anovulation documented
- Anti-Müllerian hormone (AMH) >3.0 ng/mL
- Antral follicle count ≥12 per ovary on ultrasound
- Fasting insulin >10 μU/mL or HOMA-IR >2.5
- Total testosterone 50-150 ng/dL
- LH/FSH ratio >2:1
- Currently on metformin therapy
- Recent pelvic ultrasound diagnostic report
- Active reproductive endocrinology care plan

Exclusion Criteria:
- Known allergy to clomiphene citrate or letrozole
- Other causes of hyperandrogenism: congenital adrenal hyperplasia, Cushing's
- Tubal factor infertility documented
- Male factor infertility
- Currently pregnant or breastfeeding
- Uncontrolled diabetes: HbA1c >8%
- Family history of ovarian hyperstimulation syndrome
"""
    },
    {
        "trial_id": "URO-2024-019",
        "title": "Benign Prostatic Hyperplasia Medical Management",
        "criteria_text": """
Inclusion Criteria:
- Age 50-80 years
- Male gender
- Diagnosed with benign prostatic hyperplasia (BPH)
- International Prostate Symptom Score (IPSS) ≥15
- Prostate volume ≥30 mL on ultrasound
- PSA (Prostate-Specific Antigen) 1.5-10 ng/mL
- Peak urinary flow rate (Qmax) <12 mL/s
- Post-void residual urine <300 mL
- Currently on alpha-blocker therapy (tamsulosin or alfuzosin)
- Adequate renal function: Creatinine <1.8 mg/dL
- Recent prostate MRI or ultrasound diagnostic report
- Active urology care plan

Exclusion Criteria:
- Known allergy to 5-alpha reductase inhibitors (finasteride, dutasteride)
- Prostate cancer documented on biopsy
- Urinary retention requiring catheterization
- History of prostate surgery: TURP or laser procedures
- Neurogenic bladder or urethral stricture
- Active urinary tract infection
- Hematuria of unknown etiology
"""
    },
    {
        "trial_id": "OPHTHAL-2024-020",
        "title": "Age-Related Macular Degeneration Anti-VEGF Study",
        "criteria_text": """
Inclusion Criteria:
- Age 55-90 years
- Diagnosed with wet (neovascular) age-related macular degeneration
- Visual acuity: 20/40 to 20/320 (ETDRS)
- Active choroidal neovascularization on OCT or fluorescein angiography
- Central retinal thickness ≥250 μm on OCT
- Treatment-naive or prior anti-VEGF therapy completed >3 months ago
- Adequate lens clarity for fundus examination
- Recent OCT and fundus photography diagnostic reports
- Active ophthalmology care plan

Exclusion Criteria:
- Known allergy to bevacizumab, ranibizumab, or aflibercept
- Geographic atrophy without neovascularization
- Other causes of vision loss: diabetic retinopathy, glaucoma
- Prior vitrectomy or scleral buckle surgery
- Active ocular infection or inflammation
- Uncontrolled glaucoma: IOP >25 mmHg
- History of stroke or MI within past 6 months
"""
    },
    {
        "trial_id": "ENT-2024-021",
        "title": "Chronic Rhinosinusitis with Nasal Polyps Biologic Study",
        "criteria_text": """
Inclusion Criteria:
- Age 18-70 years
- Diagnosed with chronic rhinosinusitis with nasal polyps (CRSwNP)
- Bilateral nasal polyps (endoscopic grade ≥2)
- Sino-Nasal Outcome Test (SNOT-22) score ≥30
- Blood eosinophil count ≥300 cells/μL
- IgE level 30-1500 IU/mL
- Failed medical therapy: intranasal corticosteroids and at least one course of oral steroids
- CT sinuses showing opacification
- Adequate sense of smell test: UPSIT score measurable
- Recent sinus CT diagnostic report
- Active ENT care plan
- Tetanus vaccination up-to-date

Exclusion Criteria:
- Known allergy to monoclonal antibodies (dupilumab, omalizumab)
- Cystic fibrosis diagnosis
- Aspirin-exacerbated respiratory disease with severe reactions
- Fungal sinusitis documented
- Prior sinus surgery within 3 months
- Active respiratory infection
- Immunodeficiency disorder documented
"""
    },
    {
        "trial_id": "PAIN-2024-022",
        "title": "Chronic Low Back Pain Non-Opioid Management",
        "criteria_text": """
Inclusion Criteria:
- Age 25-70 years
- Chronic low back pain >6 months duration
- Pain intensity: VAS ≥50/100
- Oswestry Disability Index (ODI) ≥30%
- Failed conservative treatment: PT, NSAIDs for at least 3 months
- MRI lumbar spine showing degenerative disc disease
- No radiculopathy: negative straight leg raise
- BMI <35 kg/m2
- Adequate mobility for functional assessments
- Recent lumbar spine MRI diagnostic report
- Active pain management care plan

Exclusion Criteria:
- Known allergy to gabapentinoids or SNRIs
- Opioid use >30 MME (morphine milligram equivalents) per day
- Spinal fracture or infection documented
- Prior lumbar spine surgery
- Active compensation or litigation
- Severe depression with suicidal ideation
- Substance use disorder documented
"""
    },
    {
        "trial_id": "ALLERGY-2024-023",
        "title": "Peanut Allergy Oral Immunotherapy Study",
        "criteria_text": """
Inclusion Criteria:
- Age 4-17 years
- Physician-diagnosed peanut allergy
- Positive skin prick test to peanut (wheal ≥3 mm)
- Peanut-specific IgE >0.35 kU/L
- Positive oral food challenge to peanut (reaction to ≤100 mg)
- History of allergic reaction to peanut within past year
- Adequate baseline spirometry: FEV1 ≥80% predicted
- Currently carrying epinephrine auto-injector
- Recent allergist evaluation report
- Active allergy care plan
- All routine childhood vaccinations up-to-date

Exclusion Criteria:
- Known allergy to epinephrine
- Severe eosinophilic esophagitis
- Uncontrolled asthma: FEV1 <80%, frequent exacerbations
- History of anaphylaxis requiring ICU admission
- Other significant food allergies with anaphylaxis
- Mastocytosis or elevated baseline tryptase
- Active atopic dermatitis requiring systemic therapy
- Family history of anaphylactic reactions to immunotherapy
"""
    },
    {
        "trial_id": "SLEEP-2024-024",
        "title": "Obstructive Sleep Apnea CPAP Adherence Study",
        "criteria_text": """
Inclusion Criteria:
- Age 30-70 years
- Diagnosed with moderate to severe obstructive sleep apnea
- AHI (Apnea-Hypopnea Index) ≥15 events/hour on polysomnography
- Oxygen desaturation index (ODI) ≥10 events/hour
- Excessive daytime sleepiness: Epworth Sleepiness Scale ≥10
- BMI 28-40 kg/m2
- CPAP-naive or poor adherence (<4 hours/night for >70% nights)
- Adequate cognitive function to use CPAP device
- Recent polysomnography diagnostic report
- Active sleep medicine care plan

Exclusion Criteria:
- Known allergy to CPAP mask materials
- Central sleep apnea (>50% central events)
- Severe COPD with chronic hypercapnia
- Recent myocardial infarction or unstable angina
- Prior upper airway surgery for OSA
- Significant nasal obstruction requiring surgery
- Severe claustrophobia preventing mask use
"""
    },
    {
        "trial_id": "TRAUMA-2024-025",
        "title": "Post-Traumatic Stress Disorder Pharmacotherapy Study",
        "criteria_text": """
Inclusion Criteria:
- Age 18-65 years
- Diagnosed with PTSD per DSM-5 criteria
- Index trauma occurred at least 3 months ago
- PCL-5 (PTSD Checklist) score ≥33
- CAPS-5 (Clinician-Administered PTSD Scale) ≥25
- Currently engaged in evidence-based psychotherapy
- Failed at least one SSRI trial
- No active substance use (negative urine drug screen)
- Adequate hepatic function: ALT and AST <2x ULN
- Adequate renal function: Creatinine <1.5 mg/dL
- Active psychiatry or psychology care plan
- Recent psychiatric evaluation report

Exclusion Criteria:
- Known allergy to prazosin or other alpha-blockers
- Bipolar disorder or schizophrenia diagnosis
- Active suicidal ideation (C-SSRS score ≥4)
- Severe alcohol use disorder
- Traumatic brain injury with cognitive impairment
- Hypotension: baseline BP <100/60 mmHg
- Currently pregnant or breastfeeding
- Family history of completed suicide
"""
    },
    {
        "trial_id": "ADDICTION-2024-026",
        "title": "Opioid Use Disorder Medication-Assisted Treatment",
        "criteria_text": """
Inclusion Criteria:
- Age 18-65 years
- Diagnosed with opioid use disorder (moderate to severe) per DSM-5
- Active opioid use or in early remission (<3 months)
- Positive urine drug screen for opioids
- Motivated for treatment: ready for medication-assisted therapy
- COWS (Clinical Opiate Withdrawal Scale) score available
- Adequate hepatic function: ALT and AST <5x ULN
- Hepatitis C screening completed (positive or negative acceptable)
- HIV screening completed
- Currently engaged with addiction medicine or psychiatry
- Recent comprehensive psychiatric evaluation report
- Active substance use disorder care plan

Exclusion Criteria:
- Known allergy to buprenorphine, naltrexone, or methadone
- Acute liver failure or decompensated cirrhosis
- Currently on long-term opioid therapy for chronic pain (prescribed)
- Severe benzodiazepine use disorder without medical supervision
- Active suicidal ideation
- Pregnancy without prenatal care established
- Severe psychiatric disorder requiring hospitalization
"""
    },
    {
        "trial_id": "PEDS-2024-027",
        "title": "Pediatric Growth Hormone Deficiency Treatment Study",
        "criteria_text": """
Inclusion Criteria:
- Age 3-15 years
- Diagnosed with growth hormone deficiency
- Height <3rd percentile for age and gender
- Growth velocity <4 cm/year
- Bone age delayed by ≥2 years
- IGF-1 (Insulin-like Growth Factor-1) <-2 SD for age
- Failed growth hormone stimulation test (peak GH <10 ng/mL)
- Normal thyroid function: TSH 0.5-5.0 mIU/L, Free T4 normal
- Brain MRI normal or showing pituitary hypoplasia
- No other causes of short stature
- Recent bone age X-ray and pituitary MRI diagnostic reports
- Active pediatric endocrinology care plan
- All recommended childhood vaccinations up-to-date

Exclusion Criteria:
- Known allergy to recombinant growth hormone (somatropin)
- Active malignancy or history of cancer
- Turner syndrome, Prader-Willi syndrome, or other genetic syndromes
- Severe scoliosis or intracranial hypertension
- Uncontrolled diabetes mellitus
- Family history of multiple endocrine neoplasia
- Closed epiphyses documented on X-ray
"""
    },
    {
        "trial_id": "WOMEN-2024-028",
        "title": "Endometriosis Pain Management Study",
        "criteria_text": """
Inclusion Criteria:
- Age 18-45 years
- Female gender
- Surgically confirmed endometriosis (laparoscopy with biopsy)
- Moderate to severe pelvic pain: VAS ≥50/100
- Dysmenorrhea requiring pain medication
- Failed NSAIDs and oral contraceptives for at least 3 months
- Regular menstrual cycles (21-35 days)
- CA-125 level available (may be elevated)
- Recent pelvic ultrasound or MRI diagnostic report
- Active gynecology care plan
- HPV vaccination completed

Exclusion Criteria:
- Known allergy to GnRH agonists or antagonists
- Currently pregnant or breastfeeding
- Desire for pregnancy within next 12 months
- Severe endometriosis with ovarian cysts requiring immediate surgery
- Other causes of pelvic pain: PID, fibroids
- Osteoporosis: T-score <-2.5 on DEXA scan
- Undiagnosed abnormal uterine bleeding
- Family history of early menopause or osteoporosis
"""
    },
    {
        "trial_id": "MEN-2024-029",
        "title": "Male Hypogonadism Testosterone Replacement Study",
        "criteria_text": """
Inclusion Criteria:
- Age 30-70 years
- Male gender
- Symptomatic hypogonadism: decreased libido, fatigue, erectile dysfunction
- Morning total testosterone <300 ng/dL (confirmed on 2 separate occasions)
- Free testosterone low for age
- LH and FSH levels available (to determine primary vs secondary)
- Adequate hemoglobin: Hgb 12-17 g/dL
- Hematocrit <50%
- PSA (Prostate-Specific Antigen) <4 ng/mL
- Normal digital rectal exam
- Recent PSA test and urinalysis reports
- Active endocrinology or urology care plan

Exclusion Criteria:
- Known allergy to testosterone formulations
- Prostate cancer or breast cancer documented
- Severe benign prostatic hyperplasia with urinary retention
- Untreated sleep apnea (AHI >15 without CPAP)
- Polycythemia: hematocrit >52%
- Congestive heart failure NYHA Class III-IV
- Recent MI or stroke within 6 months
- Desire for fertility preservation
"""
    },
    {
        "trial_id": "BONE-2024-030",
        "title": "Postmenopausal Osteoporosis Treatment Study",
        "criteria_text": """
Inclusion Criteria:
- Age 50-80 years
- Female gender
- Postmenopausal status (>12 months since last menstrual period)
- Osteoporosis: T-score ≤-2.5 on DEXA scan (spine or hip)
- At least one fragility fracture, or high FRAX score (≥20% major, ≥3% hip)
- Adequate vitamin D level: 25-OH vitamin D >20 ng/mL
- Serum calcium 8.5-10.5 mg/dL
- Adequate renal function: Creatinine clearance ≥30 mL/min
- PTH within normal limits
- Recent DEXA scan diagnostic report
- Active endocrinology or rheumatology care plan
- Tetanus and zoster vaccinations up-to-date

Exclusion Criteria:
- Known allergy to bisphosphonates or denosumab
- Hypocalcemia: serum calcium <8.5 mg/dL
- Severe vitamin D deficiency: <12 ng/mL
- Esophageal abnormalities (for oral bisphosphonates)
- Atypical femur fracture or osteonecrosis of the jaw
- Active dental issues or planned dental procedures
- Hyperparathyroidism or Paget's disease
- Family history of hypocalcemia or rickets
"""
    },
    {
        "trial_id": "VASCULAR-2024-031",
        "title": "Peripheral Artery Disease Claudication Study",
        "criteria_text": """
Inclusion Criteria:
- Age 50-85 years
- Diagnosed with peripheral artery disease (PAD)
- Intermittent claudication: walking impairment questionnaire score ≥25%
- Ankle-brachial index (ABI) 0.40-0.90
- Resting toe pressure >40 mmHg
- Peak walking time <12 minutes on treadmill test
- Currently on antiplatelet therapy (aspirin or clopidogrel)
- Currently on statin therapy
- Adequate renal function: eGFR ≥30 mL/min/1.73m2
- Recent lower extremity arterial doppler diagnostic report
- Active vascular surgery care plan

Exclusion Criteria:
- Known allergy to cilostazol or pentoxifylline
- Critical limb ischemia with rest pain or tissue loss
- Recent lower extremity revascularization (<3 months)
- Congestive heart failure NYHA Class III-IV
- Recent MI or stroke within 6 months
- Exercise limitation due to non-vascular causes (arthritis, COPD)
- Uncontrolled diabetes: HbA1c >10%
"""
    },
    {
        "trial_id": "AUTOIMMUNE-2024-032",
        "title": "Myasthenia Gravis Immunosuppression Study",
        "criteria_text": """
Inclusion Criteria:
- Age 18-75 years
- Diagnosed with myasthenia gravis (confirmed with antibody testing)
- Acetylcholine receptor antibody positive or MuSK antibody positive
- MG-ADL (Myasthenia Gravis Activities of Daily Living) score ≥3
- Generalized myasthenia (Class II-IV per MGFA classification)
- Currently on pyridostigmine (cholinesterase inhibitor)
- Failed or incomplete response to pyridostigmine alone
- Recent EMG with repetitive nerve stimulation diagnostic report
- Active neurology care plan
- Up-to-date pneumococcal and influenza vaccinations

Exclusion Criteria:
- Known allergy to corticosteroids or azathioprine
- Thymoma requiring immediate surgical intervention
- Myasthenic crisis requiring ICU care currently
- Recent thymectomy (<6 months)
- Severe immunosuppression or active infection
- Uncontrolled diabetes: HbA1c >9%
- Tuberculosis: positive QuantiFERON without treatment
- Family history of thymoma or autoimmune disease with complications
"""
    },
    {
        "trial_id": "METABOLIC-2024-033",
        "title": "Familial Hypercholesterolemia Lipid-Lowering Study",
        "criteria_text": """
Inclusion Criteria:
- Age 18-75 years
- Diagnosed with heterozygous familial hypercholesterolemia
- LDL cholesterol >190 mg/dL despite statin therapy
- Total cholesterol >300 mg/dL
- Family history of premature coronary artery disease (<55 years males, <65 females)
- Dutch Lipid Clinic Network score ≥6 (definite or probable FH)
- Currently on maximum tolerated statin dose
- Triglycerides <400 mg/dL
- Adequate hepatic function: ALT and AST <3x ULN
- CK (Creatine Kinase) <5x ULN
- Recent lipid panel and genetic testing reports (if available)
- Active cardiology or lipid clinic care plan

Exclusion Criteria:
- Known allergy to PCSK9 inhibitors or ezetimibe
- Homozygous familial hypercholesterolemia
- Severe statin-induced myopathy (history of rhabdomyolysis)
- Active liver disease: cirrhosis or hepatitis
- Recent acute coronary syndrome (<3 months)
- Currently pregnant or breastfeeding
- Uncontrolled hypertension: BP >180/110 mmHg
"""
    },
    {
        "trial_id": "BLEEDING-2024-034",
        "title": "Hemophilia A Factor Replacement Prophylaxis Study",
        "criteria_text": """
Inclusion Criteria:
- Age 12-65 years
- Diagnosed with moderate to severe Hemophilia A
- Factor VIII activity <5%
- At least 6 bleeding episodes in past 12 months
- At least 2 target joints with chronic arthropathy
- Currently on factor VIII replacement therapy (prophylaxis or on-demand)
- Adequate venous access for infusions
- No current inhibitor: Bethesda titer <0.6 BU
- Recent factor VIII level and inhibitor screening reports
- Active hematology care plan
- Hepatitis A and B vaccinations completed

Exclusion Criteria:
- Known allergy to recombinant factor VIII products
- High-titer inhibitors: Bethesda titer >5 BU
- Other bleeding disorders: von Willebrand disease, platelet disorders
- Active joint infection or septic arthritis
- HIV with CD4 count <200 (if applicable)
- Hepatitis C with decompensated cirrhosis
- Planned major surgery within next 3 months
- Family history of inhibitor development with severe complications
"""
    },
    {
        "trial_id": "KIDNEY-2024-035",
        "title": "IgA Nephropathy Immunosuppression Study",
        "criteria_text": """
Inclusion Criteria:
- Age 18-70 years
- Biopsy-proven IgA nephropathy
- Persistent proteinuria: UPCR >0.75 g/g despite ACE inhibitor/ARB therapy
- eGFR 30-90 mL/min/1.73m2
- Blood pressure controlled <130/80 mmHg
- Hematuria: >5 RBC/HPF on urinalysis
- Currently on maximum tolerated ACE inhibitor or ARB
- Adequate bone marrow: WBC ≥3500/μL
- Recent kidney biopsy pathology report
- Active nephrology care plan

Exclusion Criteria:
- Known allergy to corticosteroids or mycophenolate
- Rapidly progressive glomerulonephritis with crescents >50%
- Henoch-Schönlein purpura (IgA vasculitis) as primary diagnosis
- Secondary IgA nephropathy (liver disease, celiac disease)
- Prior kidney transplant
- Active infection: hepatitis B, hepatitis C, HIV, or tuberculosis
- Currently pregnant or breastfeeding
- Family history of ESRD requiring transplant
"""
    },
    {
        "trial_id": "CANCER-2024-036",
        "title": "Metastatic Colorectal Cancer Chemotherapy Study",
        "criteria_text": """
Inclusion Criteria:
- Age 18-75 years
- Histologically confirmed colorectal adenocarcinoma
- Metastatic disease (Stage IV)
- Measurable disease per RECIST 1.1 criteria
- ECOG performance status 0-1
- Adequate bone marrow: Hemoglobin ≥9 g/dL, ANC ≥1500/μL, Platelets ≥100,000/μL
- Adequate hepatic function: Total bilirubin ≤1.5x ULN, ALT and AST ≤3x ULN
- Adequate renal function: Creatinine clearance ≥50 mL/min
- Currently on or completed first-line chemotherapy (FOLFOX or FOLFIRI)
- Recent CT chest/abdomen/pelvis diagnostic report
- Recent colonoscopy with biopsy pathology report
- Active oncology care plan
- Influenza vaccination current

Exclusion Criteria:
- Known allergy to fluoropyrimidines, oxaliplatin, or irinotecan
- DPD (dihydropyrimidine dehydrogenase) deficiency documented
- Uncontrolled brain metastases
- Severe neuropathy: grade ≥2
- Active inflammatory bowel disease
- Recent major surgery <4 weeks
- Gilbert's syndrome with severe hyperbilirubinemia
- Family history of colorectal cancer with Lynch syndrome complications
- Currently pregnant or breastfeeding
"""
    },
    {
        "trial_id": "LIVER-2024-037",
        "title": "Primary Biliary Cholangitis Ursodeoxycholic Acid Study",
        "criteria_text": """
Inclusion Criteria:
- Age 25-75 years
- Diagnosed with primary biliary cholangitis (PBC)
- Positive anti-mitochondrial antibody (AMA) titer ≥1:40
- Elevated alkaline phosphatase >1.5x ULN
- GGT (Gamma-Glutamyl Transferase) elevated >2x ULN
- Total bilirubin <2.0 mg/dL (non-cirrhotic)
- ALT and AST <5x ULN
- Pruritus severity: VAS ≥30/100
- Currently treatment-naive for PBC or on suboptimal UDCA dose
- Recent liver biopsy pathology report (if performed)
- Active hepatology care plan
- Hepatitis A and B vaccinations documented

Exclusion Criteria:
- Known allergy to ursodeoxycholic acid (UDCA)
- Decompensated cirrhosis: ascites, encephalopathy, variceal bleeding
- Hepatocellular carcinoma documented
- Overlap syndrome with autoimmune hepatitis
- Extrahepatic biliary obstruction on imaging
- Currently pregnant or breastfeeding
- Severe osteoporosis with fragility fractures
- Family history of PBC with liver transplantation
"""
    },
    {
        "trial_id": "PANCREAS-2024-038",
        "title": "Chronic Pancreatitis Pain and Enzyme Replacement Study",
        "criteria_text": """
Inclusion Criteria:
- Age 18-70 years
- Diagnosed with chronic pancreatitis
- Recurrent abdominal pain: VAS ≥40/100
- CT or MRI evidence of chronic pancreatitis (calcifications, ductal changes)
- Pancreatic exocrine insufficiency: fecal elastase <200 μg/g stool
- Steatorrhea: fecal fat >7 g/day
- Elevated fasting glucose or diabetes mellitus due to pancreatic insufficiency
- Currently on pancreatic enzyme replacement therapy
- Adequate nutritional status: albumin >3.0 g/dL
- Fat-soluble vitamin levels: A, D, E, K measurable
- Recent pancreatic CT or MRI diagnostic report
- Active gastroenterology care plan

Exclusion Criteria:
- Known allergy to pancreatic enzyme products (porcine-derived)
- Acute pancreatitis episode within past 4 weeks
- Pancreatic cancer documented
- Severe malabsorption requiring TPN (total parenteral nutrition)
- Active alcohol use disorder (contraindication)
- Prior pancreatic surgery: Whipple or total pancreatectomy
- Uncontrolled diabetes: HbA1c >10%
- Fibrosing colonopathy (associated with high-dose enzymes)
"""
    },
    {
        "trial_id": "RARE-2024-039",
        "title": "Gaucher Disease Enzyme Replacement Therapy Study",
        "criteria_text": """
Inclusion Criteria:
- Age 2-65 years
- Diagnosed with Gaucher disease type 1 (confirmed by enzyme assay)
- Glucocerebrosidase enzyme activity <30% of normal
- Splenomegaly: spleen volume >5 multiples of normal (MN)
- Thrombocytopenia: platelet count <60,000/μL
- Anemia: hemoglobin <11 g/dL
- Bone involvement: bone pain, bone crises, or avascular necrosis on MRI
- Chitotriosidase level elevated >1000 nmol/mL/hr
- Currently treatment-naive for enzyme replacement therapy
- Recent Gaucher cell identification in bone marrow biopsy report
- Active medical genetics or hematology care plan
- All age-appropriate vaccinations up-to-date

Exclusion Criteria:
- Known allergy to imiglucerase or other enzyme replacement therapies
- Gaucher disease type 2 or 3 (neuronopathic forms)
- Significant antibody development to ERT in past
- Severe liver disease: cirrhosis with hepatic dysfunction
- Active malignancy
- Severe immunodeficiency disorder
- Pregnancy (ERT decision requires specialist consultation)
- Family history of severe Gaucher complications with poor ERT response
"""
    },
    {
        "trial_id": "VACCINE-2024-040",
        "title": "Influenza Vaccine Immunogenicity in Immunocompromised Patients",
        "criteria_text": """
Inclusion Criteria:
- Age 18-80 years
- Immunocompromised status: on immunosuppressive therapy or with immunodeficiency
- Conditions: HIV with CD4 200-500, solid organ transplant recipients, or on biologic therapies
- Willing to receive high-dose or adjuvanted influenza vaccine
- Adequate baseline immune function for vaccine response assessment
- CD4 count ≥200 cells/μL (if HIV)
- HIV viral load <1000 copies/mL (if HIV)
- Adequate bone marrow: WBC ≥2000/μL
- No acute illness or fever >100.4°F at vaccination
- Recent immunology panel and lymphocyte subset analysis report
- Active infectious disease or immunology care plan
- Vaccination record documented

Exclusion Criteria:
- Known allergy to eggs, influenza vaccine components, or previous severe reaction
- Guillain-Barré syndrome within 6 weeks of prior influenza vaccine
- Received influenza vaccine in current season already
- Active severe immunodeficiency: CD4 <200 or severe combined immunodeficiency
- Active acute infection requiring antibiotics
- Recent live vaccine administration within past 4 weeks
- Febrile illness within past week
- Family history of severe vaccine reactions
- Currently pregnant in first trimester (relative exclusion)
"""
    }
]


def send_to_parse_criteria(protocol: Dict) -> Dict:
    """
    Send a protocol to the criteria parser API

    Args:
        protocol: Dictionary with trial_id and criteria_text

    Returns:
        API response as dictionary
    """
    try:
        payload = {
            "trial_id": protocol["trial_id"],
            "criteria_text": protocol["criteria_text"]
        }

        print(f"\n{'='*80}")
        print(f"Processing: {protocol['trial_id']}")
        print(f"Title: {protocol.get('title', 'N/A')}")
        print(f"{'='*80}")

        # Call API with authentication
        headers = {
            "Authorization": f"Bearer {ACCESS_TOKEN}",
            "Content-Type": "application/json"
        }

        response = requests.post(
            API_URL,
            headers=headers,
            json=payload,
            timeout=300  # 5 minute timeout for Bedrock processing
        )

        # Check if request was successful
        response.raise_for_status()

        result = response.json()

        print(f"✅ SUCCESS: {protocol['trial_id']}")
        if 'parsed_criteria' in result:
            parsed = result['parsed_criteria']
            if isinstance(parsed, dict):
                inc_count = len(parsed.get('inclusion', []))
                exc_count = len(parsed.get('exclusion', []))
            else:
                # Count by type if it's an array
                inc_count = len([c for c in parsed if c.get('type') == 'inclusion'])
                exc_count = len([c for c in parsed if c.get('type') == 'exclusion'])
            print(f"   - Inclusion criteria: {inc_count}")
            print(f"   - Exclusion criteria: {exc_count}")

        return {
            "trial_id": protocol["trial_id"],
            "success": True,
            "response": result
        }

    except requests.exceptions.HTTPError as e:
        error_msg = f"{e.response.status_code} {e.response.reason}"
        try:
            error_detail = e.response.json()
            error_msg += f": {error_detail.get('message', str(error_detail))}"
        except:
            error_msg += f": {e.response.text}"
        print(f"❌ ERROR: {protocol['trial_id']} - {error_msg}")
        return {
            "trial_id": protocol["trial_id"],
            "success": False,
            "error": error_msg
        }
    except Exception as e:
        print(f"❌ ERROR: {protocol['trial_id']} - {str(e)}")
        return {
            "trial_id": protocol["trial_id"],
            "success": False,
            "error": str(e)
        }


def main():
    """
    Main function to seed all protocols
    """
    print("\n" + "="*80)
    print("CLINICAL TRIAL PROTOCOL SEEDING SCRIPT")
    print("="*80)
    print(f"\nTotal protocols to process: {len(PROTOCOLS)}")
    print(f"API Endpoint: {API_URL}")
    print("\nStarting protocol processing...")
    print("="*80)

    results = []

    # Process only first 20 protocols
    protocols_to_process = PROTOCOLS[:20]

    for i, protocol in enumerate(protocols_to_process, 1):
        print(f"\n[{i}/{len(protocols_to_process)}] Processing {protocol['trial_id']}...")

        result = send_to_parse_criteria(protocol)
        results.append(result)

        # Add delay between requests to avoid rate limiting
        if i < len(protocols_to_process):
            time.sleep(2)

    # Summary
    print("\n" + "="*80)
    print("SEEDING SUMMARY")
    print("="*80)

    successful = [r for r in results if r['success']]
    failed = [r for r in results if not r['success']]

    print(f"\n✅ Successful: {len(successful)}/{len(protocols_to_process)}")
    print(f"❌ Failed: {len(failed)}/{len(protocols_to_process)}")

    if failed:
        print("\nFailed protocols:")
        for result in failed:
            print(f"  - {result['trial_id']}: {result.get('error', 'Unknown error')}")

    print("\n" + "="*80)
    print("Seeding complete!")
    print("="*80)

    # Save results to file
    with open('/tmp/seeding_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\nDetailed results saved to: /tmp/seeding_results.json")


if __name__ == "__main__":
    main()
