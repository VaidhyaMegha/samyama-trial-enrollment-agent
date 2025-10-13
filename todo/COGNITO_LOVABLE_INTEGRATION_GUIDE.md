# AWS Cognito + Lovable Frontend Integration Guide

## 🎯 Overview

This guide provides **step-by-step implementation instructions** for integrating AWS Cognito authentication with a Lovable-generated frontend deployed on AWS Amplify.

**For architecture details, persona flows, and requirements**, see: `auth-persona-implementation.md`

### What is Lovable?
Lovable (formerly GPT Engineer) is an AI-powered tool that generates full-stack React/TypeScript web applications from natural language prompts.

### Deployment Flow

```
Lovable (Generate Code)
  → Export to GitHub
    → Connect AWS Amplify Hosting
      → Automatic CI/CD Deployment
        → Live App with Cognito Auth
```

---

## 💰 Complete Cost Analysis

### Monthly Cost Breakdown (100 Active Users)

| Service | Free Tier | After Free Tier | Estimated Cost (100 users) |
|---------|-----------|-----------------|---------------------------|
| **AWS Cognito User Pool** | First 50,000 MAUs FREE | $0.0055/MAU | **$0** (under free tier) |
| **Lambda Authorizer** | 1M requests/month FREE | $0.20/1M requests | **$0** (est. 10K auth checks) |
| **API Gateway** | 1M calls/month FREE (12 months) | $3.50/1M requests | **$0.18** (50K API calls) |
| **Lambda Functions** | 1M requests + 400K GB-sec FREE | $0.20/1M requests + compute | **$2-5** (depends on usage) |
| **DynamoDB** | 25 GB storage + 25 RCU/WCU FREE | $0.25/GB + $0.25/WCU | **$0-2** (small dataset) |
| **AWS HealthLake (FHIR)** | No free tier | $0.65/GB stored + $0.75/GB ingested | **$10-30** (depends on patient data) |
| **S3 (Protocol PDFs)** | 5 GB storage + 20K GET requests FREE | $0.023/GB + $0.0004/1K requests | **$0** (under free tier) |
| **AWS Textract** | 1,000 pages/month FREE | $1.50/1K pages (text) + $15/1K (forms/tables) | **$5-20** (depends on uploads) |
| **AWS Comprehend Medical** | No free tier | $0.01/100 characters (entity detection) | **$10-25** (depends on protocol size) |
| **AWS Amplify Hosting** | 1,000 build minutes + 15 GB served FREE | $0.01/build min + $0.15/GB | **$0-10** (typical frontend) |
| **CloudWatch Logs** | 5 GB ingestion + 5 GB storage FREE | $0.50/GB ingested + $0.03/GB stored | **$0-2** (under free tier) |
| **Data Transfer (Outbound)** | 100 GB/month FREE | $0.09/GB | **$0** (under free tier) |

### Total Estimated Monthly Cost

| Scenario | Cost Range | Notes |
|----------|------------|-------|
| **Development (Light Usage)** | **$5-15/month** | Mostly free tier, minimal protocol processing |
| **Production (100 users, 50 protocols/month)** | **$30-75/month** | HealthLake + Textract + Comprehend Medical dominate |
| **High Volume (500 users, 200 protocols/month)** | **$150-300/month** | Scale up Textract, Comprehend, HealthLake storage |

### Key Cost Drivers (Ranked)

1. **AWS HealthLake** - $10-30/month (FHIR patient data storage)
2. **AWS Comprehend Medical** - $10-25/month (NLP entity extraction)
3. **AWS Textract** - $5-20/month (PDF processing)
4. **AWS Amplify Hosting** - $0-10/month (frontend CI/CD + CDN)
5. **Lambda + API Gateway** - $2-8/month (backend API calls)
6. **Everything Else** - $0-5/month (mostly free tier)

### Cost Optimization Tips

1. **HealthLake Alternative**: Consider storing FHIR resources in DynamoDB instead (save $10-20/month)
2. **Textract Optimization**: Cache results in DynamoDB to avoid reprocessing (save 50%)
3. **Comprehend Medical**: Batch API calls and only process inclusion/exclusion sections (save 30-40%)
4. **Amplify Hosting**: Use manual deploys instead of auto-deploy to save build minutes
5. **CloudWatch Logs**: Set 7-day retention instead of indefinite (free)

### Cost Comparison: IAM Users vs Cognito

| Approach | Cost | Security | Scalability |
|----------|------|----------|-------------|
| **IAM Users (WRONG)** | $0 (but high operational cost) | ❌ Not HIPAA-compliant for app users | ❌ Manual user management |
| **Cognito Users (CORRECT)** | $0 (first 50K MAUs) | ✅ HIPAA-eligible, MFA, audit trails | ✅ Automatic, API-driven |

