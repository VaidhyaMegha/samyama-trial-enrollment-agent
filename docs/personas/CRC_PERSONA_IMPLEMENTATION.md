# Clinical Research Coordinator (CRC) Persona - Implementation Documentation

**Status**: ✅ **PRODUCTION READY**
**Last Updated**: October 14, 2025
**Version**: 1.0.0

---

## Overview

The Clinical Research Coordinator (CRC) persona is the primary user role responsible for patient screening, eligibility assessment, and initial match approval in the Trial Compass Pro system. This document details all implemented functionalities for the CRC role.

---

## Authentication & Authorization

### Cognito Integration

- **User Pool**: Integrated with AWS Cognito User Pool
- **Group Assignment**: Users are assigned to the `CRC` group
- **JWT Token-Based Auth**: All API calls include Bearer token with group claims
- **Session Management**: Automatic token refresh and session validation

### Test Credentials

```
Username: crc_test
Password: [Configured in Cognito]
Group: CRC
Name: Sarah Johnson (CRC)
Email: crc.test@example.com
```

### Role-Based Access Control (RBAC)

CRCs have access to the following operations:

| Operation                | Endpoint                   | Access Level        |
| ------------------------ | -------------------------- | ------------------- |
| Patient Search           | `GET /patients`          | ✅ Full Access      |
| Patient Creation         | `POST /patients`         | ✅ Full Access      |
| Protocol Listing         | `GET /protocols`         | ✅ Read-Only        |
| Protocol Search          | `POST /protocols/search` | ✅ Read-Only        |
| Eligibility Check        | `POST /check-criteria`   | ✅ Full Access      |
| Match Creation           | `POST /matches`          | ✅ Full Access      |
| Match Review (CRC Level) | `PUT /matches/{id}`      | ✅ First-Level Only |
| Parse criteria           | `POST /parse-criteria`   | ✅ Full Access      |

---

## Implemented Features

### 1. Patient Management

#### Patient Search & Discovery

**Location**: `/patients` page

**Features**:

- Real-time search across AWS HealthLake FHIR R4 datastore
- Search by: Name, Gender, Age, ECOG Status, Conditions
- Interactive patient cards with key demographics
- Direct navigation to eligibility check from patient card

**Implementation Details**:

- Frontend: `trial-compass-pro/src/pages/Patients.tsx`
- Backend: `aws-trial-enrollment-agent/src/lambda/patient_manager/handler.py`
- API: `GET /patients?name=...&gender=...&age=...`

**FHIR Resources Queried**:

- Patient (demographics)
- Observation (ECOG status, lab values)
- Condition (diagnoses)

#### Patient Creation

**Features**:

- Create new patients directly in HealthLake
- Support for 11 FHIR resource types
- Comprehensive data entry form
- Automatic FHIR Bundle generation

**Supported FHIR Resources**:

1. **Patient**: Demographics (name, gender, birth date)
2. **Condition**: Diagnoses, cancer type, stage
3. **Observation**: Lab values (hemoglobin, platelets, creatinine, WBC, etc.)
4. **Observation**: Performance status (ECOG, Karnofsky)
5. **MedicationStatement**: Current medications
6. **AllergyIntolerance**: Known allergies
7. **Procedure**: Prior treatments and surgeries
8. **Immunization**: Vaccination history
9. **FamilyMemberHistory**: Family medical history
10. **Encounter**: Visit history
11. **DiagnosticReport**: Lab and imaging reports

---

### 2. Protocol Management

#### Protocol Discovery

**Location**: `/eligibility-check` page

**Features**:

- View all available clinical trial protocols
- Real-time search by protocol ID, title, or disease
- Protocol metadata display:
  - NCT ID
  - Title
  - Disease area
  - Phase
  - Status
  - Enrollment targets
  - Criteria count

**Implementation Details**:

- Frontend: `trial-compass-pro/src/pages/EligibilityCheck.tsx`
- Backend: `aws-trial-enrollment-agent/src/lambda/protocol_manager/handler.py`
- API: `GET /protocols`, `POST /protocols/search`

#### Protocol Upload & Processing

**Features**:

- Upload protocol PDF documents (up to 100-200 pages)
- Automated text extraction via AWS Textract
- Medical entity recognition via AWS Comprehend Medical
- Structured criteria parsing via Amazon Bedrock (Mistral LLM)
- Criteria caching in DynamoDB

**Workflow**:

```
PDF Upload → Textract (Extract Text) → Comprehend Medical (Structure)
→ Bedrock LLM (Parse to FHIR) → DynamoDB Cache → Ready for Matching
```

**Implementation**:

- Script: `aws-trial-enrollment-agent/scripts/process_protocol_pdf.py`
- API: `POST /parse-criteria`
- Lambda: `bedrock_criteria_parser`

