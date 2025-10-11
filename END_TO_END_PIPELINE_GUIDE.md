# End-to-End Protocol Processing Pipeline - Deployment & Testing Guide

## 🎯 What Was Implemented

The complete automatic pipeline that processes clinical trial protocol PDFs end-to-end:

```
PDF Upload → Textract → Section Classifier → Parse-Criteria API → DynamoDB → Ready for Patient Matching
```

## 🚀 Deployment Steps

### 1. Deploy Infrastructure

```bash
cd infrastructure
cdk deploy
```

**What gets deployed:**
- ✅ Textract Processor Lambda (with S3 trigger)
- ✅ Section Classifier Lambda
- ✅ Protocol Orchestrator Lambda
- ✅ Parse-Criteria API Lambda
- ✅ Check-Criteria API Lambda
- ✅ DynamoDB tables for caching
- ✅ API Gateway endpoints
- ✅ S3 bucket for protocol PDFs
- ✅ All IAM permissions

### 2. Note the Outputs

After deployment, you'll see:

```
Outputs:
TrialEnrollmentAgentStack.APIEndpoint = https://xxxxx.execute-api.us-east-1.amazonaws.com/prod/
TrialEnrollmentAgentStack.ProtocolBucketName = trial-enrollment-protocols-123456789
TrialEnrollmentAgentStack.CriteriaCacheTableName = TrialEnrollmentAgentStack-CriteriaCacheTable-XXXXX
```

**Save these values!** You'll need them to test and view outputs.

## 📤 Testing the Pipeline

### Option 1: Upload a PDF to S3 (Fully Automatic)

```bash
# Get your bucket name from CDK outputs
BUCKET_NAME="trial-enrollment-protocols-123456789"

# Upload a protocol PDF
aws s3 cp protocol-docs/NCT12345678.pdf s3://${BUCKET_NAME}/NCT12345678.pdf
```

**What happens automatically:**
1. ✅ S3 triggers Textract Processor Lambda
2. ✅ Textract extracts text, tables, and queries
3. ✅ Textract Processor invokes Protocol Orchestrator
4. ✅ Protocol Orchestrator invokes Section Classifier
5. ✅ Section Classifier extracts inclusion/exclusion criteria
6. ✅ Protocol Orchestrator calls Parse-Criteria API
7. ✅ Parse-Criteria API uses Bedrock to parse criteria
8. ✅ Results stored in DynamoDB
9. ✅ Pipeline complete!

**Time:** ~2-5 minutes for a typical 100-page protocol

### Option 2: Manual Testing with Integration Scripts

```bash
# 1. Test Textract Processor only
python3 scripts/test_textract_integration.py \
  trial-enrollment-protocols-123456789 \
  NCT12345678.pdf

# 2. Test Section Classifier (uses output from step 1)
python3 scripts/test_section_classifier_integration.py \
  textract_results_NCT12345678.json

# 3. Test Full Orchestration (uses output from step 1)
python3 scripts/test_protocol_orchestrator_integration.py \
  textract_results_NCT12345678.json

# 4. Test Cache Retrieval
python3 scripts/test_protocol_orchestrator_integration.py \
  --trial-id NCT12345678 \
  --cache-only
```

## 👀 Where to See the Output

### 1. **DynamoDB - Final Structured Criteria**

**Table:** `CriteriaCacheTable`

```bash
# View stored results
TABLE_NAME="TrialEnrollmentAgentStack-CriteriaCacheTable-XXXXX"

aws dynamodb get-item \
  --table-name ${TABLE_NAME} \
  --key '{"trial_id": {"S": "NCT12345678"}}'
```

**What you'll see:**
```json
{
  "Item": {
    "trial_id": {"S": "NCT12345678"},
    "timestamp": {"S": "2025-10-11T12:34:56.789Z"},
    "inclusion_criteria": {
      "L": [
        {"S": "Age >= 18 years"},
        {"S": "Diagnosed with Type 2 Diabetes"},
        {"S": "HbA1c between 7% and 10%"}
      ]
    },
    "exclusion_criteria": {
      "L": [
        {"S": "Pregnant or breastfeeding"},
        {"S": "History of diabetic ketoacidosis"}
      ]
    },
    "parsed_criteria": {
      "L": [
        {
          "M": {
            "type": {"S": "inclusion"},
            "category": {"S": "demographics"},
            "description": {"S": "Age >= 18 years"},
            "attribute": {"S": "age"},
            "operator": {"S": "greater_than"},
            "value": {"N": "18"},
            "fhir_resource": {"S": "Patient"}
          }
        }
      ]
    },
    "metadata": {
      "M": {
        "total_criteria": {"N": "15"},
        "inclusion_count": {"N": "8"},
        "exclusion_count": {"N": "7"},
        "overall_confidence": {"N": "0.89"}
      }
    }
  }
}
```

