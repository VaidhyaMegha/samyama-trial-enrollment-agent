# Postman Test Collections

This directory contains comprehensive API test collections for the AWS Trial Enrollment Agent.

## Collections

### 1. `complex_criteria_tests.json`
**Purpose:** Test complex logical criteria with AND/OR/NOT operators

**Test Categories:**
- Simple OR logic (2 conditions)
- Simple AND logic (2 conditions)
- Nested AND/OR (2 levels)
- Triple nested logic (3+ levels)
- Multiple OR groups
- Real-world clinical trial scenarios

**Total Tests:** 15 requests

## Import Instructions

### Using Postman Desktop App:
1. Open Postman
2. Click **Import** button (top left)
3. Select **File** tab
4. Choose `complex_criteria_tests.json`
5. Click **Import**

### Using Postman Web:
1. Go to [web.postman.co](https://web.postman.co)
2. Click **Import** in workspace
3. Upload `complex_criteria_tests.json`

## Test Execution Order

### Phase 1: Parsing Tests (Requests 1-8, 12-15)
Test the criteria parser with various complex logical structures.

**Expected Results:**
- Each returns a nested JSON structure with `logic_operator` field
- Parser identifies AND, OR operators correctly
- Nested structures properly formatted

### Phase 2: Evaluation Tests (Requests 9-11)
Test the FHIR search evaluator with actual patient data.

**Prerequisites:**
- Patients must exist in HealthLake:
  - `diabetes-patient-001` (has Type 2 Diabetes, ECOG=1)
  - `ecog-0-patient` (ECOG=0)
  - `ecog-3-patient` (ECOG=3)

**Expected Results:**
- Request 9: Patient eligible (has diabetes AND ECOG 0-1)
- Request 10: ECOG criterion met (ECOG=0 is within 0-1)
- Request 11: ECOG criterion NOT met (ECOG=3 is outside 0-1)

## Key Test Scenarios

### Test 3: Basic Nested AND/OR ⭐
```
Criteria: "(Type 2 Diabetes OR Pre-diabetes) AND ECOG 0-1"
Structure:
  AND (top-level)
    ├── OR (nested)
    │   ├── Type 2 Diabetes
    │   └── Pre-diabetes
    └── ECOG 0-1
```

### Test 4: Complex Oncology ⭐⭐
```
Criteria: "(Breast OR Ovarian) AND (Stage II OR III) AND ECOG 0-1"
Structure:
  AND (top-level)
    ├── OR (cancer type)
    ├── OR (stage)
    └── ECOG 0-1
```

### Test 5: Triple Nested ⭐⭐⭐
```
Criteria: "((Diabetes OR Pre-diabetes) AND Age 40+) OR (Hypertension AND Age 50+)"
Structure:
  OR (top-level)
    ├── AND
    │   ├── OR (diabetes conditions)
    │   └── Age 40+
    └── AND
        ├── Hypertension
        └── Age 50+
```

### Test 12: Four-Level Nesting ⭐⭐⭐⭐
Most complex test - validates maximum nesting depth handling.

## Environment Variables

You may want to set these as Postman environment variables:

| Variable | Value |
|----------|-------|
| `base_url` | `https://gt7dlyqj78.execute-api.us-east-1.amazonaws.com` |
| `stage` | `prod` |
| `patient_id_diabetes` | `diabetes-patient-001` |
| `patient_id_ecog_0` | `ecog-0-patient` |
| `patient_id_ecog_3` | `ecog-3-patient` |

Then use: `{{base_url}}/{{stage}}/parse-criteria`

## Expected Response Times

| Operation | Target | Acceptable |
|-----------|--------|------------|
| Parse Criteria | <60s | <90s |
| Check Criteria (simple) | <2s | <5s |
| Check Criteria (complex) | <5s | <10s |

## Common Errors

### 400 Bad Request
**Cause:** Invalid JSON payload
**Fix:** Validate JSON syntax in request body

### 500 Internal Server Error
**Cause:** Lambda timeout or parsing error
**Fix:** Check CloudWatch logs for the Lambda function

### "No performance status observations found"
**Cause:** Patient doesn't have ECOG/Karnofsky observation
**Fix:** Create observation in HealthLake (see test data creation scripts)

## Validation Checks

After running tests, verify:

✅ Parser creates `logic_operator` field for complex criteria
✅ Nested structures have proper depth (no infinite recursion)
✅ Evaluator returns `sub_results` array for complex criteria
✅ Patient eligibility is correctly determined based on logical operators

## Advanced Testing

### Performance Testing
Run all parsing tests in sequence and measure total time:
- Target: <15 minutes for all 15 tests
- If slower, check Bedrock throttling or Lambda cold starts

### Load Testing
Use Postman Runner to execute:
- 10 iterations of Test 3 (basic nested)
- Monitor for cache hits (should see `cache_hit: true` after first run)

### Edge Cases to Test Manually
1. Empty criteria text → Should return error
2. Criteria with only "AND" (no sub-criteria) → Should handle gracefully
3. Maximum depth (10+ levels) → Should return depth limit error
4. Malformed parentheses → Parser should handle best-effort

## Test Data Setup

To run evaluation tests, you need test patients in HealthLake. See:
- `/tmp/create_test_patients.py` (if available)
- Or create manually via HealthLake Console

Required patients:
```json
{
  "diabetes-patient-001": {
    "conditions": ["Type 2 Diabetes"],
    "observations": [{"code": "89247-1", "value": 1}]
  },
  "ecog-0-patient": {
    "observations": [{"code": "89247-1", "value": 0}]
  },
  "ecog-3-patient": {
    "observations": [{"code": "89247-1", "value": 3}]
  }
}
```

## Troubleshooting

### Cache Issues
If parser returns stale results:
```bash
aws dynamodb delete-item \
  --table-name TrialEnrollmentAgentStack-CriteriaCacheTableFDCD8472-1QNO79RYH9M88 \
  --key '{"trial_id": {"S": "YOUR_TRIAL_ID"}}' \
  --region us-east-1
```

### Lambda Issues
Check logs:
```bash
aws logs tail /aws/lambda/TrialEnrollment-CriteriaParser --follow
aws logs tail /aws/lambda/TrialEnrollment-FHIRSearch --follow
```

## Success Criteria

✅ All 15 tests return 200 OK
✅ Parsing tests create proper nested structures
✅ Evaluation tests return correct eligibility
✅ Response times within acceptable range
✅ No internal server errors

---

**Last Updated:** October 7, 2025
**Version:** 1.0
**Status:** Production Ready
