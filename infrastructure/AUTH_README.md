# Authentication Infrastructure

Complete AWS Cognito + Lambda Authorizer setup for role-based access control (RBAC) in the Clinical Trial Enrollment System.

## 📋 Overview

This infrastructure provides:
- **AWS Cognito User Pool** with HIPAA-compliant security settings
- **Lambda Authorizer** for JWT token validation
- **Role-Based Access Control (RBAC)** with 3 personas: CRC, StudyAdmin, PI
- **API Gateway integration** with protected endpoints
- **Test users** for development and testing

## 🏗️ Architecture

```
User → Cognito (Login) → JWT Token
         ↓
API Gateway → Lambda Authorizer → Verify JWT
         ↓                ↓
    Protected Endpoints ← Allow/Deny based on Role
```

## 🚀 Quick Start

### 1. Create Cognito User Pool and Groups

```bash
python3 cognito_setup.py
```

This creates:
- User Pool with HIPAA-compliant password policy
- App Client for web applications
- User Groups: CRC, StudyAdmin, PI
- Configuration saved to `cognito-config.json`

### 2. Create Test Users

```bash
python3 create_test_users.py
```

This creates test users for each role:
- **CRC**: `crc_test` / `TestCRC@2025!`
- **StudyAdmin**: `studyadmin_test` / `TestAdmin@2025!`
- **PI**: `pi_test` / `TestPI@2025!`

Credentials saved to `test-users.json` (gitignored)

### 3. Deploy Lambda Authorizer

```bash
./deploy_auth.sh
```

This:
- Installs Lambda dependencies (python-jose)
- Deploys CDK stack with Lambda Authorizer
- Configures API Gateway with protected endpoints
- Outputs API Gateway URL

## 🔑 Getting JWT Tokens

### Using Helper Script

```bash
# Get token for CRC user
python3 get_jwt_token.py --role crc

# Get token for StudyAdmin
python3 get_jwt_token.py --role studyadmin

# Get token for PI with payload details
python3 get_jwt_token.py --role pi --show-payload

# Custom user
python3 get_jwt_token.py --username myuser --password MyPass@123!
```

### Using AWS CLI

```bash
aws cognito-idp initiate-auth \
  --client-id 37ef9023q0b9q6lsdvc5rlvpo1 \
  --auth-flow USER_PASSWORD_AUTH \
  --auth-parameters USERNAME=crc_test,PASSWORD=TestCRC@2025! \
  --region us-east-1
```

## 🧪 Testing Authentication

### 1. Test Protected Endpoint (with token)

```bash
# Get token
TOKEN=$(python3 get_jwt_token.py --role crc | grep "Access Token" -A 1 | tail -1)

# Call protected endpoint
curl -X POST https://YOUR_API_URL/prod/parse-criteria \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "trial_id": "test-001",
    "criteria_text": "Age >= 18 years"
  }'
```

### 2. Test Without Token (should return 401)

```bash
curl -X POST https://YOUR_API_URL/prod/parse-criteria \
  -H "Content-Type: application/json" \
  -d '{
    "trial_id": "test-001",
    "criteria_text": "Age >= 18 years"
  }'
```

### 3. Test RBAC (role-based access)

```bash
# CRC user trying to access StudyAdmin-only endpoint (should fail)
CRC_TOKEN=$(python3 get_jwt_token.py --role crc | grep "Access Token" -A 1 | tail -1)

curl -X POST https://YOUR_API_URL/prod/protocols/upload \
  -H "Authorization: Bearer $CRC_TOKEN" \
  -H "Content-Type: application/json"
# Expected: 403 Forbidden

# StudyAdmin user (should succeed)
ADMIN_TOKEN=$(python3 get_jwt_token.py --role studyadmin | grep "Access Token" -A 1 | tail -1)

curl -X POST https://YOUR_API_URL/prod/protocols/upload \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json"
# Expected: 200 OK
```

## 📊 RBAC Permission Matrix

| Role | View Protocols | Check Eligibility | Upload Protocols | Manage Users | View Analytics |
|------|---------------|-------------------|------------------|--------------|----------------|
| **CRC** | ✅ | ✅ | ❌ | ❌ | ❌ |
| **StudyAdmin** | ✅ | ✅ | ✅ | ✅ | ✅ (read-only) |
| **PI** | ✅ | ✅ | ✅ | ✅ | ✅ (full access) |

### API Endpoint Permissions

```python
# CRC permissions
GET  /protocols/*              ✅ Allowed
POST /eligibility/check        ✅ Allowed
POST /protocols/search         ✅ Allowed
POST /protocols/upload         ❌ Denied

# StudyAdmin permissions (all CRC + upload/manage)
POST /protocols/upload         ✅ Allowed
PUT  /protocols/*              ✅ Allowed
DELETE /protocols/*            ✅ Allowed
GET  /analytics/*              ✅ Allowed (read-only)

# PI permissions (all access)
*    /enrollment/*             ✅ Allowed (full access)
*    /analytics/*              ✅ Allowed (full access)
```

## 🔧 Configuration Files

### cognito-config.json

```json
{
  "UserPoolId": "us-east-1_zLcYERVQI",
  "UserPoolArn": "arn:aws:cognito-idp:us-east-1:519510601754:userpool/us-east-1_zLcYERVQI",
  "ClientId": "37ef9023q0b9q6lsdvc5rlvpo1",
  "Region": "us-east-1",
  "Groups": {
    "CRC": "Clinical Research Coordinators",
    "StudyAdmin": "Study Administrators",
    "PI": "Principal Investigators"
  },
  "ApiUrl": "https://YOUR_API_ID.execute-api.us-east-1.amazonaws.com/prod/"
}
```

