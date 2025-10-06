# Guardrails & Compliance

## Overview

The Trial Enrollment Agent implements multiple layers of security, privacy, and safety controls to ensure responsible AI use in healthcare settings.

## Security Guardrails

### 1. AWS Identity and Access Management (IAM)

**Principle of Least Privilege:**
- Each Lambda function has a dedicated IAM role with minimal permissions
- Bedrock access is scoped to specific model ARNs only
- HealthLake access is read-only for query operations
- DynamoDB access is restricted to specific tables

**Example IAM Policy:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel"
      ],
      "Resource": [
        "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "healthlake:ReadResource",
        "healthlake:SearchWithGet"
      ],
      "Resource": "arn:aws:healthlake:us-east-1:*:datastore/*"
    }
  ]
}
```

### 2. Data Encryption

**At Rest:**
- DynamoDB tables use AWS-managed encryption
- HealthLake data is encrypted by default
- Lambda environment variables can use KMS encryption

**In Transit:**
- All API calls use HTTPS/TLS 1.2+
- VPC endpoints for private AWS service access
- No PHI transmitted in plain text

### 3. Network Isolation

**VPC Configuration (Production):**
- Lambda functions deployed in private subnets
- HealthLake accessible via VPC endpoint
- No direct internet access from processing functions
- API Gateway as controlled entry point

### 4. Audit Logging

**CloudWatch Integration:**
- All Lambda invocations logged with request/response metadata
- Agent actions tracked with correlation IDs
- Tool usage audited with input/output hashes
- Retention period: 90 days minimum

**Example Log Entry:**
```json
{
  "timestamp": "2024-10-05T14:30:00Z",
  "correlation_id": "abc-123",
  "agent_action": "check_criteria",
  "patient_id_hash": "sha256:...",
  "trial_id": "NCT12345678",
  "result": "eligible",
  "criteria_checked": 5
}
```

## Privacy & HIPAA Compliance

### 1. Data Minimization

**Only Required Data:**
- Agent queries only specific FHIR resources needed for criteria
- No bulk patient data exports
- Results contain only de-identified summaries

**PHI Handling:**
- Patient names not included in agent outputs
- Only patient IDs used for references
- Explanations focus on clinical data, not identifiers

### 2. HIPAA-Eligible Services

**Service Selection:**
- Amazon HealthLake: HIPAA-eligible, BAA available
- Amazon Bedrock: HIPAA-eligible, no PHI sent to training
- DynamoDB: HIPAA-eligible with encryption
- CloudWatch Logs: PHI-filtered before logging

### 3. Synthetic Data for Development

**Testing Requirements:**
- All development uses Synthea-generated synthetic patients
- No real patient data in version control
- Demo scripts include disclaimers
- Test data clearly marked as synthetic

## AI Safety Guardrails

### 1. Bedrock Guardrails

**Content Filtering:**
- Enable Bedrock guardrails for all LLM calls
- Filter for PII detection
- Block toxic or harmful content
- Custom vocabulary filters for sensitive terms

**Configuration:**
```python
guardrail_config = {
    "guardrailIdentifier": "trial-enrollment-guardrail",
    "guardrailVersion": "1",
    "trace": "enabled"
}
```

### 2. Output Validation

**Structured Outputs:**
- All LLM outputs validated against schemas
- Criteria parsing results must match expected format
- Numeric values bounds-checked
- Enum values validated

**Hallucination Mitigation:**
- Low temperature (0.1-0.3) for factual tasks
- Grounding in source criteria text
- Evidence citations required
- Human review flags for uncertainty

### 3. Decision Boundaries

**Agent Limitations:**
- Agent identifies candidates only
- Cannot make final enrollment decisions
- All results marked "requires human review"
- No automated patient contact

**Required Disclaimers:**
```
⚠️ PRELIMINARY SCREENING ONLY
This assessment is based on available EHR data and requires:
1. Physician review and confirmation
2. Complete medical record review
3. Patient consent before enrollment
4. IRB-approved screening procedures
```

## Operational Guardrails

### 1. Rate Limiting

**API Gateway Throttling:**
- 100 requests/second per endpoint
- 10,000 requests/day per API key
- Burst capacity: 200 requests

### 2. Cost Controls

**Resource Limits:**
- Lambda timeout: 60 seconds max
- Lambda memory: 512MB (right-sized)
- DynamoDB on-demand (auto-scaling)
- Bedrock quota monitoring with alarms

### 3. Error Handling

**Graceful Degradation:**
- Retry logic with exponential backoff
- Circuit breakers for external services
- Fallback to cached data when available
- Clear error messages to users

### 4. Monitoring & Alerting

**CloudWatch Alarms:**
- Lambda error rate > 5%
- API Gateway 4xx/5xx > threshold
- Bedrock throttling events
- HealthLake query timeouts

## Compliance Documentation

### 1. Data Flow Diagram

```
┌─────────────────┐
│  User/Clinician │
└────────┬────────┘
         │ HTTPS/TLS
         v
    ┌────────────┐
    │API Gateway │ (WAF, Auth)
    └────┬───────┘
         │ Private
         v
    ┌──────────────┐
    │Lambda (VPC)  │ (IAM, Encryption)
    └───┬──────┬───┘
        │      │
        v      v
   ┌────────┐ ┌───────────┐
   │Bedrock │ │HealthLake │ (HIPAA-eligible)
   └────────┘ └───────────┘
```

### 2. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| PHI exposure | Low | High | Encryption, access controls, audit logs |
| LLM hallucination | Medium | Medium | Low temperature, validation, human review |
| Unauthorized access | Low | High | IAM, API keys, VPC isolation |
| Service outage | Medium | Low | Retry logic, fallbacks, monitoring |

### 3. Human-in-the-Loop Requirements

**Mandatory Review Points:**
1. Criteria parsing accuracy verification
2. Eligibility decision confirmation
3. Patient outreach approval
4. Enrollment decision (never automated)

### 4. Audit Trail

**Required Documentation:**
- Date/time of agent run
- User who initiated evaluation
- Criteria version used
- Patient data sources queried
- All tool calls and results
- Final decision rationale

## Responsible AI Principles

### 1. Transparency
- Clear explanations for all decisions
- Criterion-by-criterion reasoning
- Evidence from patient records cited

### 2. Accountability
- All actions logged and auditable
- Human responsibility for final decisions
- Clear escalation paths for issues

### 3. Fairness
- No bias in criteria interpretation
- Consistent evaluation across patients
- Regular review for disparate impact

### 4. Privacy
- Data minimization
- Purpose limitation
- Retention policies enforced

## Incident Response

**In Case of Security Event:**
1. Immediately revoke API keys/credentials
2. Review CloudWatch logs for anomalies
3. Assess scope of potential PHI exposure
4. Notify security team and compliance officer
5. Document incident per HIPAA requirements

**In Case of AI Safety Issue:**
1. Halt agent for affected use case
2. Review recent evaluations for impact
3. Update prompts/guardrails as needed
4. Re-validate with test scenarios
5. Document and learn from incident

## Continuous Improvement

**Regular Reviews:**
- Monthly security posture assessment
- Quarterly guardrail effectiveness review
- Annual compliance audit
- Continuous monitoring of agent outputs

---

**Last Updated:** 2024-10-05
**Review Cycle:** Quarterly
**Owner:** Security & Compliance Team