---

### 3. Eligibility Assessment

#### Modern Eligibility Check Interface

**Location**: `/eligibility-check` page

**Features**:

- **Animated Circular Progress Indicator**:

  - Beautiful SVG-based progress circle
  - Animates from 0% to match score
  - Color-coded (green >80%, yellow 50-80%, red <50%)
- **Statistics Dashboard**:

  - Criteria Met (with percentage)
  - Criteria Not Met
  - Total Criteria Evaluated
  - Overall Recommendation (Highly Eligible / Potentially Eligible / Review Required)
- **Interactive Criteria Cards**:

  - Color-coded by status (green for met, red for not met)
  - Check/X icons for visual clarity
  - Hover effects for interactivity
  - Detailed patient values and reasoning
  - Confidence scores per criterion
- **PDF Export Functionality**:

  - Professional PDF report generation
  - Includes protocol info, patient data, overall score, detailed criteria table
  - Color-coded status indicators
  - Automatic download with timestamp

**Patient Data Entry**:

- Manual entry form with 11 FHIR resource sections
- Support for all major clinical data points
- Real-time validation
- Accordion-based organization for easy navigation

**Eligibility Check Process**:

1. Select protocol from dropdown (searches cached criteria)
2. Enter patient data (manual or from existing patient)
3. Click "Check Eligibility"
4. System:
   - Fetches cached parsed criteria from DynamoDB
   - Creates temporary patient in HealthLake (if needed)
   - Queries HealthLake FHIR data
   - Evaluates each criterion against patient data
   - Returns detailed results with confidence scores
5. View animated results with statistics
6. Export PDF report if needed
7. Create match for PI approval

**Implementation**:

- Frontend: `trial-compass-pro/src/pages/EligibilityCheck.tsx` (lines 1021-1332)
- Backend: `aws-trial-enrollment-agent/src/lambda/fhir_search/handler.py`
- API: `POST /check-criteria`

---

### 4. Match Management & 2-Level Approval Workflow

#### CRC's Role in Match Approval

**Location**: `/matches` page

**Features**:

- View all matches across all workflow stages
- 5 tab interface:
  - **CRC Review**: Matches awaiting CRC approval
  - **PI Approval**: Matches sent to PI for final approval
  - **Approved**: Fully approved matches
  - **Rejected**: Rejected matches
  - **All**: Complete match history

#### 2-Level Approval Workflow

**Workflow Stages**:

```
[CRC Creates Match]
    ↓
[pending] - CRC Reviews and Approves
    ↓
[pending_pi_approval] - PI Reviews and Gives Final Approval
    ↓
[approved] - Patient Can Enroll
```

**Rejection Flow**:

```
[pending] → CRC Rejects → [rejected]
[pending_pi_approval] → PI Rejects → [rejected]
```

**CRC Responsibilities**:

1. **Create Matches**: After eligibility check, create matches for promising candidates
2. **First-Level Review**: Review match details and approve to send to PI
3. **Limited Rejection**: Can reject matches at pending stage

**Role-Based Access Control**:

- CRCs can only approve `pending` matches (moves to `pending_pi_approval`)
- CRCs cannot perform final approval (reserved for PI)
- UI enforces role separation:
  - Shows "Approve & Send to PI" button for `pending` matches
  - Shows "Only Principal Investigator (PI) can provide final approval" message for `pending_pi_approval` matches

**Match Card Display**:

- Patient ID and name
- Protocol name
- Match score (color-coded)
- Status badge with icon
- Protocol ID
- Match creation date
- Workflow-specific action buttons and status messages

**Backend Validation**:

- Lambda function validates all status transitions
- Tracks CRC reviewer and timestamp
- Prevents invalid state changes
- Returns detailed error messages for invalid transitions

**Implementation**:

- Frontend: `trial-compass-pro/src/pages/Matches.tsx`
- Backend: `aws-trial-enrollment-agent/src/lambda/match_manager/handler.py`
- API: `GET /matches`, `POST /matches`, `PUT /matches/{id}`

---

## Technical Architecture

### Frontend Stack

- **Framework**: React 18 + TypeScript
- **UI Library**: shadcn/ui components
- **Animations**: Framer Motion
- **PDF Generation**: jsPDF + jspdf-autotable
- **Auth**: AWS Amplify + Cognito
- **API Client**: Axios with JWT interceptor
- **Routing**: React Router v6

### Backend Stack

- **Compute**: AWS Lambda (Python 3.11)
- **API Gateway**: REST API with Lambda Authorizer
- **Authentication**: AWS Cognito User Pools
- **Data Storage**:
  - AWS HealthLake (FHIR R4 datastore)
  - DynamoDB (criteria cache, matches)
