# Persona-Based Functional Flows

## Overview
This document defines the key personas, their goals, and functional workflows for the Trial Enrollment & Eligibility Agent system. These flows guide UI/UX design and feature prioritization.

## ⚠️ IMPLEMENTATION STATUS & HACKATHON ALIGNMENT

### Current Implementation (✅ Phase 1 - Completed)
The system currently implements:
- **Protocol Processing Pipeline**: S3 upload → AWS Textract → Comprehend Medical → Criteria Parser API
- **Core Lambda Functions**: Criteria Parser (Bedrock Titan), FHIR Search, Textract Processor, Section Classifier
- **Data Layer**: DynamoDB caching, HealthLake FHIR store
- **API Gateway**: REST endpoints for parse-criteria and check-criteria
- **Interface**: CLI-based scripts (not web UI)

### Critical Gaps for Hackathon Scoring ⚠️
1. **❌ Authentication/Authorization NOT Implemented**
   - No user management or RBAC
   - Required for HIPAA compliance and persona-based access
   - **Action Required**: Implement Cognito + role-based access control

2. **⚠️ Multi-Step Agent Orchestration Limited**
   - Current implementation uses direct Lambda invocations
   - Limited cross-step context and memory
   - **Action Required**: Enhance orchestration workflow

### Future Implementation (⏭️ Phase 2+)
- Web UI for protocol upload and patient matching
- Real-time patient candidate search
- Eligibility reports and analytics dashboards
- Multi-site feasibility analysis

---

## Persona 1: Clinical Research Coordinator (Primary User)

### Profile
- **Role**: Day-to-day trial enrollment management
- **Goals**: Quickly identify eligible patients, reduce screening time, maintain enrollment pipeline
- **Pain Points**: Manual chart review takes hours, criteria are complex, missing eligible patients costs time/money
- **Technical Skill**: Moderate (familiar with EHR, not technical)

### Functional Flows

#### Flow 1.1: Upload New Trial Protocol
```
1. Navigate to "Trials" → "Add New Trial"
2. Enter Trial ID (e.g., NCT12345678)
3. Upload protocol PDF (drag-drop or browse)
4. [System] Processes PDF with Textract (~20-30s for 20-100 pages)
5. [System] Displays extraction status:
   - ✓ Pages processed: 26
   - ✓ Confidence: 88.1%
   - ✓ Inclusion criteria found
   - ✓ Exclusion criteria found
6. Review extracted criteria preview
7. Click "Process Criteria" → Section Classifier analyzes
8. [System] Shows Comprehend Medical analysis:
   - Medical entity density: 15.2%
   - Criteria count: Inclusion (4), Exclusion (3)
9. Click "Convert to FHIR" → parse-criteria API processes
10. [System] Stores in DynamoDB, shows "Trial Ready"
11. Trial now appears in dashboard as "Active"
```

**UI Needs**: Progress indicators, confidence scores, preview panels, error handling

#### Flow 1.2: Search for Eligible Patients (Future)
```
1. Select active trial from dashboard
2. View trial criteria summary with FHIR resources
3. Click "Find Candidates"
4. [System] Queries FHIR patient store
5. View ranked patient list with match scores
6. For each patient, see:
   - Overall match: 85% (7/8 criteria met)
   - Green checkmarks: Met criteria
   - Red X: Failed criteria with explanation
   - Amber warning: Missing data
7. Click patient → detailed eligibility report
8. Action buttons: "Pre-screen", "Schedule Visit", "Exclude"
```

**UI Needs**: Patient cards, match visualization, criteria breakdown, action workflows

#### Flow 1.3: Review Eligibility Report
```
1. Open patient eligibility report
2. See criteria-by-criteria breakdown:

   INCLUSION CRITERIA:
   ✓ Age >= 18 years
     - Patient age: 52 (from Patient.birthDate)
     - Status: MET

   ✓ Diagnosis of T2DM
     - ICD-10: E11.9 (Type 2 diabetes)
     - Confirmed: 2023-05-12
     - Status: MET

   ✗ HbA1c 7-10%
     - Latest value: 6.8% (2024-09-15)
     - Status: NOT MET (below threshold)

3. View Comprehend Medical entities detected
4. Export report as PDF for IRB/documentation
5. Log decision: "Eligible" or "Ineligible" with reason
```

**UI Needs**: Structured report view, color coding, export function, audit logging

