# Architecture Overview

## System Architecture

The Trial Enrollment Agent is built on AWS serverless services with Amazon Bedrock at its core for AI-powered decision making.

```
┌────────────────────────────────────────────────────────────────┐
│                         User Layer                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │  Clinician   │  │   Research   │  │  Study       │         │
│  │  Interface   │  │  Coordinator │  │  Coordinator │         │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘         │
└─────────┼──────────────────┼──────────────────┼────────────────┘
          │                  │                  │
          └──────────────────┴──────────────────┘
                             │
                        HTTPS/TLS
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                    API Gateway Layer                             │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  Amazon API Gateway (REST API)                             │ │
│  │  - Authentication & Authorization                          │ │
│  │  - Rate Limiting & Throttling                              │ │
│  │  - Request/Response Transformation                         │ │
│  │  - CORS Configuration                                      │ │
│  └────────────┬───────────────────────────┬───────────────────┘ │
└───────────────┼───────────────────────────┼─────────────────────┘
                │                           │
      /parse-criteria              /check-criteria
                │                           │
┌───────────────▼───────────────┐  ┌────────▼──────────────────────┐
│  Criteria Parser Lambda        │  │  FHIR Search Lambda           │
│  ┌──────────────────────────┐ │  │  ┌─────────────────────────┐ │
│  │ - Receives trial criteria│ │  │  │ - Receives patient ID + │ │
│  │ - Calls Bedrock LLM      │ │  │  │   parsed criteria       │ │
│  │ - Parses to JSON         │ │  │  │ - Queries FHIR store    │ │
│  │ - Validates output       │ │  │  │ - Evaluates each        │ │
│  │ - Caches results         │ │  │  │   criterion             │ │
│  └────────────┬─────────────┘ │  │  │ - Returns eligibility   │ │
└────────────────┼───────────────┘  │  └──────────┬──────────────┘ │
                 │                  └─────────────┼────────────────┘
                 │                                │
                 │                                │
┌────────────────▼────────────────────────────────▼────────────────┐
│                    Core AWS Services                              │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │  Amazon Bedrock                                             ││
│  │  ┌───────────────────────────────────────────────────────┐ ││
│  │  │  Anthropic Claude 3 Sonnet                            │ ││
│  │  │  - Criteria parsing & interpretation                  │ ││
│  │  │  - Explanation generation                             │ ││
│  │  │  - Outreach material drafting                         │ ││
│  │  │  - Guardrails enabled (PII filtering, content safety) │ ││
│  │  └───────────────────────────────────────────────────────┘ ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                   │
│  ┌─────────────────────────┐  ┌──────────────────────────────┐ │
│  │  Amazon HealthLake      │  │  Amazon DynamoDB             │ │
│  │  (FHIR R4)              │  │                              │ │
│  │  ┌───────────────────┐  │  │  ┌────────────────────────┐ │ │
│  │  │ Patient Resources │  │  │  │ Criteria Cache         │ │ │
│  │  │ Condition         │  │  │  │ (trial_id → criteria)  │ │ │
│  │  │ Observation       │  │  │  └────────────────────────┘ │ │
│  │  │ Medication        │  │  │                              │ │
│  │  │ Procedure         │  │  │  ┌────────────────────────┐ │ │
│  │  └───────────────────┘  │  │  │ Evaluation Results     │ │ │
│  │  - HIPAA Eligible       │  │  │ (evaluation_id → data) │ │ │
│  │  - Encrypted at rest    │  │  └────────────────────────┘ │ │
│  └─────────────────────────┘  └──────────────────────────────┘ │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │  Amazon CloudWatch                                          ││
│  │  - Lambda execution logs                                    ││
│  │  - API Gateway metrics                                      ││
│  │  - Bedrock usage tracking                                   ││
│  │  - Custom metrics & alarms                                  ││
│  │  - Audit trail (tool calls, decisions)                      ││
│  └─────────────────────────────────────────────────────────────┘│
└───────────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────────┐
│                    Agent Orchestration Layer                       │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │  Trial Enrollment Agent (Python)                             │ │
│  │  ┌────────────────────────────────────────────────────────┐ │ │
│  │  │  Workflow:                                             │ │ │
│  │  │  1. Receive: patient_id + trial_criteria               │ │ │
│  │  │  2. Parse criteria → tool: parse_criteria              │ │ │
│  │  │  3. For each criterion:                                │ │ │
│  │  │     - Check patient data → tool: check_criteria        │ │ │
│  │  │     - Collect results                                  │ │ │
│  │  │  4. Determine eligibility (logic)                      │ │ │
│  │  │  5. Generate explanation → Bedrock LLM                 │ │ │
│  │  │  6. (Optional) Generate outreach → Bedrock LLM         │ │ │
│  │  │  7. Return structured result                           │ │ │
│  │  └────────────────────────────────────────────────────────┘ │ │
│  └──────────────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. API Gateway
- **Purpose**: Public-facing REST API endpoint
- **Security**:
  - API keys for authentication (production: Cognito OAuth)
  - Rate limiting (100 req/sec)
  - CORS enabled for web clients
- **Endpoints**:
  - `POST /parse-criteria` → Criteria Parser Lambda
  - `POST /check-criteria` → FHIR Search Lambda
  - `GET /health` → Health check

### 2. Criteria Parser Lambda
- **Runtime**: Python 3.11
- **Memory**: 512 MB
- **Timeout**: 60 seconds
- **Function**:
  - Receives free-text eligibility criteria
  - Uses Bedrock Claude to parse into structured JSON
  - Validates output schema
  - Caches in DynamoDB for reuse
- **Output Schema**:
  ```json
  {
    "type": "inclusion|exclusion",
    "category": "demographics|condition|lab_value|...",
    "description": "...",
    "attribute": "...",
    "operator": "between|equals|contains|...",
    "value": "...",
    "fhir_resource": "Patient|Observation|Condition|...",
    "fhir_path": "..."
  }
  ```

### 3. FHIR Search Lambda
- **Runtime**: Python 3.11
- **Memory**: 512 MB
- **Timeout**: 60 seconds
- **Function**:
  - Receives patient_id and parsed criteria
  - Queries FHIR store for relevant resources
  - Evaluates each criterion against patient data
  - Returns pass/fail for each with evidence
- **FHIR Resources Queried**:
  - `Patient` (demographics)
  - `Condition` (diagnoses)
  - `Observation` (lab values, vitals)
  - `MedicationStatement` (current medications)
  - `Procedure` (past procedures)

### 4. Amazon Bedrock
- **Model**: Anthropic Claude 3 Sonnet
- **Use Cases**:
  1. **Criteria Parsing**: Low temp (0.1), few-shot prompting
  2. **Explanation Generation**: Medium temp (0.3), chain-of-thought
  3. **Outreach Drafting**: Medium temp (0.3), professional tone
- **Guardrails**:
  - PII detection and filtering
  - Content safety filters
  - Medical domain vocabulary
  - Output validation

### 5. Amazon HealthLake
- **Standard**: FHIR R4
- **Data**: Synthetic patients (Synthea)
- **Compliance**: HIPAA-eligible
- **Operations**:
  - Read individual resources
  - Search with parameters
  - Bundle operations for batch loading

### 6. DynamoDB
**Criteria Cache Table**:
- Partition Key: `trial_id`
- Purpose: Cache parsed criteria to avoid re-parsing
- TTL: 30 days

**Evaluation Results Table**:
- Partition Key: `evaluation_id`
- Sort Key: `timestamp`
- Purpose: Audit trail of all evaluations
- TTL: 90 days

### 7. CloudWatch
- **Logs**: All Lambda execution logs
- **Metrics**:
  - Lambda invocations, duration, errors
  - API Gateway requests, latency, 4xx/5xx
  - Bedrock token usage
- **Alarms**:
  - Error rate > 5%
  - Lambda timeout threshold
  - Cost alerts

## Data Flow

### Patient Eligibility Evaluation Flow

```
1. User Request
   ↓
   [API Gateway] POST /evaluate
   ↓