**Key Point**: Cognito users ≠ IAM users. Cognito is for application users (free tier covers most use cases), while IAM is for AWS infrastructure permissions (one Lambda role, not per-user).

---

## 📋 Implementation Phases

### Phase 1: AWS Cognito Setup (Backend) - 2 days
### Phase 2: Lambda Authorizer Implementation - 1 day
### Phase 3: Lovable Frontend Generation - 2 days
### Phase 4: AWS Amplify Deployment - 1 day
### Phase 5: Testing & HIPAA Compliance - 1 day

**Total: 7 days**

---

## 🔧 Phase 1: AWS Cognito Setup

### Step 1.1: Create Cognito Setup Script

Create `infrastructure/cognito_setup.py`:

```python
import boto3
import json
import os

cognito = boto3.client('cognito-idp', region_name='us-east-1')

def create_user_pool():
    """Create Cognito User Pool with HIPAA-compliant settings"""

    response = cognito.create_user_pool(
        PoolName='TrialEnrollmentUserPool',
        Policies={
            'PasswordPolicy': {
                'MinimumLength': 12,
                'RequireUppercase': True,
                'RequireLowercase': True,
                'RequireNumbers': True,
                'RequireSymbols': True,
                'TemporaryPasswordValidityDays': 7
            }
        },
        AutoVerifiedAttributes=['email'],
        MfaConfiguration='OPTIONAL',
        AccountRecoverySetting={
            'RecoveryMechanisms': [
                {'Name': 'verified_email', 'Priority': 1}
            ]
        },
        Schema=[
            {
                'Name': 'email',
                'AttributeDataType': 'String',
                'Required': True,
                'Mutable': False
            },
            {
                'Name': 'name',
                'AttributeDataType': 'String',
                'Required': True,
                'Mutable': True
            },
            {
                'Name': 'custom:role',
                'AttributeDataType': 'String',
                'Mutable': True,
                'DeveloperOnlyAttribute': False
            }
        ],
        UserPoolTags={
            'Environment': 'production',
            'Project': 'TrialEnrollment',
            'HIPAA': 'true'
        }
    )

    user_pool_id = response['UserPool']['Id']
    print(f"✅ User Pool created: {user_pool_id}")
    return user_pool_id


def create_user_groups(user_pool_id):
    """Create role-based user groups"""

    groups = [
        {
            'name': 'CRC',
            'description': 'Clinical Research Coordinators - Day-to-day trial management',
            'precedence': 3
        },
        {
            'name': 'StudyAdmin',
            'description': 'Study Administrators - System administration and data quality',
            'precedence': 1  # Highest precedence
        },
        {
            'name': 'PI',
            'description': 'Principal Investigators - Strategic oversight and approvals',
            'precedence': 2
        }
    ]

    for group in groups:
        cognito.create_group(
            GroupName=group['name'],
            UserPoolId=user_pool_id,
            Description=group['description'],
            Precedence=group['precedence']
        )
        print(f"✅ Group created: {group['name']}")


def create_user_pool_client(user_pool_id):
    """Create app client for Lovable frontend"""

    response = cognito.create_user_pool_client(
        UserPoolId=user_pool_id,
        ClientName='TrialEnrollmentWebApp',
        GenerateSecret=False,  # Public client (frontend)
        RefreshTokenValidity=30,  # 30 days
        AccessTokenValidity=1,    # 1 hour
        IdTokenValidity=1,        # 1 hour
        TokenValidityUnits={
            'AccessToken': 'hours',
            'IdToken': 'hours',
            'RefreshToken': 'days'
        },
        ReadAttributes=['email', 'name', 'custom:role'],
        WriteAttributes=['name'],
        ExplicitAuthFlows=[
            'ALLOW_USER_PASSWORD_AUTH',
            'ALLOW_REFRESH_TOKEN_AUTH',
            'ALLOW_USER_SRP_AUTH'  # Secure Remote Password
        ],
        PreventUserExistenceErrors='ENABLED',
        EnableTokenRevocation=True,
        EnablePropagateAdditionalUserContextData=False
    )

    client_id = response['UserPoolClient']['ClientId']
    print(f"✅ App Client created: {client_id}")
    return client_id


if __name__ == '__main__':
    print("🚀 Setting up AWS Cognito for Trial Enrollment Agent...\n")

    # Create User Pool
    user_pool_id = create_user_pool()

    # Create User Groups
    create_user_groups(user_pool_id)

    # Create App Client
    client_id = create_user_pool_client(user_pool_id)

    # Save configuration
    config = {
        'userPoolId': user_pool_id,
        'userPoolClientId': client_id,
        'region': 'us-east-1'
    }

    with open('infrastructure/cognito-config.json', 'w') as f:
        json.dump(config, f, indent=2)

    print("\n✅ Cognito setup complete!")
    print(f"📝 Configuration saved to: infrastructure/cognito-config.json")
    print("\n🔑 Add these to your .env file:")
    print(f"COGNITO_USER_POOL_ID={user_pool_id}")
    print(f"COGNITO_CLIENT_ID={client_id}")
    print(f"COGNITO_REGION=us-east-1")
```