- **AI/ML Services**:
  - Amazon Textract (PDF text extraction)
  - Amazon Comprehend Medical (medical entity recognition)
  - Amazon Bedrock (Mistral LLM for criteria parsing)

### Lambda Functions

| Function                    | Purpose                      | Trigger     |
| --------------------------- | ---------------------------- | ----------- |
| `patient_manager`         | CRUD operations for patients | API Gateway |
| `protocol_manager`        | Protocol listing and search  | API Gateway |
| `bedrock_criteria_parser` | Parse protocol criteria      | API Gateway |
| `fhir_search`             | Eligibility evaluation       | API Gateway |
| `match_manager`           | Match CRUD and workflow      | API Gateway |
| `lambda_authorizer`       | JWT validation and RBAC      | API Gateway |

### DynamoDB Tables

| Table                  | Purpose                  | Primary Key  |
| ---------------------- | ------------------------ | ------------ |
| `CriteriaCacheTable` | Parsed protocol criteria | `trial_id` |
| `MatchesTable`       | Patient-protocol matches | `match_id` |

---

## API Endpoints Used by CRC

### Patient APIs

```
GET /patients?name=John&gender=Male&age=45
POST /patients
GET /patients/{patientId}
```

### Protocol APIs

```
GET /protocols
POST /protocols/search
GET /protocols/{protocolId}
GET /protocols/{protocolId}/criteria
```

### Eligibility APIs

```
POST /check-criteria
{
  "patient_id": "Patient/123",
  "criteria": [
    {
      "category": "demographics",
      "attribute": "age",
      "operator": "greater_than",
      "value": 18
    }
  ]
}
```

### Match APIs

```
GET /matches?status=pending
POST /matches
{
  "patient_id": "Patient/123",
  "protocol_id": "NCT12345",
  "match_score": 85,
  "patient_name": "John Doe",
  "protocol_name": "Cancer Trial 2024",
  "criteria_results": [...]
}

PUT /matches/{matchId}
{
  "status": "pending_pi_approval",
  "notes": "Patient meets all inclusion criteria",
  "reviewed_by": "crc_test"
}
```

---

## User Workflows

### Workflow 1: Screen New Patient for Eligibility

```
1. CRC logs in with crc_test credentials
2. Navigate to "Eligibility Check" page
3. Select protocol from dropdown search
4. Enter patient data in comprehensive form:
   - Demographics (age, gender, birth date)
   - Conditions (cancer type, stage, other diagnoses)
   - Lab values (hemoglobin, platelets, creatinine, etc.)
   - Performance status (ECOG, Karnofsky)
   - Medications, allergies, prior treatments
   - Family history, encounters, diagnostic reports
5. Click "Check Eligibility"
6. View animated results with:
   - Circular progress indicator showing match score
   - Statistics dashboard (criteria met/not met/total)
   - Detailed criteria cards with patient values
7. Export PDF report (optional)
8. Click "Create Match for Review"
9. Navigate to "Patient Matches" to track status
```

### Workflow 2: Review and Approve Match

```
1. Navigate to "Patient Matches" page
2. Click "CRC Review" tab to see pending matches
3. Review match details:
   - Patient information
   - Protocol information
   - Match score
   - Criteria evaluation results
4. Add review notes (optional)
5. Click "Approve & Send to PI"
6. Match moves to "PI Approval" tab
7. CRC sees confirmation message:
   "Match approved by CRC and sent to PI for final approval"
8. PI will see match in their queue for final approval
```

### Workflow 3: Search Existing Patients

```
1. Navigate to "Patients" page
2. Use search filters:
   - Name
   - Gender (Male/Female/Other)
   - Age range
   - ECOG status
   - Conditions
3. Click "Search Patients"
4. View patient cards with key information
5. Click "Check Eligibility" on patient card
6. System pre-populates patient data
7. Select protocol and continue eligibility check
```

---

## Error Handling

### Common Scenarios

#### Invalid Protocol Criteria Format

**Error**: "Protocol has incomplete criteria format"
**Solution**: Protocol needs to be reprocessed through parse-criteria API
**CRC Action**: Contact Study Admin to reprocess protocol

#### Session Expired

**Error**: "Session expired. Please login again"
**Solution**: JWT token expired
**CRC Action**: Logout and login again

#### Insufficient Permissions

**Error**: "Only Principal Investigator (PI) can provide final approval"
**Solution**: CRC trying to approve pending_pi_approval match
**CRC Action**: Wait for PI to approve the match

#### HealthLake Connection Issues

**Error**: "Failed to connect to HealthLake"
**Solution**: Network or AWS service issue
**CRC Action**: Retry after a few moments, contact IT if persists

---

## Performance Metrics