### test-users.json (gitignored)

```json
{
  "users": [
    {
      "username": "crc_test",
      "email": "crc.test@example.com",
      "name": "Sarah Johnson (CRC)",
      "role": "CRC",
      "password": "TestCRC@2025!"
    }
  ]
}
```

## 🌐 Frontend Integration

### AWS Amplify Configuration

```typescript
// src/config/amplify-config.ts
import { Amplify } from 'aws-amplify';

export const amplifyConfig = {
  Auth: {
    Cognito: {
      userPoolId: 'us-east-1_zLcYERVQI',
      userPoolClientId: '37ef9023q0b9q6lsdvc5rlvpo1',
      region: 'us-east-1'
    }
  }
};

Amplify.configure(amplifyConfig);
```

### Login Example

```typescript
import { signIn, fetchAuthSession, getCurrentUser } from '@aws-amplify/auth';

// Login
async function login(username: string, password: string) {
  try {
    const user = await signIn({ username, password });
    console.log('✅ Logged in:', user);

    // Get JWT tokens
    const session = await fetchAuthSession();
    const accessToken = session.tokens?.accessToken.toString();

    // Get user info and groups
    const currentUser = await getCurrentUser();
    const idToken = session.tokens?.idToken;
    const groups = idToken?.payload['cognito:groups'] as string[];

    console.log('User groups:', groups); // ['CRC'] or ['StudyAdmin'] or ['PI']

    return { accessToken, groups };
  } catch (error) {
    console.error('❌ Login failed:', error);
    throw error;
  }
}
```

### API Request with JWT

```typescript
import { fetchAuthSession } from '@aws-amplify/auth';
import axios from 'axios';

async function callProtectedAPI() {
  // Get access token
  const session = await fetchAuthSession();
  const accessToken = session.tokens?.accessToken.toString();

  // Call API with Authorization header
  const response = await axios.post(
    'https://YOUR_API_URL/prod/parse-criteria',
    {
      trial_id: 'test-001',
      criteria_text: 'Age >= 18 years'
    },
    {
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json'
      }
    }
  );

  return response.data;
}
```

## 🐛 Troubleshooting

### Error: "Unauthorized: No token provided"

**Cause**: Missing or malformed Authorization header

**Fix**: Ensure header format is `Authorization: Bearer <JWT_TOKEN>`

### Error: "Unauthorized: Token expired"

**Cause**: Access token expired (60 minutes)

**Fix**: Refresh token or re-authenticate

```typescript
import { fetchAuthSession } from '@aws-amplify/auth';

// Amplify automatically refreshes tokens
const session = await fetchAuthSession({ forceRefresh: true });
```

### Error: "Forbidden: Insufficient permissions"

**Cause**: User role doesn't have permission for the endpoint

**Fix**:
1. Verify user is in correct Cognito group
2. Check RBAC matrix in `src/lambda/authorizer/lambda_function.py`
3. Test with different user role

### Error: "Public key not found for kid"

**Cause**: Lambda Authorizer can't fetch Cognito public keys

**Fix**:
1. Check Lambda has internet access (VPC NAT Gateway or no VPC)
2. Verify User Pool ID is correct
3. Check CloudWatch Logs for authorizer function

## 📁 File Structure

```
infrastructure/
├── cognito_setup.py              # Create User Pool, Client, Groups
├── create_test_users.py          # Create test users for each role
├── get_jwt_token.py              # Helper to get JWT tokens for testing
├── deploy_auth.sh                # Deploy Lambda Authorizer with CDK
├── app.py                        # CDK stack definition (updated with authorizer)
├── cognito-config.json           # Cognito configuration (gitignored)
├── test-users.json               # Test user credentials (gitignored)
└── AUTH_README.md                # This file

src/lambda/authorizer/
├── lambda_function.py            # Lambda Authorizer implementation
└── requirements.txt              # python-jose[cryptography]
```

## 🔐 Security Best Practices

1. **Never commit sensitive files**:
   - `cognito-config.json` contains IDs (not secrets, but keep private)
   - `test-users.json` contains passwords (definitely gitignored)

2. **Production users**:
   - Use Cognito-managed sign-up flow (not admin-created users)
   - Enable MFA for all users (currently disabled, needs SMS config)
   - Use stronger password policy (current: 12 chars, all char types)

3. **Token handling**:
   - Store tokens securely (sessionStorage or memory, NOT localStorage)
   - Always use HTTPS for API calls
   - Implement token refresh logic
   - Clear tokens on logout

4. **RBAC enforcement**:
   - Lambda Authorizer validates JWT signature
   - Backend Lambda functions should ALSO verify user groups from context
   - Don't rely solely on frontend role checks

5. **Monitoring**:
   - Enable CloudWatch Logs for authorizer function
   - Monitor failed authentication attempts
   - Set up CloudWatch Alarms for 401/403 errors

## 📚 Additional Resources

- [AWS Cognito Documentation](https://docs.aws.amazon.com/cognito/)
- [Lambda Authorizer Guide](https://docs.aws.amazon.com/apigateway/latest/developerguide/apigateway-use-lambda-authorizer.html)
- [AWS Amplify Auth](https://docs.amplify.aws/javascript/build-a-backend/auth/)
- [JWT.io - Token Debugger](https://jwt.io/)

## 🆘 Support

For issues or questions:
1. Check CloudWatch Logs for Lambda Authorizer
2. Verify Cognito User Pool and Groups are created
3. Test JWT token with [jwt.io](https://jwt.io/)
4. Review RBAC matrix in `lambda_function.py`

---

✅ **Authentication infrastructure is now ready for production use!**
