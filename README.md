# Clinical Trial Enrollment & Eligibility Agent

An autonomous AI agent that automates patient-trial matching by parsing clinical trial eligibility criteria and cross-referencing them with patient electronic health records (EHR) in FHIR format.

## Overview

Clinical trial enrollment is the #1 bottleneck in medical research. This project uses Amazon Bedrock to create an intelligent agent that:

1. **Parses** trial eligibility criteria from protocols into structured, computable format
2. **Searches** FHIR-compliant patient records to check criteria
3. **Matches** patients to trials with explainable, criterion-by-criterion justifications
4. **Generates** eligibility reports for study coordinators

## Architecture

```
┌─────────────────┐
│  User/Clinician │
└────────┬────────┘
         │
         v
┌──────────────────────────────────────────┐
│       API Gateway (REST API)             │
│   https://...execute-api.us-east-1...    │
└────────┬────────────────────┬────────────┘
         │                    │
         v                    v
┌────────────────┐    ┌─────────────────┐
│ Criteria Parser│    │  FHIR Search    │
│    Lambda      │    │     Lambda      │
│                │    │                 │
│ Amazon Titan   │    │ HealthLake Auth │
│   Bedrock API  │    │    (SigV4)      │
└────────┬───────┘    └────────┬────────┘
         │                     │
         v                     v
    ┌─────────┐         ┌──────────────┐
    │ Bedrock │         │  HealthLake  │
    │  Titan  │         │ FHIR R4 Store│
    └─────────┘         └──────────────┘
         │                     │
         v                     v
    ┌─────────────────────────────────┐
    │  DynamoDB Tables                │
    │  - Criteria Cache               │
    │  - Evaluation Results           │
    └─────────────────────────────────┘
```

## Key Features

- **Automated Criteria Parsing**: Converts free-text eligibility criteria into structured JSON using Amazon Titan
- **FHIR Integration**: Queries patient data from AWS HealthLake using authenticated FHIR APIs
- **Explainable Results**: Provides per-criterion pass/fail explanations with evidence
- **HIPAA-Eligible**: Uses AWS HealthLake with proper authentication and encryption
- **Audit Trail**: Complete observability via CloudWatch and AWS Lambda Powertools
- **Serverless Architecture**: Fully serverless with auto-scaling Lambda functions

## Technology Stack

- **Amazon Bedrock (Titan Text Express v1)**: LLM for criteria parsing and reasoning
- **Amazon HealthLake**: FHIR R4-compliant patient data store (HIPAA-eligible)
- **AWS Lambda**: Serverless functions for criteria parser and FHIR search
- **Amazon API Gateway**: REST API endpoints for tool invocation
- **Amazon DynamoDB**: Caching parsed criteria and evaluation results
- **Amazon CloudWatch**: Logging and observability
- **AWS CDK (Python)**: Infrastructure as Code
- **AWS Lambda Powertools**: Structured logging, tracing, and metrics

## Project Structure

```
aws-trial-enrollment-agent/
├── docs/                             # Documentation
│   ├── PROTOCOL_PROCESSING_GUIDE.md  # Protocol PDF processing guide
│   ├── implementation_plan.md        # Detailed implementation strategy
│   └── deployment_guide.md           # Deployment instructions
├── src/                              # Source code
│   ├── lambda/                       # Lambda functions
│   │   ├── criteria_parser/          # Criteria parsing (Amazon Titan)
│   │   ├── fhir_search/              # FHIR query tool (HealthLake)
│   │   ├── textract_processor/       # PDF text extraction (AWS Textract)
│   │   ├── section_classifier/       # Criteria classification (Comprehend Medical)
│   │   └── protocol_orchestrator/    # Pipeline orchestration
│   ├── agent/                        # Agent configuration
│   └── utils/                        # Shared utilities
├── infrastructure/                   # AWS CDK Infrastructure
│   └── app.py                       # CDK stack definition
├── scripts/                          # Utility scripts
│   ├── process_protocol_pdf.py      # End-to-end protocol processor
│   ├── load_synthea_data.py         # Generate synthetic FHIR data
│   ├── upload_to_healthlake.py      # Upload patients to HealthLake
│   └── end_to_end_demo.py           # Complete workflow demonstration
├── tests/                            # Test suites (pytest)
│   ├── test_criteria_parser.py      # Criteria parser tests
│   └── test_fhir_search.py          # FHIR search tests
├── protocol-docs/                    # Sample protocol PDFs for testing
├── tmp/                              # Temporary output files (gitignored)
├── requirements.txt                  # Python dependencies
└── README.md                         # This file
```

## Deployment Status

### ✅ Deployed Infrastructure (AWS us-east-1)

- **API Gateway Endpoint**: `https://gt7dlyqj78.execute-api.us-east-1.amazonaws.com/prod/`
- **Criteria Parser Lambda**: `TrialEnrollment-CriteriaParser`
- **FHIR Search Lambda**: `TrialEnrollment-FHIRSearch`
- **HealthLake Datastore**: `8640ed6b344b85e4729ac42df1c7d00e` (FHIR R4)
- **DynamoDB Tables**:
  - Criteria Cache Table
  - Evaluation Results Table