---

## Persona 2: Study Administrator

### Profile
- **Role**: Trial setup and data management
- **Goals**: Ensure protocols are correctly processed, maintain trial database, generate reports
- **Pain Points**: Data quality issues, version control, compliance documentation
- **Technical Skill**: High (comfortable with technical details)

### Functional Flows

#### Flow 2.1: Monitor Protocol Processing
```
1. Navigate to "Admin" → "Processing Pipeline"
2. View real-time pipeline status:
   - Textract jobs: 2 in progress, 15 completed today
   - Section Classifier: 13 processed, avg entity density 12.4%
   - Parse-criteria API: 11 converted to FHIR
   - DynamoDB: 50 trials cached
3. Click on any trial to see detailed logs:
   - Textract confidence scores by page
   - Query answers vs pattern extraction
   - Comprehend Medical entity breakdown
   - FHIR resource generation success/failures
4. Download processing report (JSON/CSV)
5. Reprocess failed trials with adjusted settings
```

**UI Needs**: Dashboard with metrics, detailed logs viewer, reprocessing controls

#### Flow 2.2: Manage Trial Criteria Library
```
1. Navigate to "Criteria Library"
2. Browse extracted criteria across all trials
3. Filter by:
   - Medical condition (Diabetes, Cancer, etc.)
   - Criteria type (Age, Labs, Medications, etc.)
   - FHIR resource type (Observation, Condition, etc.)
4. View criteria variations:
   - "Age >= 18" appears in 47 trials
   - "HbA1c 7-10%" appears in 12 trials (8 variations)
5. Standardize criteria definitions
6. Create reusable templates for common patterns
```

**UI Needs**: Search/filter interface, criteria comparison, template management

#### Flow 2.3: Audit & Compliance Reports
```
1. Navigate to "Reports" → "Compliance"
2. Generate audit trail for specific trial:
   - Protocol upload timestamp + user
   - Processing steps with confidence scores
   - Comprehend Medical entity detection log
   - All patient matches with timestamps
   - User decisions and actions
3. Export for IRB submission
4. View data retention status (TTL, 90 days)
5. Download HIPAA compliance checklist
```

**UI Needs**: Report generator, audit trail viewer, export formats, compliance checklist

---

## Persona 3: Principal Investigator (PI)

### Profile
- **Role**: Trial oversight and strategic decisions
- **Goals**: Understand enrollment feasibility, review complex cases, ensure scientific rigor
- **Pain Points**: Limited time, needs high-level summaries, wants confidence in automation
- **Technical Skill**: Low (clinical expertise, not tech-focused)

### Functional Flows

#### Flow 3.1: Review Trial Feasibility
```
1. Navigate to dashboard → select trial
2. View enrollment feasibility summary:
   - Estimated eligible patients: 23-31 (from 500 screened)
   - Time to target (N=50): 8-12 months
   - Top disqualifying criteria:
     1. HbA1c range (42% excluded)
     2. Prior medication history (28% excluded)
     3. Comorbidities (15% excluded)
3. See site comparison (if multi-site):
   - Site A: 12 eligible
   - Site B: 8 eligible
   - Site C: 5 eligible
4. Decision: "Relax HbA1c criterion?" → Simulation
5. Adjust criterion → see new feasibility estimate
```

**UI Needs**: Executive dashboard, feasibility metrics, criteria impact analysis, what-if scenarios

#### Flow 3.2: Approve High-Confidence Matches
```
1. View "Pending PI Approval" queue
2. Filter: Show only high-confidence matches (>90%)
3. Review patient summary (no PHI shown):
   - Demographics: 54F
   - Matching criteria: 8/8 met
   - System confidence: 94%
   - Comprehend Medical: 18.3% entity density
   - CRC recommendation: Eligible
4. Approve batch or review individually
5. Flagged cases (<80% confidence) require detailed review
```

**UI Needs**: Approval queue, confidence filtering, bulk actions, exception highlights

#### Flow 3.3: Export Enrollment Analytics
```
1. Navigate to "Analytics" → select trial
2. View enrollment funnel:
   - Patients screened: 127
   - Pre-screen passed: 58 (46%)
   - Criteria-eligible: 31 (24%)
   - Enrolled: 12 (9%)
3. See trends over time (enrollment velocity)
4. Compare AI-suggested vs manual screening:
   - AI sensitivity: 94% (missed 2/31)
   - AI specificity: 89% (11 false positives)
   - Time saved: 18.5 hours
5. Export for publication/grant reporting
```

