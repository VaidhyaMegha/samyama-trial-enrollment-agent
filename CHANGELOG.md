# Changelog

All notable changes to the AWS Trial Enrollment Agent project.

## [1.0.0] - 2025-10-06

### 🎉 Initial Deployment

#### Added
- **Criteria Parser Lambda Function**
  - Implemented using Amazon Bedrock Titan Text Express v1
  - Parses free-text eligibility criteria into structured JSON format
  - Supports multiple Bedrock API response formats (old and new)
  - Validates parsed criteria with comprehensive error handling
  - Deployed to AWS us-east-1 region

- **FHIR Search Lambda Function**
  - Queries AWS HealthLake FHIR R4 datastore
  - Implements AWS SigV4 authentication for secure HealthLake access
  - Supports demographic, condition, and observation criteria
  - Provides detailed eligibility results with evidence
  - Age calculation from FHIR birthDate
  - Deployed to AWS us-east-1 region

- **AWS Infrastructure (CDK)**
  - API Gateway REST API with CORS support
  - Two Lambda functions with proper IAM roles
  - DynamoDB tables for criteria cache and evaluation results
  - CloudWatch logging with AWS Lambda Powertools
  - HealthLake integration with proper permissions

- **HealthLake FHIR Datastore**
  - Created FHIR R4 datastore in us-east-1
  - Datastore ID: `8640ed6b344b85e4729ac42df1c7d00e`
  - Uploaded 3 synthetic patients:
    - patient-001: Female, 46 years (eligible)
    - patient-002: Male, 15 years (not eligible)
    - patient-003: Male, 55 years (eligible)

- **Scripts and Utilities**
  - `load_synthea_data.py`: Generate synthetic FHIR patient data
  - `upload_to_healthlake.py`: Upload patient bundles to HealthLake with SigV4 auth
  - `end_to_end_demo.py`: Complete workflow demonstration script

- **Comprehensive Testing**
  - 15 unit tests with pytest
  - 14/15 tests passing (93% pass rate)
  - Tests for criteria parser validation and parsing
  - Tests for FHIR search functionality
  - End-to-end integration testing

- **Documentation**
  - Comprehensive README.md with deployment status
  - API endpoint documentation
  - Usage examples and troubleshooting guide
  - Cost estimates and compliance information

#### Changed
- Updated model from Claude to Amazon Titan Text Express v1
- Modified Lambda handlers to support both old and new Bedrock response formats
- Enhanced error handling in criteria parser
- Improved FHIR search with AWS SigV4 authentication

#### Infrastructure Details
- **Region**: us-east-1
- **API Gateway**: `https://gt7dlyqj78.execute-api.us-east-1.amazonaws.com/prod/`
- **Lambda Functions**:
  - TrialEnrollment-CriteriaParser
  - TrialEnrollment-FHIRSearch
- **DynamoDB Tables**:
  - CriteriaCacheTable
  - EvaluationResultsTable

#### Test Results
```
Total Tests: 15
Passed: 14
Failed: 1 (test isolation issue, passes independently)
Success Rate: 93%
```

#### End-to-End Demo Results
```
Trial: demo-trial-001
Criteria: Patients must be between 18 and 65 years old

✓ patient-001: ELIGIBLE (Female, 46 years)
✗ patient-002: NOT ELIGIBLE (Male, 15 years)
✓ patient-003: ELIGIBLE (Male, 55 years)

Success Rate: 67% (2/3 patients eligible)
```

### Dependencies
- Python 3.11+
- boto3 ~= 1.34.0
- aws-lambda-powertools >= 2.31.0
- aws-xray-sdk >= 2.12.0
- requests >= 2.31.0
- AWS CDK 2.x
- Node.js 18+

### AWS Services Used
- Amazon Bedrock (Titan Text Express v1)
- AWS Lambda
- Amazon API Gateway
- AWS HealthLake (FHIR R4)
- Amazon DynamoDB
- Amazon CloudWatch
- AWS IAM

### Known Issues
- 1 test has intermittent failures due to test isolation (passes when run independently)
- CDK bootstrap warnings (non-blocking, deployment successful)

### Security & Compliance
- ✅ HIPAA-eligible AWS services
- ✅ AWS SigV4 authentication for HealthLake
- ✅ IAM least privilege roles
- ✅ DynamoDB and HealthLake encryption enabled
- ✅ CloudWatch audit logging
- ✅ Synthetic test data only (no real PHI)

---

## Upcoming Features

### Planned for v1.1.0
- [ ] Agent workflow orchestration
- [ ] Advanced criteria parsing (lab values, medications)
- [ ] Batch patient screening
- [ ] Enhanced security guardrails
- [ ] Production hardening
- [ ] Performance optimization

### Future Considerations
- [ ] Multi-region deployment
- [ ] Criteria caching optimization
- [ ] Real-time patient monitoring
- [ ] Integration with clinical trial registries
- [ ] Advanced matching algorithms
- [ ] UI/Dashboard for study coordinators