### 📊 Test Results

- **14/15 tests passing** (93% pass rate)
- End-to-end demo: ✅ Successful
- Deployed Lambdas: ✅ Fully functional

### 🧪 Sample Data

- **3 Synthetic Patients** loaded in HealthLake:
  - `patient-001`: Female, 46 years old, eligible for age 18-65 trial
  - `patient-002`: Male, 15 years old, not eligible (under 18)
  - `patient-003`: Male, 55 years old, eligible for age 18-65 trial

## Quick Start: Protocol Processing

**Process any clinical trial protocol PDF in one command:**

```bash
python scripts/process_protocol_pdf.py /path/to/protocol.pdf
```

This script will:
1. Upload the PDF to S3
2. Extract eligibility criteria using AWS Textract
3. Classify criteria using Amazon Comprehend Medical
4. Save structured outputs to `tmp/` directory

**Example:**
```bash
# Process a protocol PDF
python scripts/process_protocol_pdf.py protocol-docs/26_page.pdf

# With custom trial ID
python scripts/process_protocol_pdf.py ~/Downloads/trial.pdf --trial-id NCT12345678
```

For detailed information, see [Protocol Processing Guide](docs/PROTOCOL_PROCESSING_GUIDE.md).

## Getting Started

### Prerequisites

- AWS Account with:
  - Amazon Bedrock access (Titan models enabled in us-east-1)
  - HealthLake permissions
  - Lambda, API Gateway, and DynamoDB permissions
- Python 3.11+
- AWS CLI configured
- Node.js 18+ (for AWS CDK)

### Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd aws-trial-enrollment-agent
   ```

2. **Create and activate virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure AWS credentials**
   ```bash
   aws configure
   # Set region to us-east-1 for Bedrock Titan access
   ```

5. **Enable Bedrock model access**
   - Go to AWS Console → Bedrock → Model access
   - Enable "Titan Text Express" model

6. **Deploy infrastructure with CDK**
   ```bash
   cd infrastructure
   npm install -g aws-cdk
   pip install -r requirements.txt
   cdk deploy --require-approval never
   ```

7. **Create HealthLake FHIR datastore** (if not exists)
   ```bash
   aws healthlake create-fhir-datastore \
     --datastore-name "TrialEnrollmentDatastore" \
     --datastore-type-version R4 \
     --region us-east-1
   ```

8. **Load synthetic patient data**
   ```bash
   cd ../scripts
   python3 upload_to_healthlake.py
   ```

### Running Tests

```bash
# Set environment variables
export POWERTOOLS_TRACE_DISABLED=1
export AWS_XRAY_CONTEXT_MISSING=LOG_ERROR

# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

## Usage

### Test Individual Lambda Functions

**Criteria Parser:**
```bash
aws lambda invoke \
  --function-name TrialEnrollment-CriteriaParser \
  --cli-binary-format raw-in-base64-out \
  --payload file://test-criteria.json \
  response.json \
  --region us-east-1

cat response.json | python3 -m json.tool
```

**FHIR Search:**
```bash
aws lambda invoke \
  --function-name TrialEnrollment-FHIRSearch \
  --cli-binary-format raw-in-base64-out \
  --payload file://test-fhir-search.json \
  response.json \
  --region us-east-1

cat response.json | python3 -m json.tool
```

### Run End-to-End Demo

```bash
cd scripts
python3 end_to_end_demo.py
```

**Demo Output:**
```
================================================================================
STEP 1: Parsing Eligibility Criteria
================================================================================
Trial ID: demo-trial-001
Criteria Text: Patients must be between 18 and 65 years old

✓ Successfully parsed 1 criteria

================================================================================
STEP 2: Checking Patient Eligibility - patient-001
================================================================================
Patient: patient-001
Eligible: ✓ YES

Criteria Results:
  1. Age between 18 and 65 years: ✓ MET
     Reason: Patient age is 46 years

================================================================================
FINAL SUMMARY
================================================================================
Total Patients Tested: 3
Eligible Patients: 2
Not Eligible: 1
```

### Programmatic Usage

```python
import boto3
import json

lambda_client = boto3.client('lambda', region_name='us-east-1')

# Step 1: Parse criteria
parse_response = lambda_client.invoke(
    FunctionName='TrialEnrollment-CriteriaParser',
    InvocationType='RequestResponse',
    Payload=json.dumps({
        'criteria_text': 'Patients must be between 18 and 65 years old',
        'trial_id': 'test-trial-001'
    })
)

parsed = json.loads(parse_response['Payload'].read())
criteria = json.loads(parsed['body'])['criteria']

# Step 2: Check patient eligibility
search_response = lambda_client.invoke(
    FunctionName='TrialEnrollment-FHIRSearch',
    InvocationType='RequestResponse',
    Payload=json.dumps({
        'patient_id': 'patient-001',
        'criteria': criteria
    })
)

result = json.loads(search_response['Payload'].read())
eligibility = json.loads(result['body'])

print(f"Patient eligible: {eligibility['eligible']}")
print(f"Reason: {eligibility['results'][0]['reason']}")
```

