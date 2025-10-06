# Deployment Guide

## Prerequisites

### AWS Account Setup
1. **AWS Account** with appropriate permissions
2. **Bedrock Access** enabled in your region
   - Request model access for Anthropic Claude 3 Sonnet
   - Navigate to Amazon Bedrock > Model Access
   - Enable "Anthropic Claude 3 Sonnet"

3. **AWS CLI** configured
   ```bash
   aws configure
   ```

4. **Python 3.11+** installed
5. **Node.js 18+** (for CDK)
6. **Docker** (optional, for local FHIR server)

### Enable Required AWS Services
- Amazon Bedrock
- AWS Lambda
- Amazon API Gateway
- Amazon DynamoDB
- Amazon HealthLake (optional)
- Amazon CloudWatch

## Step 1: Clone and Setup Repository

```bash
# Clone repository
git clone <repository-url>
cd aws-trial-enrollment-agent

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Step 2: Configure Environment

Create `.env` file in project root:

```bash
# AWS Configuration
AWS_REGION=us-east-1
AWS_PROFILE=default

# Bedrock Configuration
BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0

# FHIR Configuration
FHIR_ENDPOINT=http://localhost:8080/fhir
USE_HEALTHLAKE=false

# Lambda Function Names
CRITERIA_PARSER_FUNCTION=TrialEnrollment-CriteriaParser
FHIR_SEARCH_FUNCTION=TrialEnrollment-FHIRSearch
```

## Step 3: Deploy Infrastructure with CDK

```bash
# Navigate to infrastructure directory
cd infrastructure

# Install CDK dependencies
npm install -g aws-cdk
pip install -r requirements.txt

# Bootstrap CDK (first time only)
cdk bootstrap

# Review changes
cdk diff

# Deploy stack
cdk deploy

# Note the outputs:
# - API Gateway URL
# - Lambda function names
# - DynamoDB table names
```

### CDK Outputs Example
```
TrialEnrollmentAgentStack.APIEndpoint = https://abc123.execute-api.us-east-1.amazonaws.com/prod/
TrialEnrollmentAgentStack.CriteriaParserFunctionName = TrialEnrollment-CriteriaParser
TrialEnrollmentAgentStack.FHIRSearchFunctionName = TrialEnrollment-FHIRSearch
```

## Step 4: Setup FHIR Server

### Option A: Local HAPI FHIR (Development)

```bash
# Using Docker
docker run -p 8080:8080 hapiproject/hapi:latest

# FHIR server will be available at http://localhost:8080/fhir
```

### Option B: AWS HealthLake (Production)

```bash
# Create HealthLake datastore
aws healthlake create-fhir-datastore \
  --datastore-name trial-enrollment-patients \
  --datastore-type-version R4 \
  --preload-data-config PreloadDataType=SYNTHEA

# Get datastore endpoint
aws healthlake describe-fhir-datastore \
  --datastore-id <datastore-id>

# Update .env with HealthLake endpoint
FHIR_ENDPOINT=<healthlake-endpoint>
USE_HEALTHLAKE=true
```

## Step 5: Load Synthetic Patient Data

```bash
# Navigate to project root
cd ..

# Load sample patients
python scripts/load_synthea_data.py

# Follow prompts to:
# 1. Generate synthetic patients
# 2. Save locally
# 3. Upload to FHIR server
```

Verify data loaded:
```bash
# Check patient count
curl http://localhost:8080/fhir/Patient?_summary=count

# View a specific patient
curl http://localhost:8080/fhir/Patient/patient-001
```

## Step 6: Test Lambda Functions

### Test Criteria Parser

```bash
# Create test event
cat > test-parser-event.json << EOF
{
  "criteria_text": "Patients must be between 18 and 65 years old with Type 2 Diabetes",
  "trial_id": "test-trial-001"
}
EOF

# Invoke Lambda
aws lambda invoke \
  --function-name TrialEnrollment-CriteriaParser \
  --payload file://test-parser-event.json \
  --cli-binary-format raw-in-base64-out \
  response.json

# View response
cat response.json | jq
```

### Test FHIR Search

```bash
# Create test event
cat > test-search-event.json << EOF
{
  "patient_id": "patient-001",
  "criteria": [
    {
      "type": "inclusion",
      "category": "demographics",
      "description": "Age 18-65",
      "attribute": "age",
      "operator": "between",
      "value": [18, 65]
    }
  ]
}
EOF

# Invoke Lambda
aws lambda invoke \
  --function-name TrialEnrollment-FHIRSearch \
  --payload file://test-search-event.json \
  --cli-binary-format raw-in-base64-out \
  response.json