**Run the setup:**
```bash
cd infrastructure
python3 cognito_setup.py
```

### Step 1.2: Create Test Users Script

Create `infrastructure/create_test_users.py`:

```python
import boto3
import os

cognito = boto3.client('cognito-idp', region_name='us-east-1')

USER_POOL_ID = os.environ['COGNITO_USER_POOL_ID']

def create_user(email, name, role, temp_password='TempPass123!'):
    """Create a test user and add to role group"""

    try:
        # Create user
        response = cognito.admin_create_user(
            UserPoolId=USER_POOL_ID,
            Username=email,
            UserAttributes=[
                {'Name': 'email', 'Value': email},
                {'Name': 'email_verified', 'Value': 'true'},
                {'Name': 'name', 'Value': name},
                {'Name': 'custom:role', 'Value': role}
            ],
            TemporaryPassword=temp_password,
            MessageAction='SUPPRESS'  # Don't send email (for testing)
        )

        print(f"✅ User created: {email}")

        # Add user to group
        cognito.admin_add_user_to_group(
            UserPoolId=USER_POOL_ID,
            Username=email,
            GroupName=role
        )

        print(f"   Added to group: {role}")

    except cognito.exceptions.UsernameExistsException:
        print(f"⚠️  User already exists: {email}")


if __name__ == '__main__':
    print("👥 Creating test users...\n")

    # Create test users for each role
    create_user(
        email='crc@example.com',
        name='Jane Coordinator',
        role='CRC'
    )

    create_user(
        email='admin@example.com',
        name='John Administrator',
        role='StudyAdmin'
    )

    create_user(
        email='pi@example.com',
        name='Dr. Sarah Investigator',
        role='PI'
    )

    print("\n✅ Test users created!")
    print("\n🔑 Login credentials:")
    print("   Email: crc@example.com / admin@example.com / pi@example.com")
    print("   Temp Password: TempPass123!")
    print("   (Users must change password on first login)")
```

---

## 🔒 Phase 2: Lambda Authorizer Implementation

### Step 2.1: Create Lambda Authorizer Function

Create `src/lambda/cognito_authorizer/handler.py`:

```python
import json
import os
import jwt
import requests
from functools import lru_cache
from aws_lambda_powertools import Logger
from typing import Dict, Any

logger = Logger()

USER_POOL_ID = os.environ['COGNITO_USER_POOL_ID']
REGION = os.environ.get('AWS_REGION', 'us-east-1')
CLIENT_ID = os.environ['COGNITO_CLIENT_ID']


@lru_cache(maxsize=1)
def get_cognito_keys():
    """Fetch and cache Cognito public keys for JWT verification"""
    keys_url = f'https://cognito-idp.{REGION}.amazonaws.com/{USER_POOL_ID}/.well-known/jwks.json'
    response = requests.get(keys_url)
    return response.json()['keys']


def verify_jwt_token(token: str) -> Dict[str, Any]:
    """Verify JWT token signature and return claims"""

    try:
        # Get unverified header to extract key ID
        headers = jwt.get_unverified_header(token)
        kid = headers['kid']

        # Find the matching public key
        keys = get_cognito_keys()
        key = next((k for k in keys if k['kid'] == kid), None)

        if not key:
            raise Exception('Public key not found')

        # Convert JWK to PEM format
        from jwt.algorithms import RSAAlgorithm
        public_key = RSAAlgorithm.from_jwk(json.dumps(key))

        # Verify and decode token
        claims = jwt.decode(
            token,
            public_key,
            algorithms=['RS256'],
            audience=CLIENT_ID,
            options={'verify_exp': True}
        )

        return claims

    except jwt.ExpiredSignatureError:
        logger.error("Token expired")
        raise Exception('Token expired')
    except jwt.InvalidTokenError as e:
        logger.error(f"Invalid token: {str(e)}")
        raise Exception('Invalid token')


def get_user_role(claims: Dict[str, Any]) -> str:
    """Extract user role from Cognito groups"""
    groups = claims.get('cognito:groups', [])

    # Return highest precedence role
    if 'StudyAdmin' in groups:
        return 'StudyAdmin'
    elif 'PI' in groups:
        return 'PI'
    elif 'CRC' in groups:
        return 'CRC'
    else:
        return 'Unknown'


def generate_iam_policy(user_id: str, email: str, role: str, method_arn: str) -> Dict[str, Any]:
    """Generate IAM policy based on user role"""

    # Extract API Gateway info from method ARN
    arn_parts = method_arn.split(':')
    api_gateway_arn = ':'.join(arn_parts[:5])

    # Define role-based permissions (matches auth-persona-implementation.md)
    role_permissions = {
        'CRC': {
            'allow': [
                f"{api_gateway_arn}/*/POST/parse-criteria",
                f"{api_gateway_arn}/*/POST/check-criteria",
                f"{api_gateway_arn}/*/GET/trials",
                f"{api_gateway_arn}/*/GET/trials/*",
                f"{api_gateway_arn}/*/POST/patients/*/pre-screen"
            ]
        },
        'StudyAdmin': {
            'allow': [
                f"{api_gateway_arn}/*/*"  # Full access
            ]
        },
        'PI': {
            'allow': [
                f"{api_gateway_arn}/*/POST/check-criteria",
                f"{api_gateway_arn}/*/GET/trials",
                f"{api_gateway_arn}/*/GET/trials/*",
                f"{api_gateway_arn}/*/GET/analytics/*",
                f"{api_gateway_arn}/*/POST/patients/*/approve"
            ]
        }
    }

    permissions = role_permissions.get(role, {'allow': []})

    policy = {
        'principalId': user_id,
        'policyDocument': {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Action': 'execute-api:Invoke',
                    'Effect': 'Allow',
                    'Resource': permissions['allow']
                }
            ]
        },
        'context': {
            'userId': user_id,
            'email': email,
            'role': role
        }
    }

    return policy


def lambda_handler(event, context):
    """
    Lambda Authorizer for API Gateway
    Validates Cognito JWT tokens and returns IAM policy
    """

    logger.info("Authorization request received")

    try:
        # Extract token from Authorization header
        token = event['authorizationToken']
        if token.startswith('Bearer '):
            token = token[7:]

        # Verify JWT token
        claims = verify_jwt_token(token)

        # Extract user information
        user_id = claims['sub']
        email = claims['email']
        role = get_user_role(claims)

        logger.info(f"Authorization successful - User: {email}, Role: {role}")

        # Generate IAM policy
        policy = generate_iam_policy(user_id, email, role, event['methodArn'])

        return policy

    except Exception as e:
        logger.error(f"Authorization failed: {str(e)}")
        raise Exception('Unauthorized')
```

Create `src/lambda/cognito_authorizer/requirements.txt`:
```
PyJWT==2.8.0
cryptography==41.0.7
requests==2.31.0
aws-lambda-powertools==2.31.0
```

### Step 2.2: Update SAM Template

Add to `template.yaml`:

```yaml
CognitoAuthorizerFunction:
  Type: AWS::Serverless::Function
  Properties:
    CodeUri: src/lambda/cognito_authorizer/
    Handler: handler.lambda_handler
    Runtime: python3.11
    Timeout: 10
    Environment:
      Variables:
        COGNITO_USER_POOL_ID: !Ref CognitoUserPoolId
        COGNITO_CLIENT_ID: !Ref CognitoClientId
    Layers:
      - !Ref CommonLayer

# Add Parameters
Parameters:
  CognitoUserPoolId:
    Type: String
    Description: Cognito User Pool ID

  CognitoClientId:
    Type: String
    Description: Cognito App Client ID

# Update API Gateway
TrialEnrollmentApi:
  Type: AWS::Serverless::Api
  Properties:
    StageName: prod
    Cors:
      AllowOrigin: "'*'"  # Update with your Amplify domain later
      AllowHeaders: "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'"
      AllowMethods: "'GET,POST,PUT,DELETE,OPTIONS'"
      AllowCredentials: true
    Auth:
      DefaultAuthorizer: CognitoAuthorizer
      Authorizers:
        CognitoAuthorizer:
          FunctionArn: !GetAtt CognitoAuthorizerFunction.Arn
          FunctionPayloadType: TOKEN
          Identity:
            Header: Authorization
            ValidationExpression: "Bearer .*"
```

### Step 2.3: Deploy Backend

```bash
# Set environment variables
export COGNITO_USER_POOL_ID=<from step 1.1>
export COGNITO_CLIENT_ID=<from step 1.1>

# Build and deploy
sam build
sam deploy --guided \
  --parameter-overrides \
    CognitoUserPoolId=$COGNITO_USER_POOL_ID \
    CognitoClientId=$COGNITO_CLIENT_ID

# Save API Gateway URL
export API_GATEWAY_URL=<output from deploy>
```

