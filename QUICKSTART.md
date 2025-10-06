# Quickstart Guide

Get the Trial Enrollment Agent running in 15 minutes.

## Prerequisites

- AWS Account with Bedrock access
- Python 3.11+
- AWS CLI configured
- 15 minutes

## 1. Clone & Setup (2 min)

```bash
git clone <repo-url>
cd aws-trial-enrollment-agent
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 2. Enable Bedrock Access (1 min)

```bash
# Via AWS Console:
# 1. Go to Amazon Bedrock
# 2. Click "Model Access" in left sidebar
# 3. Click "Request Model Access"
# 4. Select "Anthropic Claude 3 Sonnet"
# 5. Click "Request Access"
```

## 3. Deploy Infrastructure (5 min)

```bash
cd infrastructure
pip install -r requirements.txt
cdk bootstrap  # First time only
cdk deploy
```

**Save the outputs!** You'll need the API endpoint and Lambda function names.

## 4. Setup FHIR Server (2 min)

**Option A - Docker (Recommended for demo):**
```bash
docker run -d -p 8080:8080 hapiproject/hapi:latest
```

**Option B - Use public test server:**
```bash
export FHIR_ENDPOINT=http://hapi.fhir.org/baseR4
```

## 5. Load Sample Patients (2 min)

```bash
cd ..
python scripts/load_synthea_data.py
# Press 'y' to upload when prompted
```

This creates 3 test patients:
- `patient-001`: Eligible (45yo, diabetes, HbA1c 8%)
- `patient-002`: Not eligible (14yo, too young)
- `patient-003`: Not eligible (has CKD exclusion)

## 6. Test the Agent (3 min)

### Quick Test via API

```bash
export API_URL=<your-api-gateway-url-from-step-3>

# Test criteria parsing
curl -X POST $API_URL/parse-criteria \
  -H "Content-Type: application/json" \
  -d '{
    "criteria_text": "Patients must be 18-65 years old with Type 2 Diabetes",
    "trial_id": "quickstart-test"
  }' | jq
```

### Run Full Demo

```bash
# Set environment variables
export CRITERIA_PARSER_FUNCTION=TrialEnrollment-CriteriaParser
export FHIR_SEARCH_FUNCTION=TrialEnrollment-FHIRSearch
export AWS_REGION=us-east-1
export FHIR_ENDPOINT=http://localhost:8080/fhir

# Run demo
python scripts/demo.py
```

## Expected Output

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                    TRIAL ENROLLMENT AGENT DEMO                               ║
╚══════════════════════════════════════════════════════════════════════════════╝

================================================================================
 SCENARIO 1: Eligible Patient
================================================================================

[Agent] Parsing eligibility criteria for DIABETES-TRIAL-2024...
[Agent] Parsed 5 criteria
[Agent] Checking patient patient-001 against criteria...
[Agent] Patient patient-001 eligibility: ELIGIBLE
[Agent] Generating detailed explanation...

================================================================================
 ELIGIBILITY RESULT
================================================================================

Trial ID: DIABETES-TRIAL-2024
Patient ID: patient-001
Eligible: ✓ YES

Summary:
  - Total Criteria: 5
  - Inclusion Met: 3
  - Exclusions Violated: 0

Explanation:
The patient meets all eligibility criteria for this diabetes trial. They are
45 years old (within the 18-65 range), have a confirmed diagnosis of Type 2
Diabetes Mellitus, and their most recent HbA1c of 8.0% falls within the target
range of 7-10%. No exclusion criteria were identified...
```

## Troubleshooting

### "Bedrock Access Denied"
→ Go to AWS Console > Bedrock > Model Access and request access to Claude 3

### "FHIR Connection Failed"
→ Check Docker is running: `docker ps`
→ Or use public server: `export FHIR_ENDPOINT=http://hapi.fhir.org/baseR4`

### "Lambda Function Not Found"
→ Check CDK deployed successfully: `cdk deploy --require-approval never`
→ Verify function names: `aws lambda list-functions | grep TrialEnrollment`

### "No patients found"
→ Re-run data loading: `python scripts/load_synthea_data.py`
→ Verify in FHIR: `curl http://localhost:8080/fhir/Patient/patient-001`

## What's Next?

1. **Read the Docs**: Check `/docs` for detailed architecture
2. **Customize**: Modify criteria parser prompts in `src/lambda/criteria_parser/handler.py`
3. **Extend**: Add more FHIR resource types in `src/lambda/fhir_search/handler.py`
4. **Deploy to Prod**: See `docs/deployment_guide.md` for production setup

## Quick Reference

### Useful Commands

```bash
# View Lambda logs
aws logs tail /aws/lambda/TrialEnrollment-CriteriaParser --follow

# Test Lambda directly
aws lambda invoke \
  --function-name TrialEnrollment-CriteriaParser \
  --payload '{"criteria_text":"Age 18-65"}' \
  response.json

# Run tests
pytest tests/ -v

# Destroy stack (cleanup)
cd infrastructure && cdk destroy
```

### Key Files

| File | Purpose |
|------|---------|
| `README.md` | Main documentation |
| `src/agent/trial_enrollment_agent.py` | Agent orchestrator |
| `infrastructure/app.py` | CDK stack |
| `scripts/demo.py` | Demo walkthrough |
| `docs/deployment_guide.md` | Full deployment instructions |

## Need Help?

- 📖 Read: `docs/deployment_guide.md`
- 🏗️ Architecture: `docs/architecture_overview.md`
- 🔒 Security: `docs/guardrails_and_compliance.md`
- 🧪 Testing: `pytest tests/ -v`

## Success Criteria

You've successfully deployed if:
- [x] CDK deploy completed without errors
- [x] Sample patients loaded into FHIR server
- [x] Demo script runs and shows eligibility results
- [x] API endpoints return 200 OK

**Congratulations!** 🎉 You now have a working AI agent for clinical trial enrollment.

---

**Time to Complete**: ~15 minutes
**Difficulty**: Easy
**Cost**: <$1 for testing (pay-as-you-go)
