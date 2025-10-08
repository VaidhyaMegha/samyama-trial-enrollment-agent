# Remaining FHIR Resources - Implementation TODO

**Date:** October 8, 2025
**Status:** Planning Phase
**Priority:** Medium (after current resources are fully tested)

---

## Overview

This document outlines the remaining 9 FHIR resources to be implemented for comprehensive clinical trial eligibility checking.

**Current Status:** 6/15 FHIR resources implemented (40%)
**Target:** 12/15 resources (80% coverage of real-world trials)

---

## Priority Ranking (by real-world trial frequency)

### 🔴 HIGH PRIORITY (Next Sprint)

#### 1. Procedure ⭐⭐⭐⭐
**Real-world Trial Frequency:** 54% of trials
**Effort:** 2-3 days
**Complexity:** Medium

**Purpose:** Surgical history, biopsies, procedures

**Required Coding Systems:**
- **CPT** (Current Procedural Terminology)
- **SNOMED CT** (for procedure types)
- **ICD-10-PCS** (for hospital procedures)

**Common Criteria Examples:**
- "No prior cancer surgery within 6 months"
- "History of coronary artery bypass graft"
- "Prior diagnostic biopsy required"
- "No surgical procedures within 4 weeks"

**Implementation Tasks:**
- [ ] Add Procedure resource support to FHIR search handler
- [ ] Add CPT/SNOMED examples to parser prompt
- [ ] Implement procedure date filtering
- [ ] Support temporal criteria ("within X months")
- [ ] Create test patients with procedure history
- [ ] Test end-to-end

**Coding System Examples Needed:**
- Mastectomy (CPT: 19301-19307)
- Biopsy (CPT: 10021, 19081-19086)
- CABG (CPT: 33510-33536)
- Colonoscopy (CPT: 45378-45392)
- Appendectomy (CPT: 44950-44970)

---

#### 2. MedicationRequest (Prescriptions) ⭐⭐⭐⭐
**Real-world Trial Frequency:** 68% of trials
**Effort:** 1-2 days
**Complexity:** Low (similar to MedicationStatement)

**Purpose:** Prescribed medications (vs. MedicationStatement = taken medications)

**Required Coding Systems:**
- **RxNorm** (same as MedicationStatement)

**Common Criteria Examples:**
- "Prescribed chemotherapy within 6 months"
- "Not currently prescribed immunosuppressants"
- "On prescribed anticoagulation therapy"

**Implementation Tasks:**
- [ ] Add MedicationRequest support to FHIR search handler
- [ ] Reuse RxNorm examples from MedicationStatement
- [ ] Add prescription status filtering (active, completed, stopped)
- [ ] Test with prescribed medications
- [ ] Document differences from MedicationStatement

**Note:** Can largely reuse MedicationStatement code

---

#### 3. DiagnosticReport ⭐⭐⭐
**Real-world Trial Frequency:** 56% of trials
**Effort:** 3-4 days
**Complexity:** Medium-High

**Purpose:** Imaging results, pathology reports, lab report summaries

**Required Coding Systems:**
- **LOINC** (for report types)
- **SNOMED CT** (for findings)

**Common Criteria Examples:**
- "CT scan showing no metastasis"
- "Pathology report confirming breast cancer"
- "MRI within 6 months"
- "Echocardiogram showing ejection fraction >40%"

**Implementation Tasks:**
- [ ] Add DiagnosticReport support to FHIR search handler
- [ ] Add LOINC codes for common reports
- [ ] Support conclusion/finding text search
- [ ] Support coded findings
- [ ] Add temporal filtering ("within X months")
- [ ] Create test patients with diagnostic reports
- [ ] Test end-to-end

**Coding System Examples Needed:**
- CT Chest (LOINC: 24627-2)
- MRI Brain (LOINC: 24556-3)
- Echocardiogram (LOINC: 34552-0)
- Mammogram (LOINC: 24606-6)
- Pathology report (LOINC: 11526-1)

---

### 🟠 MEDIUM PRIORITY (Future Sprints)

#### 4. Encounter ⭐⭐
**Real-world Trial Frequency:** 42% of trials
**Effort:** 2-3 days
**Complexity:** Medium