---

## 🎨 Phase 3: Lovable Frontend Generation

### Step 3.1: Comprehensive Lovable Prompt

Use this prompt in Lovable:

```
Create a React + TypeScript web application for a Clinical Trial Enrollment System with AWS Cognito authentication.

AUTHENTICATION REQUIREMENTS:
- Integrate AWS Amplify v6 for Cognito authentication
- Login page with email/password (modern glassmorphism design)
- Role-based access control (3 roles: CRC, StudyAdmin, PI)
- Protected routes with authentication guards
- MFA support
- Password reset flow
- Logout functionality with confirmation

UI STRUCTURE:

1. Public Pages:
   - Login page (glassmorphism card, centered layout)
   - Password reset page
   - 404 error page

2. Shared Layout (All Roles):
   - Top navigation bar with:
     * App logo/title
     * User info dropdown (name, email, role badge)
     * Logout button
   - Side navigation (role-based menu items)
   - Main content area with breadcrumbs

3. CRC Dashboard Pages:
   - Trials List (table with search, filters)
   - Upload Protocol (drag-drop PDF upload with progress)
   - Active Trials (cards with status badges)
   - Patient Search (FHIR query interface)
   - Eligibility Reports (criteria breakdown with color coding)

4. Study Admin Dashboard Pages:
   - All CRC pages PLUS:
   - System Monitoring (metrics cards, real-time stats)
   - Processing Pipeline Status (step progress indicators)
   - User Management (CRUD table for users)
   - Audit Logs (searchable log viewer with filters)

5. PI Dashboard Pages:
   - View-only Trials List
   - Enrollment Analytics (charts: bar, line, pie)
   - Approval Queue (patient cards with approve/reject actions)
   - Feasibility Analysis (what-if scenario simulator)

DESIGN REQUIREMENTS:
- Use Tailwind CSS + shadcn/ui components
- Responsive design (mobile-first, tablet, desktop)
- Dark mode toggle
- Loading states (skeletons, spinners)
- Error boundaries with user-friendly messages
- Toast notifications (react-toastify)
- Confidence score visualization:
  * >90%: Green badge with "High confidence"
  * 70-90%: Amber badge with "Review recommended"
  * <70%: Red badge with "Manual review required"
- Data tables with:
  * Sorting (click column headers)
  * Filtering (search bar + dropdown filters)
  * Pagination (10/25/50 per page)
  * Export buttons (CSV, PDF)

API INTEGRATION:
- Axios for HTTP requests
- JWT token in Authorization header: "Bearer {token}"
- Base URL from environment variable
- Endpoints:
  * POST /parse-criteria (body: {trial_id, criteria_text})
  * POST /check-criteria (body: {trial_id, patient_id})
  * GET /trials (returns array of trials)
  * GET /trials/{id} (returns single trial with criteria)
  * GET /analytics/feasibility (returns enrollment metrics)

COGNITO CONFIGURATION:
- Use AWS Amplify v6 Auth API (fetchAuthSession, signIn, signOut, getCurrentUser)
- Environment variables:
  * VITE_COGNITO_USER_POOL_ID
  * VITE_COGNITO_CLIENT_ID
  * VITE_COGNITO_REGION
  * VITE_API_BASE_URL

ADDITIONAL FEATURES:
- Form validation with react-hook-form + zod
- Date formatting with date-fns
- Charts with recharts or Chart.js
- Icons from lucide-react
- Animations with framer-motion (subtle, not excessive)

Use TypeScript with strict mode. Include proper error handling and loading states for all async operations.
```

### Step 3.2: Iterative Refinement Prompts

After initial generation, refine with these prompts:

**Prompt 2 (Authentication):**
```
Implement the authentication hook using AWS Amplify v6. Create src/hooks/useAuth.ts that:
- Checks auth status on mount
- Provides login(email, password) function
- Provides logout() function
- Returns user object with {userId, email, role, groups}
- Handles token refresh automatically
- Throws errors with user-friendly messages
```

**Prompt 3 (Protected Routes):**
```
Create a ProtectedRoute component that:
- Shows loading spinner while checking auth
- Redirects to /login if not authenticated
- Shows "Access Denied" page if user role not in allowedRoles prop
- Passes children if authorized
Use it to wrap all dashboard routes.
```

**Prompt 4 (API Client):**
```
Create src/services/api.ts with axios instance that:
- Uses VITE_API_BASE_URL from env
- Adds JWT token to Authorization header (from fetchAuthSession)
- Handles 401 errors by redirecting to login
- Shows toast notification on network errors
Export typed API methods for each endpoint.
```