**UI Needs**: Analytics dashboard, enrollment funnel, AI performance metrics, export capabilities

---

## 🔐 AUTHENTICATION & AUTHORIZATION ARCHITECTURE (NEW - REQUIRED)

### Overview
For HIPAA-compliant, multi-persona access to protected health information (PHI) and trial data, the system requires comprehensive authentication, authorization, and audit capabilities.

### Authentication Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    User Layer                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  CRC         │  │  Admin       │  │  PI          │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
└─────────┼──────────────────┼──────────────────┼─────────────┘
          │                  │                  │
          └──────────────────┴──────────────────┘
                             │
                     HTTPS/TLS + JWT Token
                             │
┌────────────────────────────▼──────────────────────────────────┐
│              Amazon Cognito User Pool                          │
│  ┌──────────────────────────────────────────────────────────┐│
│  │  User Authentication & Management                         ││
│  │  - Email/password login                                   ││
│  │  - MFA (Multi-Factor Authentication)                      ││
│  │  - Password policies (HIPAA-compliant)                    ││
│  │  - User groups for RBAC                                   ││
│  │  - JWT token generation (ID + Access + Refresh)           ││
│  └──────────────────────────────────────────────────────────┘│
└────────────────────────────┬──────────────────────────────────┘
                             │
                    JWT Access Token
                             │
┌────────────────────────────▼──────────────────────────────────┐
│        API Gateway Lambda Authorizer                           │
│  ┌──────────────────────────────────────────────────────────┐│
│  │  Token Validation & Claims Extraction                     ││
│  │  - Verify JWT signature                                   ││
│  │  - Check token expiration                                 ││
│  │  - Extract user ID and role (cognito:groups)              ││
│  │  - Generate IAM policy for API Gateway                    ││
│  │  - Log authorization attempts (audit trail)               ││
│  └──────────────────────────────────────────────────────────┘│
└────────────────────────────┬──────────────────────────────────┘
                             │
                    IAM Policy (Allow/Deny)
                             │