2. [Agent] Receives request
   ↓
3. [Agent] → Parse Criteria Tool
   ↓
   [Criteria Parser Lambda] → Bedrock
   ↓
   Returns: structured_criteria[]
   ↓
4. [Agent] → For each criterion
   ↓
   [FHIR Search Lambda] → HealthLake
   ↓
   Returns: criterion_result{met, evidence}
   ↓
5. [Agent] → Evaluate all results
   ↓
   Logic: eligible = all_inclusions_met AND no_exclusions_met
   ↓
6. [Agent] → Generate Explanation
   ↓
   [Bedrock] → Natural language summary
   ↓
7. [Agent] → Return Result
   ↓
   Response: {eligible, explanation, detailed_results}
   ↓
   [API Gateway] → User
```

## Security Architecture

### Defense in Depth

```
┌─────────────────────────────────────────────────────────────┐
│ Layer 1: Network Security                                   │
│ - VPC with private subnets (production)                     │
│ - VPC Endpoints for AWS services                            │
│ - No direct internet access from Lambda                     │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Layer 2: API Security                                       │
│ - API Gateway with API keys/Cognito                         │
│ - Rate limiting & throttling                                │
│ - WAF (optional) for DDoS protection                        │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Layer 3: Application Security                               │
│ - IAM roles with least privilege                            │
│ - Input validation & sanitization                           │
│ - Output schema validation                                  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Layer 4: Data Security                                      │
│ - Encryption at rest (DynamoDB, HealthLake)                 │
│ - Encryption in transit (TLS 1.2+)                          │
│ - No PHI in logs                                            │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Layer 5: AI Safety                                          │
│ - Bedrock guardrails (PII, content filtering)               │
│ - Low temperature for factual tasks                         │
│ - Human-in-the-loop requirements                            │
└─────────────────────────────────────────────────────────────┘
```

## Scalability

### Horizontal Scaling
- **Lambda**: Auto-scales to 1000 concurrent executions
- **API Gateway**: Handles 10,000 req/sec (regional)
- **DynamoDB**: On-demand scaling, unlimited throughput
- **HealthLake**: Managed, scales automatically

### Performance Optimizations
1. **Caching**: DynamoDB for parsed criteria
2. **Batch Processing**: Evaluate multiple criteria in single FHIR query
3. **Parallel Execution**: Concurrent Lambda invocations
4. **Connection Pooling**: Reuse FHIR connections

### Cost Optimization
- **Lambda**: Right-sized memory allocation
- **DynamoDB**: On-demand billing
- **Bedrock**: Efficient prompting to minimize tokens
- **CloudWatch**: Log retention policies

## Disaster Recovery

### Backup Strategy
- **DynamoDB**: Point-in-time recovery enabled
- **HealthLake**: Automatic backups
- **Configuration**: Infrastructure as Code (CDK)

### Recovery Objectives
- **RTO** (Recovery Time Objective): 1 hour
- **RPO** (Recovery Point Objective): 5 minutes

### Failure Scenarios
1. **Lambda Failure**: Automatic retry, fallback logic
2. **Bedrock Throttling**: Exponential backoff, queue requests
3. **FHIR Timeout**: Cached results if available
4. **Region Failure**: Cross-region replication (optional)

## Monitoring & Observability

### Key Metrics
1. **Functional**:
   - Eligibility evaluations per day
   - Average criteria per trial
   - Patient match rate

2. **Performance**:
   - End-to-end latency (target: <5s)
   - Lambda cold start frequency
   - FHIR query duration

3. **Business**:
   - Time saved vs manual screening
   - Accuracy rate (vs human review)
   - Cost per evaluation

### Dashboards
- Real-time operations dashboard
- Weekly business metrics
- Monthly cost analysis

## Future Enhancements

### Near-term (Next 3 months)
1. **Advanced Criteria**: Complex logical expressions (AND/OR)
2. **Multi-site Support**: Federated FHIR queries
3. **Patient Matching Score**: ML-based propensity model
4. **Web UI**: Clinician-friendly interface

### Long-term (6-12 months)
1. **Real-time Monitoring**: EventBridge for new patient data
2. **Predictive Analytics**: SageMaker for enrollment forecasting
3. **Integration**: Direct EHR integration (Epic, Cerner)
4. **Regulatory**: FDA/IRB compliance tooling

---

**Document Version**: 1.0
**Last Updated**: 2024-10-05
**Review Schedule**: Quarterly