**Prompt 5 (Role-Based Navigation):**
```
Update the side navigation to show different menu items based on user role:
- CRC: Trials, Upload, Patients, Reports
- StudyAdmin: All CRC items + Admin, Monitoring, Audit, Users
- PI: Trials (read-only), Analytics, Approvals, Feasibility
Add active state highlighting and icons for each menu item.
```

### Step 3.3: Export Code from Lovable

1. Click "Export" in Lovable
2. Download ZIP file
3. Extract to local directory
4. Initialize Git repository

```bash
cd ~/lovable-trial-enrollment-app
git init
git add .
git commit -m "Initial Lovable export"
```

---

## 🚀 Phase 4: AWS Amplify Deployment

### Step 4.1: Push to GitHub

```bash
# Create GitHub repository (via GitHub UI or CLI)
gh repo create trial-enrollment-frontend --public --source=. --remote=origin

# Push code
git branch -M main
git push -u origin main
```

### Step 4.2: Connect AWS Amplify Hosting

**Option A: AWS Console (Recommended for first-time)**

1. Go to AWS Amplify Console: https://console.aws.amazon.com/amplify
2. Click "New app" → "Host web app"
3. Choose "GitHub"
4. Authorize GitHub access
5. Select repository: `trial-enrollment-frontend`
6. Select branch: `main`
7. Configure build settings:

```yaml
version: 1
frontend:
  phases:
    preBuild:
      commands:
        - npm install
    build:
      commands:
        - npm run build
  artifacts:
    baseDirectory: dist
    files:
      - '**/*'
  cache:
    paths:
      - node_modules/**/*
```

8. Add Environment Variables:
   - `VITE_COGNITO_USER_POOL_ID` = `<from Phase 1>`
   - `VITE_COGNITO_CLIENT_ID` = `<from Phase 1>`
   - `VITE_COGNITO_REGION` = `us-east-1`
   - `VITE_API_BASE_URL` = `<API Gateway URL from Phase 2>`

9. Click "Save and deploy"

**Option B: AWS CLI (For automation)**

```bash
# Install Amplify CLI
npm install -g @aws-amplify/cli

# Initialize Amplify app
amplify init
# Answer prompts:
# - Project name: trial-enrollment-frontend
# - Environment: prod
# - Default editor: VS Code
# - App type: javascript
# - Framework: react
# - Source directory: src
# - Distribution directory: dist
# - Build command: npm run build
# - Start command: npm run dev

# Add hosting
amplify add hosting
# Choose: Hosting with Amplify Console (Managed hosting with custom domains, CI/CD)

# Publish
amplify publish
```

### Step 4.3: Configure Custom Domain (Optional)

1. In Amplify Console, go to "Domain management"
2. Click "Add domain"
3. Enter your domain (e.g., `trials.yourcompany.com`)
4. Amplify auto-configures DNS (if using Route 53) or provides CNAME records
5. Wait for SSL certificate provisioning (~15 minutes)

### Step 4.4: Update CORS in API Gateway

Now that you have your Amplify domain, update the backend:

```bash
# Edit template.yaml
Cors:
  AllowOrigin: "'https://main.d1234567890.amplifyapp.com'"  # Your Amplify domain
  AllowHeaders: "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'"
  AllowMethods: "'GET,POST,PUT,DELETE,OPTIONS'"
  AllowCredentials: true

# Redeploy
sam build && sam deploy
```

### Step 4.5: Test Deployment

1. Visit your Amplify URL: `https://main.d1234567890.amplifyapp.com`
2. You should see the login page
3. Try logging in with test user: `crc@example.com` / `TempPass123!`
4. Change password when prompted
5. You should land on CRC dashboard

---

## 🧪 Phase 5: Testing & HIPAA Compliance

### Step 5.1: Automated Testing Script

Create `scripts/test_auth_flow.sh`:

```bash
#!/bin/bash

API_URL="https://your-api-gateway.execute-api.us-east-1.amazonaws.com/prod"
USER_EMAIL="crc@example.com"
USER_PASSWORD="YourNewPassword123!"

echo "🧪 Testing Authentication Flow..."

# Test 1: Login and get token
echo "\n1️⃣ Testing login..."
TOKEN=$(aws cognito-idp initiate-auth \
  --auth-flow USER_PASSWORD_AUTH \
  --client-id $COGNITO_CLIENT_ID \
  --auth-parameters USERNAME=$USER_EMAIL,PASSWORD=$USER_PASSWORD \
  --query 'AuthenticationResult.AccessToken' \
  --output text)

if [ -z "$TOKEN" ]; then
  echo "❌ Login failed"
  exit 1
fi
echo "✅ Login successful, token obtained"

# Test 2: Call protected endpoint
echo "\n2️⃣ Testing API call with token..."
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  $API_URL/trials)

if [ "$RESPONSE" == "200" ]; then
  echo "✅ API call successful (200 OK)"
else
  echo "❌ API call failed (HTTP $RESPONSE)"
fi

# Test 3: Call without token (should fail)
echo "\n3️⃣ Testing API call without token..."
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" \
  -H "Content-Type: application/json" \
  $API_URL/trials)

if [ "$RESPONSE" == "401" ]; then
  echo "✅ Unauthorized access correctly blocked (401)"
else
  echo "❌ Should have returned 401, got $RESPONSE"
fi

echo "\n✅ All tests passed!"
```

### Step 5.2: Manual Testing Checklist

- [ ] **Authentication Flow**
  - [ ] Login with CRC user
  - [ ] Login with StudyAdmin user
  - [ ] Login with PI user
  - [ ] Password reset flow
  - [ ] Logout
  - [ ] Token refresh (wait 1 hour, app should auto-refresh)
  - [ ] Force logout on password change