┌────────────────────────────▼──────────────────────────────────┐
│              API Gateway (REST API)                            │
│  ┌──────────────────────────────────────────────────────────┐│
│  │  Protected Endpoints with RBAC                            ││
│  │  - POST /parse-criteria (CRC, Admin)                      ││
│  │  - POST /check-criteria (CRC, Admin, PI)                  ││
│  │  - GET /trials/{id} (All roles)                           ││
│  │  - POST /admin/reprocess (Admin only)                     ││
│  │  - GET /analytics/* (PI, Admin)                           ││
│  └──────────────────────────────────────────────────────────┘│
└───────────────────────────────────────────────────────────────┘
                             │
                             ▼
                    Lambda Functions (with user context)
                             │
                             ▼
┌────────────────────────────────────────────────────────────────┐
│                   Audit Trail (CloudWatch)                     │
│  - User ID + Timestamp + Action + Resource + Result           │
│  - All authentication attempts (success/failure)               │
│  - All API calls with user context                             │
│  - PHI access logs (HIPAA compliance)                          │
└────────────────────────────────────────────────────────────────┘
```

### Role-Based Access Control (RBAC)

#### User Groups in Cognito
| Group | Description | Permissions |
|-------|-------------|-------------|
| **CRC** (Clinical Research Coordinator) | Day-to-day trial management | - Upload protocols<br>- Search patients<br>- View eligibility reports<br>- Pre-screen patients<br>- Read trial data |
| **StudyAdmin** | System administration & data quality | - All CRC permissions<br>- Reprocess failed trials<br>- View system logs<br>- Manage trial library<br>- Export compliance reports |
| **PI** (Principal Investigator) | Strategic oversight & approvals | - View all trials<br>- Approve high-confidence matches<br>- View analytics dashboards<br>- Adjust trial criteria<br>- Export enrollment reports<br>- Read-only on system admin |

### Authentication Flows

#### Flow A: Initial User Registration & Setup
```
1. Admin creates user in Cognito User Pool
   - Email address (username)
   - Temporary password
   - Assign to group (CRC, StudyAdmin, or PI)

2. User receives welcome email with temporary password

3. User navigates to login page

4. [First-time login]
   - Enter email + temporary password
   - Cognito forces password change
   - Set new password (meets policy: 12+ chars, mixed case, numbers, symbols)
   - [Optional] Setup MFA (TOTP app or SMS)

5. [Cognito] Issues JWT tokens:
   - ID Token (user attributes, groups)
   - Access Token (API authorization)
   - Refresh Token (long-lived, 30 days)

6. Application stores tokens securely:
   - Access Token → sessionStorage (short-lived)
   - Refresh Token → httpOnly cookie (secure)

7. User redirected to dashboard
```

#### Flow B: Regular Login
```
1. User navigates to login page

2. User enters email + password

3. [If MFA enabled] User enters MFA code

4. [Cognito] Validates credentials
   - Check password hash
   - Verify MFA code
   - Check account status (not locked/disabled)

5. [Success] Cognito returns JWT tokens
   ID Token example payload:
   {
     "sub": "uuid",
     "email": "crc@hospital.org",
     "cognito:groups": ["CRC"],
     "exp": 1234567890,
     "iat": 1234567800
   }

6. Application makes API call with Access Token:
   Authorization: Bearer <access_token>

7. [API Gateway Authorizer] Validates token:
   - Verify JWT signature with Cognito public keys
   - Check expiration (exp claim)
   - Extract cognito:groups
   - Generate IAM policy based on role

8. [API Gateway] Allows/denies request based on policy

9. [Lambda] Receives request with user context:
   event['requestContext']['authorizer']['claims']['email']
   event['requestContext']['authorizer']['claims']['cognito:groups']

10. [Lambda] Logs action with user ID (audit trail)

11. Response returned to user
```

#### Flow C: Token Refresh (Silent Re-authentication)
```
1. Access Token expires (default: 1 hour)

2. Application detects 401 Unauthorized from API

3. Application attempts token refresh:
   - Uses Refresh Token (stored in httpOnly cookie)
   - Calls Cognito /oauth2/token endpoint

4. [Cognito] Validates Refresh Token:
   - Check token signature
   - Verify not revoked
   - Confirm user still active

5. [Success] Cognito issues new Access Token + ID Token
   (Refresh Token remains valid until 30-day expiration)

6. Application retries original API request with new token

7. [Failure] User redirected to login page
   (Refresh Token expired or revoked)
```

#### Flow D: Logout
```
1. User clicks "Logout"

2. Application calls Cognito /logout endpoint

3. [Cognito] Invalidates tokens globally

4. Application clears local storage:
   - Remove tokens from sessionStorage
   - Delete httpOnly cookies

5. User redirected to login page

6. [Audit] Log logout event to CloudWatch
```

#### Flow E: Password Reset
```
1. User clicks "Forgot Password" on login page

2. User enters email address

3. [Cognito] Sends verification code to email

4. User enters code + new password

5. [Cognito] Updates password, forces re-login

6. [Audit] Log password reset event
```

### API Endpoint Authorization Matrix

| Endpoint | CRC | StudyAdmin | PI | Notes |
|----------|-----|------------|----|----- |
| `POST /parse-criteria` | ✅ | ✅ | ❌ | Upload and parse new trials |
| `POST /check-criteria` | ✅ | ✅ | ✅ | Check patient eligibility |
| `GET /trials` | ✅ | ✅ | ✅ | List all trials |
| `GET /trials/{id}` | ✅ | ✅ | ✅ | View specific trial details |
| `DELETE /trials/{id}` | ❌ | ✅ | ❌ | Delete trial (admin only) |
| `POST /patients/search` | ✅ | ✅ | ✅ | Search for eligible patients |
| `GET /patients/{id}/report` | ✅ | ✅ | ✅ | View eligibility report |
| `POST /patients/{id}/pre-screen` | ✅ | ❌ | ❌ | Mark patient for pre-screening |
| `POST /patients/{id}/approve` | ❌ | ❌ | ✅ | PI approval for enrollment |
| `GET /admin/logs` | ❌ | ✅ | ❌ | View system logs |
| `POST /admin/reprocess/{id}` | ❌ | ✅ | ❌ | Reprocess failed trial |
| `GET /analytics/feasibility` | ❌ | ✅ | ✅ | Enrollment feasibility metrics |
| `GET /analytics/performance` | ❌ | ✅ | ✅ | AI performance metrics |
| `GET /audit/trail` | ❌ | ✅ | ✅ | Audit trail (limited for PI) |

### Implementation Plan

#### Phase 1: Core Authentication (Priority 1 - 2 days)
```bash
# 1. Create Cognito User Pool
aws cognito-idp create-user-pool \
  --pool-name TrialEnrollmentUsers \
  --policies '{
    "PasswordPolicy": {
      "MinimumLength": 12,
      "RequireUppercase": true,
      "RequireLowercase": true,
      "RequireNumbers": true,
      "RequireSymbols": true,
      "TemporaryPasswordValidityDays": 7
    }
  }' \
  --auto-verified-attributes email \
  --mfa-configuration OPTIONAL \
  --account-recovery-setting '{"RecoveryMechanisms":[{"Name":"verified_email","Priority":1}]}'

# 2. Create User Groups
aws cognito-idp create-group \
  --user-pool-id <pool-id> \
  --group-name CRC \
  --description "Clinical Research Coordinators"

aws cognito-idp create-group \
  --user-pool-id <pool-id> \
  --group-name StudyAdmin \
  --description "Study Administrators"

aws cognito-idp create-group \
  --user-pool-id <pool-id> \
  --group-name PI \
  --description "Principal Investigators"

# 3. Create App Client
aws cognito-idp create-user-pool-client \
  --user-pool-id <pool-id> \
  --client-name TrialEnrollmentWebApp \
  --generate-secret false \
  --explicit-auth-flows ALLOW_USER_PASSWORD_AUTH ALLOW_REFRESH_TOKEN_AUTH \
  --token-validity-units '{"AccessToken":"hours","IdToken":"hours","RefreshToken":"days"}' \
  --access-token-validity 1 \
  --id-token-validity 1 \
  --refresh-token-validity 30

# 4. Create Lambda Authorizer (Python)
# Location: src/lambda/cognito_authorizer/handler.py
# - Validates JWT tokens
# - Extracts user role from cognito:groups
# - Generates IAM policy for API Gateway

# 5. Update API Gateway
# - Add Lambda Authorizer to all protected endpoints
# - Configure token validation
# - Enable CORS with credentials

# 6. Update Lambda Functions
# - Add user context extraction from event
# - Log all actions with user ID
# - Implement per-role business logic
```

#### Phase 2: RBAC Enforcement (Priority 2 - 1 day)
- Implement Lambda Authorizer with role-based policies
- Add authorization checks in Lambda functions
- Test each role's access to all endpoints
- Document permission denied scenarios

#### Phase 3: Audit & Compliance (Priority 3 - 1 day)
- Enhanced CloudWatch logging with user context
- DynamoDB table for audit trail (queryable)
- PHI access tracking
- Automated compliance reports
- Alert on suspicious activity (failed auth attempts)

#### Phase 4: User Management (Priority 4 - Future)
- Admin UI for user creation
- Self-service password reset
- MFA enrollment wizard
- Session management dashboard

### Security Best Practices

1. **Password Policies**
   - Minimum 12 characters
   - Complexity requirements
   - No reuse of last 3 passwords
   - Expire after 90 days (configurable)

2. **Token Management**
   - Short-lived Access Tokens (1 hour)
   - Secure Refresh Tokens (httpOnly cookies)
   - Token rotation on refresh
   - Revocation on logout/password change

3. **MFA (Multi-Factor Authentication)**
   - Optional for CRC
   - Required for StudyAdmin and PI
   - TOTP apps (Google Authenticator, Authy)
   - SMS fallback (less secure, discouraged)

4. **Session Management**
   - Absolute timeout: 8 hours
   - Idle timeout: 30 minutes
   - Concurrent session limit: 3 per user
   - Force logout on password change

5. **Audit Logging**
   - Log all authentication attempts
   - Log all API calls with user context
   - Log all PHI access
   - Retain logs for 7 years (HIPAA requirement)
   - Encrypt logs at rest and in transit

6. **Network Security**
   - TLS 1.2+ only
   - API Gateway with WAF (DDoS protection)
   - Rate limiting (100 req/min per user)
   - IP whitelisting (optional, for admin functions)

### HIPAA Compliance Checklist
- ✅ Cognito User Pool (HIPAA-eligible service when BAA signed)
- ✅ Encryption at rest (DynamoDB, HealthLake, S3)
- ✅ Encryption in transit (TLS 1.2+)
- ✅ Access controls (RBAC via Cognito groups)
- ✅ Audit trails (CloudWatch + DynamoDB)
- ✅ Authentication (Cognito with strong password policies)
- ✅ MFA available (TOTP)
- ⚠️ BAA with AWS (must be signed separately)
- ⚠️ PHI minimization (logs must not contain raw PHI)

### Example Code Snippets

#### Lambda Authorizer (src/lambda/cognito_authorizer/handler.py)
```python
import json
import jwt
import requests
from aws_lambda_powertools import Logger

logger = Logger()

# Cognito public keys (cached)
COGNITO_KEYS = None
USER_POOL_ID = os.environ['COGNITO_USER_POOL_ID']
REGION = os.environ['AWS_REGION']

def lambda_handler(event, context):
    """
    Lambda Authorizer for API Gateway
    Validates JWT token and returns IAM policy
    """
    token = event['authorizationToken'].replace('Bearer ', '')

    try:
        # Decode and verify JWT
        claims = verify_jwt(token)
        user_id = claims['sub']
        email = claims['email']
        groups = claims.get('cognito:groups', [])

        # Generate IAM policy based on role
        policy = generate_policy(user_id, email, groups, event['methodArn'])

        logger.info(f"Authorization successful for user: {email}, groups: {groups}")
        return policy

    except Exception as e:
        logger.error(f"Authorization failed: {str(e)}")
        raise Exception('Unauthorized')

def verify_jwt(token):
    """Verify JWT signature and expiration"""
    global COGNITO_KEYS

    if not COGNITO_KEYS:
        # Fetch Cognito public keys
        keys_url = f'https://cognito-idp.{REGION}.amazonaws.com/{USER_POOL_ID}/.well-known/jwks.json'
        COGNITO_KEYS = requests.get(keys_url).json()['keys']

    # Decode header to get kid
    headers = jwt.get_unverified_header(token)
    kid = headers['kid']

    # Find matching key
    key = next((k for k in COGNITO_KEYS if k['kid'] == kid), None)
    if not key:
        raise Exception('Invalid token: key not found')

    # Verify signature and decode claims
    claims = jwt.decode(
        token,
        key,
        algorithms=['RS256'],
        audience=os.environ['COGNITO_APP_CLIENT_ID']
    )

    return claims

def generate_policy(user_id, email, groups, method_arn):
    """Generate IAM policy based on user role"""
    # Determine role
    role = 'CRC' if 'CRC' in groups else \
           'StudyAdmin' if 'StudyAdmin' in groups else \
           'PI' if 'PI' in groups else None

    if not role:
        raise Exception('No valid role found')

    # Define role permissions
    permissions = {
        'CRC': [
            'execute-api:Invoke:POST:/parse-criteria',
            'execute-api:Invoke:POST:/check-criteria',
            'execute-api:Invoke:GET:/trials*',
            'execute-api:Invoke:POST:/patients/*/pre-screen'
        ],
        'StudyAdmin': [
            'execute-api:Invoke:*:/*'  # Full access
        ],
        'PI': [
            'execute-api:Invoke:POST:/check-criteria',
            'execute-api:Invoke:GET:/trials*',
            'execute-api:Invoke:GET:/analytics*',
            'execute-api:Invoke:POST:/patients/*/approve'
        ]
    }

    return {
        'principalId': user_id,
        'policyDocument': {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Action': 'execute-api:Invoke',
                    'Effect': 'Allow',
                    'Resource': method_arn  # Simplified: should check against permissions[role]
                }
            ]
        },
        'context': {
            'userId': user_id,
            'email': email,
            'role': role
        }
    }