**Purpose:** Hospital visits, emergency visits, admission history

**Required Coding Systems:**
- **CPT** (for visit types)
- **SNOMED CT** (for encounter reasons)

**Common Criteria Examples:**
- "No hospitalizations within 3 months"
- "No emergency room visits within 30 days"
- "Outpatient visit required for screening"

**Implementation Tasks:**
- [ ] Add Encounter support to FHIR search handler
- [ ] Support encounter class (inpatient, outpatient, emergency)
- [ ] Support encounter status
- [ ] Add temporal filtering
- [ ] Create test patients with encounters
- [ ] Test end-to-end

---

#### 5. Immunization ⭐
**Real-world Trial Frequency:** 23% of trials
**Effort:** 1-2 days
**Complexity:** Low

**Purpose:** Vaccination history

**Required Coding Systems:**
- **CVX** (Vaccine codes)
- **SNOMED CT** (for vaccines)

**Common Criteria Examples:**
- "COVID-19 vaccination required"
- "No live vaccines within 4 weeks"
- "Flu vaccine within current season"

**Implementation Tasks:**
- [ ] Add Immunization support to FHIR search handler
- [ ] Add CVX codes for common vaccines
- [ ] Support vaccination status
- [ ] Add temporal filtering
- [ ] Create test patients with immunizations
- [ ] Test end-to-end

**Coding System Examples Needed:**
- COVID-19 vaccine (CVX: 207-212)
- Influenza vaccine (CVX: 141, 150, 161, 185)
- Hepatitis B vaccine (CVX: 08, 44, 51)

---

#### 6. DeviceUseStatement ⭐
**Real-world Trial Frequency:** 18% of trials
**Effort:** 1-2 days
**Complexity:** Low

**Purpose:** Medical devices (pacemakers, implants, etc.)

**Required Coding Systems:**
- **SNOMED CT** (for device types)

**Common Criteria Examples:**
- "Has pacemaker implanted"
- "No implanted defibrillator"
- "Using insulin pump"
- "Has prosthetic joint"

**Implementation Tasks:**
- [ ] Add DeviceUseStatement support to FHIR search handler
- [ ] Add SNOMED codes for common devices
- [ ] Support device status
- [ ] Create test patients with devices
- [ ] Test end-to-end

---

### 🟡 LOW PRIORITY (Optional)

#### 7. FamilyMemberHistory ⭐
**Real-world Trial Frequency:** 15% of trials
**Effort:** 2-3 days
**Complexity:** Medium

**Purpose:** Family history of diseases

**Required Coding Systems:**
- **SNOMED CT** (for conditions)
- **ICD-10** (for diagnoses)

**Common Criteria Examples:**
- "Family history of breast cancer"
- "No family history of genetic disorders"
- "First-degree relative with diabetes"

**Implementation Tasks:**
- [ ] Add FamilyMemberHistory support to FHIR search handler
- [ ] Support relationship filtering (first-degree, second-degree)
- [ ] Support condition matching
- [ ] Create test patients with family history
- [ ] Test end-to-end

---

#### 8. Coverage (Insurance) ⭐
**Real-world Trial Frequency:** 12% of trials
**Effort:** 1-2 days
**Complexity:** Low

**Purpose:** Insurance coverage information

**Required Coding Systems:**
- None (uses coverage type codes)

**Common Criteria Examples:**
- "Has Medicare coverage"
- "Has commercial insurance"
- "Insured for trial duration"

**Implementation Tasks:**
- [ ] Add Coverage support to FHIR search handler
- [ ] Support coverage type filtering
- [ ] Support coverage status
- [ ] Create test patients with coverage
- [ ] Test end-to-end

---

#### 9. CareTeam ⭐
**Real-world Trial Frequency:** 8% of trials
**Effort:** 1-2 days
**Complexity:** Low

**Purpose:** Care team members (oncologist, PCP, etc.)

**Required Coding Systems:**
- **SNOMED CT** (for roles)

**Common Criteria Examples:**
- "Has assigned oncologist"
- "Under care of cardiologist"
- "Primary care physician established"