- [ ] **Authorization (CRC user)**
  - [ ] Can access /parse-criteria endpoint
  - [ ] Can access /check-criteria endpoint
  - [ ] Can access /trials (GET)
  - [ ] Cannot access /admin/* endpoints (should get 403)
  - [ ] Cannot approve patients (should get 403)

- [ ] **Authorization (PI user)**
  - [ ] Can view trials (read-only)
  - [ ] Can access analytics
  - [ ] Can approve patients
  - [ ] Cannot upload protocols (should get 403)
  - [ ] Cannot access admin endpoints (should get 403)

- [ ] **Authorization (StudyAdmin user)**
  - [ ] Can access all endpoints
  - [ ] Can reprocess trials
  - [ ] Can view audit logs
  - [ ] Can manage users

- [ ] **UI/UX**
  - [ ] Login page loads quickly (<2s)
  - [ ] Dashboard shows role-appropriate menu
  - [ ] Loading states display correctly
  - [ ] Error messages are user-friendly
  - [ ] Toast notifications work
  - [ ] Responsive on mobile/tablet

- [ ] **Security**
  - [ ] JWT tokens in Authorization header (not in URL)
  - [ ] HTTPS only (check padlock icon)
  - [ ] Tokens cleared on logout
  - [ ] No tokens visible in browser DevTools → Network tab URLs
  - [ ] CORS headers present in API responses

### Step 5.3: HIPAA Compliance Checklist

- [ ] **Cognito Configuration**
  - [ ] MFA available (optional for CRC, required for Admin/PI)
  - [ ] Password policy: 12+ chars, complexity requirements
  - [ ] Email verification enabled
  - [ ] Account recovery via email only
  - [ ] User Pool tagged with `HIPAA: true`

- [ ] **Data Protection**
  - [ ] All data encrypted in transit (TLS 1.2+)
  - [ ] All data encrypted at rest (DynamoDB, S3, HealthLake)
  - [ ] No PHI in CloudWatch logs
  - [ ] No PHI in error messages shown to users

- [ ] **Audit Trails**
  - [ ] All login attempts logged (success/failure)
  - [ ] All API calls logged with user context
  - [ ] All PHI access logged
  - [ ] Logs retained for 7 years (CloudWatch retention policy)

- [ ] **Access Controls**
  - [ ] Role-based permissions enforced (Lambda Authorizer)
  - [ ] Principle of least privilege (CRC cannot access admin functions)
  - [ ] Session timeout: 1 hour (token expiration)
  - [ ] Idle timeout: 30 minutes (configurable in frontend)

- [ ] **Legal**
  - [ ] AWS BAA (Business Associate Agreement) signed
  - [ ] HIPAA risk assessment completed
  - [ ] Security incident response plan documented

---

## 📊 Complete Integration Flow

```
┌─────────────────────────────────────────────────────────────┐
│                     USER JOURNEY                             │
└─────────────────────────────────────────────────────────────┘

1. USER OPENS AMPLIFY URL
   https://main.d1234567890.amplifyapp.com
   ↓
2. React app loads, checks auth status (useAuth hook)
   ↓
3. No active session → Redirect to /login
   ↓
4. USER ENTERS EMAIL + PASSWORD
   ↓
5. React calls Amplify signIn(email, password)
   ↓
6. AMPLIFY SDK → AWS COGNITO
   - Validates credentials
   - Checks MFA (if enabled)
   - Returns JWT tokens (ID, Access, Refresh)
   ↓
7. AMPLIFY STORES TOKENS
   - Access Token → Secure browser storage
   - Refresh Token → Secure cookie
   ↓
8. React extracts cognito:groups from token
   role = groups.includes('CRC') ? 'CRC' : ...
   ↓
9. USER REDIRECTED TO DASHBOARD
   Based on role: /crc-dashboard or /admin-dashboard or /pi-dashboard
   ↓
10. USER CLICKS "UPLOAD PROTOCOL"
   ↓
11. React calls trialAPI.parseCriteria({trial_id, criteria_text})
   ↓
12. AXIOS INTERCEPTOR
    - Calls fetchAuthSession() to get Access Token
    - Adds header: Authorization: Bearer <token>
   ↓
13. REQUEST → API GATEWAY
    POST /parse-criteria
   ↓
14. API GATEWAY INVOKES LAMBDA AUTHORIZER
   ↓
15. LAMBDA AUTHORIZER
    - Fetches Cognito public keys (cached)
    - Verifies JWT signature
    - Checks expiration
    - Extracts cognito:groups
    - Generates IAM policy:
      * CRC → Allow POST /parse-criteria
      * PI → Deny (not in allowed list)
   ↓
16. IF AUTHORIZED → API GATEWAY FORWARDS TO LAMBDA
   ↓
17. CRITERIA PARSER LAMBDA
    - Receives event with user context:
      event['requestContext']['authorizer']['email']
      event['requestContext']['authorizer']['role']
    - Logs to CloudWatch: "User crc@example.com uploaded trial NCT12345"
    - Processes criteria with Bedrock Titan
    - Returns FHIR-formatted criteria
   ↓
18. RESPONSE → API GATEWAY → REACT APP
   ↓
19. React displays success toast + trial preview
```

---

## 🎯 Summary

### Key Files Created

**Backend:**
- `infrastructure/cognito_setup.py` - Cognito User Pool setup
- `infrastructure/create_test_users.py` - Test user creation
- `src/lambda/cognito_authorizer/handler.py` - JWT validation & RBAC
- `template.yaml` - Updated with Cognito config

**Frontend (Lovable generates):**
- `src/hooks/useAuth.ts` - Authentication hook
- `src/services/api.ts` - API client with JWT injection
- `src/components/ProtectedRoute.tsx` - Route guard
- `src/pages/Login.tsx` - Login page
- `.env.local` - Environment variables

### Environment Variables

**Backend (.env for SAM):**
```bash
COGNITO_USER_POOL_ID=us-east-1_XXXXXXXXX
COGNITO_CLIENT_ID=xxxxxxxxxxxxxxxxxxxxx
COGNITO_REGION=us-east-1
```

**Frontend (.env.local in Amplify Console):**
```bash
VITE_COGNITO_USER_POOL_ID=us-east-1_XXXXXXXXX
VITE_COGNITO_CLIENT_ID=xxxxxxxxxxxxxxxxxxxxx
VITE_COGNITO_REGION=us-east-1
VITE_API_BASE_URL=https://abcd1234.execute-api.us-east-1.amazonaws.com/prod
```

### Deployment Commands

```bash
# Backend
cd infrastructure
python3 cognito_setup.py
cd ..
sam build
sam deploy --guided

# Frontend
cd lovable-trial-enrollment-app
git init && git add . && git commit -m "Initial commit"
gh repo create trial-enrollment-frontend --public --source=. --push
# Then connect via Amplify Console

# Or use Amplify CLI
amplify init
amplify add hosting
amplify publish
```

### Cost Estimate (100 users, 50 protocols/month)

| Service | Monthly Cost |
|---------|-------------|
| Cognito + Lambda Authorizer | $0 (free tier) |
| API Gateway + Lambda Functions | $2-8 |
| Textract + Comprehend Medical | $15-45 |
| HealthLake (FHIR store) | $10-30 |
| Amplify Hosting | $0-10 |
| **Total** | **$30-75/month** |

### Next Steps

1. ✅ Run Cognito setup scripts (Phase 1)
2. ✅ Deploy Lambda Authorizer (Phase 2)
3. ✅ Generate frontend with Lovable (Phase 3)
4. ✅ Deploy to Amplify Hosting (Phase 4)
5. ✅ Test authentication & authorization (Phase 5)
6. 📝 Document for team
7. 🎉 Demo to stakeholders!

---

**Questions or Issues?**
- Check CloudWatch Logs for Lambda errors
- Use browser DevTools → Network tab to inspect API calls
- Test JWT tokens at https://jwt.io
- Verify Cognito User Pool settings in AWS Console