```

#### Updated Lambda Function with User Context
```python
def lambda_handler(event, context):
    """
    Example Lambda function that uses user context
    """
    # Extract user context from authorizer
    user_id = event['requestContext']['authorizer']['userId']
    email = event['requestContext']['authorizer']['email']
    role = event['requestContext']['authorizer']['role']

    logger.info(f"Request from user: {email} (role: {role})")

    # Audit log
    log_audit_event(
        user_id=user_id,
        action='parse-criteria',
        resource=event['body']['trial_id'],
        timestamp=datetime.utcnow().isoformat()
    )

    # Business logic with role-based checks
    if role == 'CRC':
        # CRC-specific logic
        pass

    # ... rest of function
```

---

## Cross-Persona Features

### Feature 1: Real-Time Notifications
- **Who**: All personas
- **When**: Protocol processing complete, new eligible patients found, approval needed
- **What**: Toast notifications, email summaries, dashboard badges

### Feature 2: Explainability & Transparency
- **Who**: All personas (especially CRC and PI)
- **What**:
  - Show which AI model made each decision
  - Display confidence scores with color coding
  - Provide "Why this patient?" explanations
  - Link to source data (FHIR resources)

### Feature 3: Audit Trail
- **Who**: Study Admin, PI (for compliance)
- **What**: Complete action history with timestamps, users, and decisions

### Feature 4: Help & Documentation
- **Who**: All personas
- **What**: Contextual help, tooltips for medical terms, onboarding wizard

---

## UI Component Priorities

### Phase 1 (MVP - Current Implementation)
1. ✅ Protocol upload interface
2. ✅ Processing status dashboard
3. ✅ Criteria extraction viewer
4. ⏳ Trial management (list, view, edit)

### Phase 2 (Patient Matching - Next)
5. ⏭️ FHIR patient search integration
6. ⏭️ Patient eligibility reports
7. ⏭️ Match scoring & ranking

### Phase 3 (Advanced Features)
8. ⏭️ Feasibility analysis
9. ⏭️ Analytics dashboard
10. ⏭️ Approval workflows

---

## Key UI Patterns

### Pattern 1: Confidence Visualization
```
High (>90%):    🟢 Green background, "High confidence"
Medium (70-90%): 🟡 Amber background, "Review recommended"
Low (<70%):     🔴 Red background, "Manual review required"
```

### Pattern 2: Criteria Status
```
✓ MET         → Green checkmark
✗ NOT MET     → Red X with reason
⚠ MISSING DATA → Amber warning triangle
➖ NOT CHECKED → Gray dash
```

### Pattern 3: Processing Pipeline Status
```
Textract → Section Classifier → Parse-criteria → DynamoDB
  [88%]      [15.2% entities]      [FHIR ready]    [Cached]