### 2. **CloudWatch Logs - Processing Details**

**View Textract Processor logs:**
```bash
aws logs tail /aws/lambda/TrialEnrollment-TextractProcessor --follow
```

**View Section Classifier logs:**
```bash
aws logs tail /aws/lambda/TrialEnrollment-SectionClassifier --follow
```

**View Protocol Orchestrator logs:**
```bash
aws logs tail /aws/lambda/TrialEnrollment-ProtocolOrchestrator --follow
```

**What you'll see:**
- Textract job IDs and status
- Number of pages processed
- Query answers extracted
- Tables found
- Criteria extracted (count and preview)
- Confidence scores
- Processing times
- Any errors or warnings

### 3. **Lambda Console - Execution History**

Go to AWS Console → Lambda:
- `TrialEnrollment-TextractProcessor`
- `TrialEnrollment-ProtocolOrchestrator`
- `TrialEnrollment-SectionClassifier`

Click **Monitor** tab → **Recent invocations** to see:
- Execution duration
- Memory used
- Success/failure status
- Logs

### 4. **API Gateway - Test Endpoints**

```bash
# Get API endpoint from CDK output
API_ENDPOINT="https://xxxxx.execute-api.us-east-1.amazonaws.com/prod"

# Test parse-criteria API directly
curl -X POST ${API_ENDPOINT}/parse-criteria \
  -H 'Content-Type: application/json' \
  -d '{
    "trial_id": "NCT12345678",
    "criteria_text": "Inclusion Criteria:\n- Age >= 18 years\n- Type 2 Diabetes"
  }'

# Test check-criteria API with a patient
curl -X POST ${API_ENDPOINT}/check-criteria \
  -H 'Content-Type: application/json' \
  -d '{
    "patient_id": "patient-123",
    "criteria": [
      {
        "type": "inclusion",
        "category": "demographics",
        "description": "Age >= 18 years",
        "attribute": "age",
        "operator": "greater_than",
        "value": 18,
        "fhir_resource": "Patient",
        "fhir_path": "Patient.birthDate"
      }
    ]
  }'
```

## 📊 Viewing the Complete Pipeline Flow

### Real-time Monitoring

```bash
# Terminal 1: Watch Textract Processor
aws logs tail /aws/lambda/TrialEnrollment-TextractProcessor --follow --format short

# Terminal 2: Watch Protocol Orchestrator
aws logs tail /aws/lambda/TrialEnrollment-ProtocolOrchestrator --follow --format short

# Terminal 3: Watch Section Classifier
aws logs tail /aws/lambda/TrialEnrollment-SectionClassifier --follow --format short

# Then upload a PDF
aws s3 cp your-protocol.pdf s3://${BUCKET_NAME}/
```

### Query Final Results from DynamoDB

```bash
# Scan all processed protocols
aws dynamodb scan \
  --table-name ${TABLE_NAME} \
  --output json | jq '.Items[] | {trial_id, inclusion_count: .metadata.M.inclusion_count, confidence: .metadata.M.overall_confidence}'
```

## 🔍 Example End-to-End Output

### 1. Upload PDF
```bash
$ aws s3 cp NCT05123456.pdf s3://trial-enrollment-protocols-123456789/
upload: ./NCT05123456.pdf to s3://trial-enrollment-protocols-123456789/NCT05123456.pdf
```