### Eligibility Check Performance

- **Average Response Time**: 2-5 seconds
- **Depends On**:
  - Number of criteria (typically 5-20)
  - Complexity of FHIR queries
  - HealthLake query performance

### PDF Export Performance

- **Generation Time**: 1-2 seconds
- **File Size**: 50-200 KB (depending on criteria count)
- **Format**: Searchable PDF with embedded fonts

### Match Creation Performance

- **Average Response Time**: <1 second
- **DynamoDB Write**: ~100ms
- **Includes**: Validation, write, confirmation

---

## Security Features

### Data Protection

- All API calls use HTTPS (TLS 1.2+)
- JWT tokens with short expiration (1 hour)
- Automatic token refresh
- No sensitive data in localStorage

### Access Control

- Cognito group-based RBAC
- Lambda Authorizer validates every request
- Frontend enforces UI-level access control
- Backend enforces API-level access control

### Audit Trail

- All match updates tracked with:
  - Reviewer ID
  - Review timestamp
  - Status changes
  - Notes

---

## Known Limitations

### Current Limitations

1. **No Patient Edit Capability**: Patients cannot be edited after creation (read-only)
2. **Temporary Patient Creation**: Eligibility checks create temporary patients if no ID provided
3. **No Bulk Operations**: Cannot check multiple patients at once
4. **Protocol Upload UI Missing**: CRCs can call API but no frontend UI yet
5. **No Match History View**: Cannot see detailed match change history

### Planned Enhancements (Future Releases)

- Patient data editing
- Bulk eligibility checks
- Protocol upload interface
- Match audit log view
- Advanced search filters
- Real-time notifications

---

## Testing Guide

### End-to-End Test Scenario

**Prerequisite**:

- CRC test account: `crc_test`
- Protocol in system: `diabetes-trial-2024` or similar with proper criteria format

**Test Steps**:

1. **Login Test**

   ```
   Navigate to: http://localhost:5173/login
   Username: crc_test
   Password: [configured password]
   Expected: Successful login, redirect to dashboard
   ```
2. **Eligibility Check Test**

   ```
   Navigate to: /eligibility-check
   Select protocol: diabetes-trial-2024
   Enter patient data:
     - Age: 45
     - Gender: Male
     - ECOG Status: 1
   Click: "Check Eligibility"
   Expected: Animated results display with match score
   ```
3. **PDF Export Test**

   ```
   After eligibility check completes
   Click: "Export PDF Report"
   Expected: PDF downloads with proper formatting
   ```
4. **Match Creation Test**

   ```
   After eligibility check completes
   Click: "Create Match for Review"
   Expected: Success toast, match created in database
   ```
5. **Match Approval Test**

   ```
   Navigate to: /matches
   Click: "CRC Review" tab
   Find created match
   Click: "Approve & Send to PI"
   Add notes: "Patient is a good candidate"
   Confirm approval
   Expected: Match moves to "PI Approval" tab
   ```

---

## Troubleshooting

### Issue: "No protocols available"

**Cause**: No protocols uploaded or cached
**Solution**: Contact Study Admin to upload protocols via parse-criteria API

### Issue: "Criteria not cached for this protocol"

**Cause**: Protocol uploaded but criteria not parsed
**Solution**: Reprocess protocol through parse-criteria API

### Issue: Eligibility check returns error 'str' object has no attribute 'get'

**Cause**: Protocol has incomplete criteria format
**Solution**: Use properly parsed protocols (diabetes-trial-2024, cancer-trial-2024)

### Issue: Cannot see PI approval button

**Cause**: Expected behavior - CRCs cannot perform final approval
**Solution**: Login as PI user to approve pending_pi_approval matches

---

## Support & Resources

### Documentation

- Architecture: `/docs/ARCHITECTURE.md`
- API Reference: `/docs/API_DOCUMENTATION.md`
- Auth Implementation: `/docs/COGNITO_LOVABLE_INTEGRATION.md`
- Gap Analysis: `/docs/gap_analysis_v1.md`

### Contact

- Technical Issues: Study Admin
- Feature Requests: Product Team
- Training: Clinical Operations Team

---

## Changelog

### Version 1.0.0 (October 14, 2025)

- ✅ Initial production release
- ✅ Complete CRC persona implementation
- ✅ Modern eligibility results UI with animations
- ✅ PDF export functionality
- ✅ 2-level approval workflow with role-based access control
- ✅ Integration with AWS Cognito authentication
- ✅ Support for 11 FHIR resource types
- ✅ Real-time patient search
- ✅ Protocol discovery and search
- ✅ Comprehensive match management

---

**Document Maintained By**: Development Team
**Last Review Date**: October 14, 2025
**Next Review Date**: November 14, 2025