**Implementation Tasks:**
- [ ] Add CareTeam support to FHIR search handler
- [ ] Support role filtering
- [ ] Support participant type
- [ ] Create test patients with care teams
- [ ] Test end-to-end

---

## Implementation Roadmap

### Phase 1: High Priority (Next 2-3 weeks)
1. **Week 1:** Procedure resource (2-3 days)
2. **Week 2:** MedicationRequest (1-2 days) + DiagnosticReport (3-4 days)

**Outcome:** Coverage increases from 70% → 85% of real-world trials

---

### Phase 2: Medium Priority (Month 2)
1. Encounter (2-3 days)
2. Immunization (1-2 days)
3. DeviceUseStatement (1-2 days)

**Outcome:** Coverage increases to 90% of real-world trials

---

### Phase 3: Low Priority (Optional)
1. FamilyMemberHistory (2-3 days)
2. Coverage (1-2 days)
3. CareTeam (1-2 days)

**Outcome:** Coverage increases to 92-95% of real-world trials

---

## Effort Estimation Summary

| Resource | Effort (days) | Priority | Trial Frequency |
|----------|--------------|----------|-----------------|
| Procedure | 2-3 | 🔴 High | 54% |
| MedicationRequest | 1-2 | 🔴 High | 68% |
| DiagnosticReport | 3-4 | 🔴 High | 56% |
| Encounter | 2-3 | 🟠 Medium | 42% |
| Immunization | 1-2 | 🟠 Medium | 23% |
| DeviceUseStatement | 1-2 | 🟠 Medium | 18% |
| FamilyMemberHistory | 2-3 | 🟡 Low | 15% |
| Coverage | 1-2 | 🟡 Low | 12% |
| CareTeam | 1-2 | 🟡 Low | 8% |

**Total Effort:**
- Phase 1 (High Priority): 6-9 days
- Phase 2 (Medium Priority): 5-7 days
- Phase 3 (Low Priority): 5-7 days

**Total:** 16-23 days of development

---

## Expected Coverage by Phase

| Phase | Resources Implemented | Trial Coverage |
|-------|---------------------|----------------|
| Current | 6 | 70-75% |
| Phase 1 | 9 | 85-90% |
| Phase 2 | 12 | 90-92% |
| Phase 3 | 15 | 92-95% |

---

## Temporal Criteria Support

**Note:** Many resources require temporal criteria support ("within X months", "at least Y days ago")

**Implementation Needed:**
- Date range filtering in FHIR queries
- Parser support for temporal expressions
- Date arithmetic in evaluation logic

**Effort:** 2-3 days (can be done in parallel with resource implementation)

**Priority:** 🔴 HIGH (needed for Procedure, DiagnosticReport, etc.)

---

## Recommendations

### Immediate Next Steps:
1. ✅ Complete testing of current 6 resources
2. ✅ Deploy enhanced parser with new coding systems
3. 🔴 Implement temporal criteria support (foundation for next resources)
4. 🔴 Implement Procedure resource (highest impact)

### Success Criteria for Each Resource:
- [ ] Parser prompt examples (3-5 examples with coding systems)
- [ ] FHIR search handler support
- [ ] Test patients in HealthLake (3-5 patients)
- [ ] Postman test collection (5-10 tests)
- [ ] End-to-end validation
- [ ] Documentation

### Resource Template:
Each new resource should follow this pattern:
1. Add parser prompt examples (30-60 mins)
2. Implement FHIR search function (2-4 hours)
3. Create test patients (1-2 hours)
4. Create Postman tests (1-2 hours)
5. End-to-end testing (1-2 hours)
6. Documentation (1 hour)

---

## Status

**Current:** 6/15 resources implemented (40%)
**Target (Phase 1):** 9/15 resources (60%)
**Target (Phase 2):** 12/15 resources (80%)
**Ultimate Goal:** 15/15 resources (100%)

**Next Action:** Implement temporal criteria support + Procedure resource

---

**Version:** 1.0
**Last Updated:** October 8, 2025
**Owner:** Development Team
**Next Review:** October 15, 2025