### 2. CloudWatch Logs Show Processing
```
[Textract Processor] Starting Textract job for s3://trial-enrollment-protocols-123456789/NCT05123456.pdf
[Textract Processor] Textract job started: abc123-def456-ghi789
[Textract Processor] Textract job abc123 status: IN_PROGRESS (elapsed: 5.2s)
[Textract Processor] Textract job abc123 status: IN_PROGRESS (elapsed: 10.5s)
[Textract Processor] Textract job abc123 status: SUCCEEDED (elapsed: 15.8s)
[Textract Processor] Extracted 2 query answers, 3 tables
[Textract Processor] Textract processing completed: 42 pages, confidence=0.92
[Textract Processor] Triggering Protocol Orchestrator for trial NCT05123456

[Protocol Orchestrator] Starting protocol orchestration for trial: NCT05123456
[Protocol Orchestrator] Step 1/3: Extracting criteria with Section Classifier
[Section Classifier] Extracted 12 inclusion + 8 exclusion criteria (confidence: 91%)
[Protocol Orchestrator] Step 2/3: Parsing criteria with parse-criteria API
[Parse-Criteria API] Parsed 20 criteria successfully
[Protocol Orchestrator] Step 3/3: Storing results in DynamoDB
[Protocol Orchestrator] Protocol orchestration completed for trial NCT05123456 in 23.45s
```

### 3. Query DynamoDB for Results
```json
{
  "trial_id": "NCT05123456",
  "inclusion_criteria": [
    "Age >= 18 years",
    "Diagnosed with Type 2 Diabetes Mellitus",
    "HbA1c between 7.0% and 10.5%",
    "BMI >= 25 kg/m2",
    "Able to provide informed consent"
  ],
  "exclusion_criteria": [
    "Type 1 Diabetes",
    "Pregnant or breastfeeding",
    "History of diabetic ketoacidosis",
    "Active malignancy"
  ],
  "metadata": {
    "total_criteria": 20,
    "inclusion_count": 12,
    "exclusion_count": 8,
    "overall_confidence": 0.91
  }
}
```

## 🎮 Testing Patient Eligibility

Once a protocol is processed, you can check patient eligibility:

```bash
# Get the parsed criteria from DynamoDB
CRITERIA=$(aws dynamodb get-item \
  --table-name ${TABLE_NAME} \
  --key '{"trial_id": {"S": "NCT05123456"}}' \
  --output json | jq '.Item.parsed_criteria.L')

# Check if a patient is eligible
curl -X POST ${API_ENDPOINT}/check-criteria \
  -H 'Content-Type: application/json' \
  -d "{
    \"patient_id\": \"patient-12345\",
    \"criteria\": ${CRITERIA}
  }"
```

**Response:**
```json
{
  "patient_id": "patient-12345",
  "eligible": true,
  "summary": {
    "total_criteria": 20,
    "inclusion_met": 12,
    "exclusion_violated": 0,
    "failed_criteria_count": 0
  }
}
```

## 🐛 Troubleshooting

### Check Lambda Invocations
```bash
# Check if Textract Processor was triggered
aws lambda list-invocations \
  --function-name TrialEnrollment-TextractProcessor \
  --max-items 10

# Check Protocol Orchestrator invocations
aws lambda get-function \
  --function-name TrialEnrollment-ProtocolOrchestrator
```

### Check S3 Event Notifications
```bash
# Verify S3 trigger is configured
aws s3api get-bucket-notification-configuration \
  --bucket ${BUCKET_NAME}
```

### View Error Logs
```bash
# Filter for errors
aws logs filter-log-events \
  --log-group-name /aws/lambda/TrialEnrollment-TextractProcessor \
  --filter-pattern "ERROR"
```

## 💰 Cost Monitoring

Track costs in CloudWatch:

```bash
# View Textract usage
aws cloudwatch get-metric-statistics \
  --namespace AWS/Textract \
  --metric-name PageCount \
  --start-time $(date -u -d '1 day ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 3600 \
  --statistics Sum
```

## 🎯 Quick Test Checklist

- [ ] Deploy infrastructure: `cd infrastructure && cdk deploy`
- [ ] Note bucket name from outputs
- [ ] Upload test PDF: `aws s3 cp test.pdf s3://${BUCKET_NAME}/`
- [ ] Wait 2-5 minutes
- [ ] Check DynamoDB: `aws dynamodb get-item --table-name ${TABLE_NAME} --key '{"trial_id": {"S": "test"}}'`
- [ ] Verify criteria extracted
- [ ] Test patient matching with check-criteria API

## 📝 Summary

**The complete pipeline is now automatic!**

1. **Upload PDF** → S3 bucket
2. **Wait** → 2-5 minutes (depending on PDF size)
3. **Query** → DynamoDB for structured criteria
4. **Use** → Check-criteria API to match patients

**All outputs are in:**
- DynamoDB: Structured criteria and metadata
- CloudWatch Logs: Detailed processing logs
- Lambda Console: Execution history and metrics
