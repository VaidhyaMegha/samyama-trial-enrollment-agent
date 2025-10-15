# Trial Enrollment System - Persona Documentation

This directory contains comprehensive documentation for all three personas in the Trial Enrollment system.

## Documentation Files

### 1. CRC (Clinical Research Coordinator) Persona

**File**: `CRC_PERSONA_IMPLEMENTATION.md`
**Status**: ✅ Production Ready
**Size**: 18 KB
**Contents**:

- Patient management and eligibility checking
- Match creation workflow
- Integration with AWS HealthLake
- FHIR resource handling

### 2. Study Admin Persona

**File**: `STUDY_ADMIN_IMPLEMENTATION.md`
**Status**: ✅ Production Ready
**Size**: 11 KB
**Contents**:

- Protocol upload and processing
- System monitoring and health metrics
- Audit trail and compliance
- Processing pipeline management

### 3. PI (Principal Investigator) Persona

**File**: `PI_PERSONA_COMPLETE.md`
**Status**: ✅ Production Ready
**Size**: 87 KB
**Contents**:

- Executive summary and architecture overview
- Dashboard and real-time metrics
- Trial portfolio management with enhanced UI
- Match review and 2-level approval workflow
- Patient roster and enrollment tracking
- CSV export and reporting
- Complete API documentation
- Frontend implementation details
- Data flow diagrams
- Deployment guide
- Security and compliance
- Testing and validation

## Quick Access Guide

### For Developers

- **Backend Implementation**: See backend sections in each persona doc
- **Frontend Implementation**: See frontend sections in each persona doc
- **API Documentation**: See API sections in each persona doc
- **Deployment**: See deployment sections in each persona doc

### For PIs (End Users)

- **Getting Started**: See "Quick Start Guide" section in `PI_PERSONA_COMPLETE.md`
- **User Features**: See "Core Features & Functionality" section
- **Troubleshooting**: See "Troubleshooting" appendix

### For Study Admins

- **System Management**: See `STUDY_ADMIN_IMPLEMENTATION.md`
- **Protocol Management**: See protocol sections
- **Monitoring**: See monitoring and health sections

### For CRCs

- **Patient Screening**: See `CRC_PERSONA_IMPLEMENTATION.md`
- **Eligibility Checks**: See eligibility sections
- **Match Creation**: See workflow sections

## Architecture Summary

```
┌─────────────────────────────────────┐
│         Frontend (React)            │
│  - CRC UI                           │
│  - StudyAdmin UI                    │
│  - PI UI                            │
└──────────────┬──────────────────────┘
               │ HTTPS
               ▼
┌─────────────────────────────────────┐
│      Amazon API Gateway             │
│  - JWT Authorization                │
│  - CORS Configuration               │
│  - Rate Limiting                    │
└──────────────┬──────────────────────┘
               │
    ┌──────────┴──────────┐
    │                     │
    ▼                     ▼
┌──────────┐      ┌──────────────┐
│ Lambda   │      │ Lambda       │
│ Functions│      │ Authorizer   │
└────┬─────┘      └──────────────┘
     │
     ├─→ patient_manager
     ├─→ protocol_manager
     ├─→ fhir_search
     ├─→ match_manager
     ├─→ admin_manager (with PI endpoints)
     ├─→ criteria_parser
     └─→ textract_processor
```

## Implementation Status

| Persona     | Backend     | Frontend    | Deployment  | Documentation |
| ----------- | ----------- | ----------- | ----------- | ------------- |
| CRC         | ✅ Complete | ✅ Complete | ✅ Deployed | ✅ Complete   |
| Study Admin | ✅ Complete | ✅ Complete | ✅ Deployed | ✅ Complete   |
| PI          | ✅ Complete | ✅ Complete | ✅ Deployed | ✅ Complete   |

## Test Credentials

**CRC User**:

- Username: `crc_test`
- Password: `TestCRC@2025!`

**Study Admin User**:

- Username: `admin_test`
- Password: `TestAdmin@2025!`

**PI User**:

- Username: `pi_test`
- Password: `TestPI@2025!`

## API Endpoints

**Base URL**: `https://gt7dlyqj78.execute-api.us-east-1.amazonaws.com/prod/`

**CRC Endpoints**:

- `GET /patients`
- `POST /patients`
- `GET /protocols`
- `POST /check-criteria`
- `POST /matches`

**Study Admin Endpoints**:

- `GET /admin/dashboard`
- `GET /admin/processing-status`
- `GET /admin/audit-trail`
- `POST /admin/reprocess/{id}`

**PI Endpoints**:

- `GET /pi/dashboard`
- `GET /pi/trials`
- `GET /pi/trials/{id}`
- `GET /pi/export/enrollment-summary`

## Quick Start

### For Development

1. **Backend Setup**:

   ```bash
   cd aws-trial-enrollment-agent/infrastructure
   cdk deploy
   ```
2. **Frontend Setup**:

   ```bash
   cd trial-compass-pro
   npm install
   npm run dev
   ```
3. **Access Application**:

   - Open `http://localhost:5173`
   - Login with test credentials
   - Start testing features

### For Production Deployment

See the "Deployment Guide" section in each persona documentation file.

## Support

**Documentation Issues**: Open GitHub issue
**Technical Support**: Contact development team
**Feature Requests**: Submit via GitHub

---

**Last Updated**: October 15, 2025
**Version**: 1.0.0
**Status**: ✅ Production Ready