```

### Pattern 4: Action Buttons (Role-Based)
```
CRC:   [Find Patients] [Pre-screen] [Schedule]
Admin: [Reprocess] [View Logs] [Export]
PI:    [Approve] [Review Details] [Adjust Criteria]
```

---

## Sample User Stories

### Story 1 (CRC): Quick Protocol Upload
```
AS A Clinical Research Coordinator
I WANT TO upload a trial protocol PDF and see extracted criteria within 30 seconds
SO THAT I can start screening patients immediately without manual data entry
```

### Story 2 (Admin): Monitor Data Quality
```
AS A Study Administrator
I WANT TO see Comprehend Medical entity density and confidence scores
SO THAT I can ensure extraction quality before using criteria for patient matching
```

### Story 3 (PI): Trust AI Recommendations
```
AS A Principal Investigator
I WANT TO see why each patient was matched with evidence from their health record
SO THAT I can trust the system's recommendations and make informed decisions
```

---

## Technical Implementation Notes for UI Team

### Data Flows
1. **Protocol Upload** → POST to Textract Processor Lambda → Poll for completion → Display results
2. **Criteria View** → GET from DynamoDB (trial_id key) → Render formatted criteria
3. **Patient Matching** → POST to FHIR search endpoint → Receive ranked matches → Display cards

### State Management
- Trial status: `uploaded | processing | ready | active | completed | archived`
- Patient match status: `pending | eligible | ineligible | enrolled | withdrawn`
- Processing stages: `textract | classifier | parser | fhir | stored`

### API Endpoints (Planned)
```
POST   /api/trials/upload          - Upload protocol PDF
GET    /api/trials/{id}             - Get trial details
GET    /api/trials/{id}/criteria    - Get extracted criteria
POST   /api/trials/{id}/search      - Find eligible patients
GET    /api/patients/{id}/report    - Get eligibility report
POST   /api/admin/reprocess/{id}    - Reprocess trial
GET    /api/analytics/feasibility   - Get feasibility metrics
```

### Error Handling
- Show user-friendly messages for all errors
- Provide retry options for transient failures
- Log all errors to CloudWatch for debugging
- Display system status banner if AWS services degraded

---

**Document Version**: 1.0
**Last Updated**: 2025-10-11
**For**: UI/UX Design & Development