# View response
cat response.json | jq
```

## Step 7: Test API Gateway Endpoints

```bash
# Set API endpoint (from CDK output)
export API_ENDPOINT=https://abc123.execute-api.us-east-1.amazonaws.com/prod

# Test health check
curl $API_ENDPOINT/health

# Test parse criteria
curl -X POST $API_ENDPOINT/parse-criteria \
  -H "Content-Type: application/json" \
  -d '{
    "criteria_text": "Patients must be 18-65 years old",
    "trial_id": "test-001"
  }' | jq

# Test check criteria
curl -X POST $API_ENDPOINT/check-criteria \
  -H "Content-Type: application/json" \
  -d '{
    "patient_id": "patient-001",
    "criteria": [...]
  }' | jq
```

## Step 8: Run End-to-End Agent

```bash
# Update environment variables with deployed Lambda names
export CRITERIA_PARSER_FUNCTION=TrialEnrollment-CriteriaParser
export FHIR_SEARCH_FUNCTION=TrialEnrollment-FHIRSearch
export AWS_REGION=us-east-1

# Run demo script
python scripts/demo.py
```

## Step 9: Run Tests

```bash
# Install test dependencies
pip install pytest pytest-cov pytest-mock

# Run unit tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# View coverage report
open htmlcov/index.html
```

## Step 10: Monitoring & Logs

### View Lambda Logs

```bash
# Criteria Parser logs
aws logs tail /aws/lambda/TrialEnrollment-CriteriaParser --follow

# FHIR Search logs
aws logs tail /aws/lambda/TrialEnrollment-FHIRSearch --follow
```

### CloudWatch Metrics

Access CloudWatch Console to view:
- Lambda invocation count
- Error rates
- Duration metrics
- API Gateway request metrics

### Create Dashboard

```bash
# Create monitoring dashboard
aws cloudwatch put-dashboard \
  --dashboard-name TrialEnrollmentAgent \
  --dashboard-body file://infrastructure/dashboard.json
```

## Troubleshooting

### Issue: Bedrock Access Denied

**Solution:**
```bash
# Check model access
aws bedrock list-foundation-models --region us-east-1

# Request access via console
# Bedrock > Model Access > Request access
```

### Issue: Lambda Timeout

**Solution:**
- Increase Lambda timeout in CDK stack
- Optimize FHIR queries
- Use caching for repeated criteria parsing

### Issue: FHIR Connection Failed

**Solution:**
```bash
# Verify FHIR endpoint
curl $FHIR_ENDPOINT/metadata

# Check security group rules (if using VPC)
# Verify network connectivity
```

### Issue: Rate Limiting

**Solution:**
- Implement exponential backoff
- Request Bedrock quota increase
- Use DynamoDB caching more aggressively

## Production Considerations

### 1. Security Hardening
- [ ] Enable VPC for Lambda functions
- [ ] Use AWS Secrets Manager for credentials
- [ ] Enable CloudTrail for audit logging
- [ ] Implement API Gateway authentication
- [ ] Enable WAF for API Gateway

### 2. Cost Optimization
- [ ] Set up billing alarms
- [ ] Use Lambda reserved concurrency
- [ ] Implement DynamoDB TTL for old data
- [ ] Monitor Bedrock usage
- [ ] Use CloudWatch Logs Insights for optimization

### 3. High Availability
- [ ] Deploy across multiple AZs
- [ ] Implement circuit breakers
- [ ] Set up CloudWatch alarms
- [ ] Create runbooks for incidents
- [ ] Test disaster recovery procedures

### 4. Compliance
- [ ] Sign AWS BAA for HIPAA compliance
- [ ] Implement data retention policies
- [ ] Set up encrypted backups
- [ ] Document PHI handling procedures
- [ ] Regular security audits

## Cleanup

To avoid ongoing charges, destroy the stack when done:

```bash
# Delete CloudFormation stack
cd infrastructure
cdk destroy

# Confirm deletion
# Type 'y' when prompted

# Delete HealthLake datastore (if created)
aws healthlake delete-fhir-datastore --datastore-id <datastore-id>

# Stop local FHIR server
docker stop <container-id>
```

## Next Steps

1. **Customize Criteria Parser** - Add domain-specific medical ontologies
2. **Enhance FHIR Queries** - Support more resource types and complex queries
3. **Add UI** - Build web interface for clinicians
4. **Integrate EHR** - Connect to real EHR systems via HL7/FHIR
5. **Scale Testing** - Load test with larger patient populations
6. **Add Features** - Site feasibility, patient matching scores, etc.

## Support

For issues or questions:
- Check documentation in `/docs`
- Review CloudWatch logs
- Open GitHub issue
- Contact AWS Support for service-specific issues

---

**Last Updated:** 2024-10-05
**Version:** 1.0.0