## API Endpoints

### POST /parse-criteria
Parse free-text eligibility criteria into structured format.

**Request:**
```json
{
  "criteria_text": "Patients must be between 18 and 65 years old",
  "trial_id": "trial-001"
}
```

**Response:**
```json
{
  "criteria": [{
    "type": "inclusion",
    "category": "demographics",
    "description": "Age between 18 and 65 years",
    "attribute": "age",
    "operator": "between",
    "value": [18, 65],
    "unit": "years",
    "fhir_resource": "Patient",
    "fhir_path": "Patient.birthDate"
  }],
  "trial_id": "trial-001",
  "count": 1
}
```

### POST /check-criteria
Check if a patient meets eligibility criteria.

**Request:**
```json
{
  "patient_id": "patient-001",
  "criteria": [...]
}
```

**Response:**
```json
{
  "patient_id": "patient-001",
  "eligible": true,
  "results": [{
    "met": true,
    "reason": "Patient age is 46 years",
    "evidence": {
      "birthDate": "1979-05-15",
      "calculated_age": 46
    }
  }],
  "summary": {
    "total_criteria": 1,
    "inclusion_met": 1,
    "exclusion_violated": 0
  }
}
```

## Development Roadmap

- [x] Project documentation and architecture design
- [x] Criteria Parser implementation with Amazon Titan
- [x] FHIR Search Integration with HealthLake
- [x] AWS Infrastructure deployment (Lambda, API Gateway, DynamoDB)
- [x] HealthLake datastore setup and patient data loading
- [x] End-to-end testing and demo
- [x] AWS SigV4 authentication for HealthLake
- [ ] Agent Workflow orchestration
- [ ] Advanced criteria parsing (lab values, medications)
- [ ] Batch patient screening
- [ ] Security guardrails enhancement
- [ ] Production hardening

## Guardrails & Compliance

- **HIPAA-Eligible Services**: AWS HealthLake with encryption at rest and in transit
- **No Real PHI**: All testing uses Synthea-generated synthetic patient data
- **Audit Logging**: Complete trail of Lambda invocations via CloudWatch
- **AWS IAM**: Least privilege roles for Lambda functions
- **Data Encryption**: DynamoDB encryption enabled, HealthLake AWS-managed encryption
- **Human Review Required**: System provides eligibility assessments; final enrollment decisions require clinician confirmation
- **AWS Lambda Powertools**: Structured logging with correlation IDs for tracing

## Cost Considerations

**Estimated Monthly Costs (Development):**
- Amazon Bedrock (Titan Text Express): ~$5-10 for testing
- AWS HealthLake: ~$0.75/GB stored + $1.00 per 1M requests
- AWS Lambda: Within free tier for development
- API Gateway: Within free tier for development
- DynamoDB: On-demand pricing, minimal for development
- CloudWatch Logs: ~$1-2/month

**Total Estimated**: $10-20/month for development and testing

## Troubleshooting

### Common Issues

1. **Bedrock Access Denied**
   - Ensure Titan models are enabled in the AWS Console
   - Check your region is us-east-1

2. **HealthLake 401 Unauthorized**
   - Lambda execution role needs HealthLake permissions
   - Check datastore ID is correct

3. **Tests Failing**
   - Set environment variables: `POWERTOOLS_TRACE_DISABLED=1`
   - Ensure virtual environment is activated

4. **CDK Deploy Failures**
   - Run `cdk bootstrap` if first time using CDK
   - Check IAM permissions for CloudFormation

## AWS Hackathon Compliance

### Required Technologies
- ✅ Amazon Bedrock (Titan Text Express v1 for LLM inference)
- ✅ AWS Lambda (Serverless compute for tools)
- ✅ Amazon API Gateway (Tool endpoints)

### Scoring Criteria
- **Functionality**: ✅ End-to-end working system with real trial matching
- **Technical Execution**: ✅ Multi-service AWS integration, serverless architecture
- **Architecture**: ✅ Scalable, secure, well-documented design
- **Presentation**: ✅ Working demo, comprehensive documentation
- **Guardrails**: ✅ HIPAA compliance, safety measures, audit trails

## License

MIT License - See LICENSE file for details

## Contributors

Built with ❤️ for AWS AI Agent Hackathon 2025

## References

1. [AWS HealthLake Documentation](https://docs.aws.amazon.com/healthlake/)
2. [Amazon Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
3. [FHIR R4 Specification](https://hl7.org/fhir/R4/)
4. [Synthea Patient Generator](https://github.com/synthetichealth/synthea)
5. [AWS Lambda Powertools](https://awslabs.github.io/aws-lambda-powertools-python/)

---

**Built for AWS AI Agent Hackathon 2025**

**Status**: ✅ Deployed and Functional | **Region**: us-east-1 | **Last Updated**: 2025-10-06
