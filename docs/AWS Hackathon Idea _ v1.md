Love it—this hackathon is a great fit, and healthcare/clinical trials is absolutely in-scope. Here’s a concrete concept that’s ambitious **but demo-able** in hackathon time and maps cleanly to AWS’s judging \+ required tech.

# **Concept: Trial Enrollment & Eligibility Agent**

**One-line:** An autonomous agent that ingests a trial protocol, converts eligibility criteria into computable checks, and then searches a (synthetic) FHIR patient store to surface **matched, explainable candidate cohorts**—with draft outreach/tasks for study coordinators.

## **Why this wins**

* **Impact (value 20%)**: Enrollment is the \#1 bottleneck; even small gains are huge for timelines/cost.

* **Technical execution (50%)**: Heavy use of **Bedrock AgentCore (Gateway, Identity, Memory)** for tool use \+ multi-step planning; Bedrock LLM for reasoning; optional SageMaker model for risk/propensity scoring; auditable actions.

* **Special award shot**: “Best Bedrock AgentCore Implementation.”

## **What the demo shows (3–4 minutes)**

1. Upload or point to a **trial protocol PDF / CT.gov record**.

2. Agent extracts & normalizes **inclusion/exclusion** into JSON logic (e.g., age ≥ 18, HbA1c 7–10, no CKD stage 4).

3. Agent queries a **FHIR store** of synthetic EHRs, returns a ranked list of candidates with **per-patient explanations** (which criteria passed/failed).

4. One click to:

   * auto-draft **physician outreach** or **pre-screen questionnaire**,

   * log an **EHR note** or task (mocked),

   * generate **IRB-friendly screening worksheet**.

# **Thin-slice build (hackathon scope)**

* **Data**: Use **AWS HealthLake** (or a lightweight HAPI-FHIR container) preloaded with synthetic patients (Synthea).

* **Protocol source**: Start with 1 oncology or diabetes trial; parse from CT.gov JSON \+ a small PDF snippet for unstructured criteria.

* **Rules**: Convert criteria to a simple JSON rules DSL (range checks, ICD codes, meds, labs); store alongside the trial.

* **Explainers**: For each candidate, show pass/fail per criterion \+ short natural-language rationale.

* **Safety/PII**: Keep everything in a private VPC; only HIPAA-eligible services; no real patient data.

# **AWS architecture (minimal, judge-friendly)**

* **Amazon Bedrock AgentCore**

  * **Gateway tools**:

    * `get_trial(protocol_id)` (CT.gov/parsed JSON)

    * `parse_criteria(document_url)` (Lambda)

    * `fhir_search(criteria_json)` (HealthLake/HAPI-FHIR via API Gateway)

    * `draft_outreach(patient_id, clinician_id)` (Lambda)

  * **Identity** for least-privilege access to the FHIR store

  * **Memory** to persist trial context across steps (criteria ↔ results)

* **LLM on Bedrock** (Claude/Titan) for: criteria extraction, reasoning, explanation, doc drafting.

* **Amazon SageMaker (optional stretch)**: small XGBoost/TabNet model for **enrollment propensity** given structured features.

* **EventBridge (stretch)**: watch for new labs/diagnoses → re-evaluate matches.

* **DynamoDB**: cache criteria JSON \+ candidate snapshots.

* **CloudWatch/AgentCore observability**: step-by-step audit trail.

# **Scoring checklist → deliverables**

* **Functionality**: Working end-to-end agent run on a sample protocol \+ 1–2 synthetic cohorts.

* **Architecture**: 1 diagram (PNG) \+ README (data flow, auth, HIPAA-eligible choices).

* **Presentation**: 3–4 min screen-recorded demo with narrator script.

* **Docs**: Brief **limitations & risk** page (hallucination guardrails, manual review points).

* **Repo**: IaC snippets (CDK/Terraform light) \+ “seed” script to load Synthea bundles.

# **Guardrails & compliance (what judges care about)**

* Don’t assert diagnoses—**only surface candidates** with explanations and a “requires human confirmation” banner.

* Restrict all tools with allow-lists (AgentCore Gateway).

* Log every tool call \+ input/output hashes for audit.

# **Fast build plan (5 work units)**

1. **Data & FHIR**: stand up HealthLake or HAPI-FHIR; load Synthea; validate a few search queries.

2. **Criteria DSL**: write the JSON schema \+ Lambda that maps parsed text → computable checks.

3. **AgentCore tools**: register `parse_criteria`, `fhir_search`, `draft_outreach`.

4. **Reasoning prompts**: chain: *read protocol → emit JSON criteria → call fhir\_search → rank & explain*.

5. **UI**: super-simple web app (or CLI) to upload protocol and view cohort with explanations.

# **Nice stretch (only if time allows)**

* **Site feasibility**: run the criteria across multiple “sites” (separate FHIR datasets) and produce an expected enrollment curve.

* **Adverse-event triage**: watch for lab outliers post-enrollment and draft MedDRA-mapped AE reports.

* **eConsent**: generate personalized consent summaries at 6th-grade reading level.

# **Two backup ideas (also strong)**

* **Protocol Deviation Copilot**: agent scans EHR events vs. schedule-of-activities; flags deviations; drafts CAPA notes.

* **Safety Signal Scout**: agent that ingests spontaneous reports \+ EHR timelines to draft **case narratives** for pharmacovigilance.

If this sounds good, I can sketch the criteria-DSL and the AgentCore tool contracts next, plus a tiny synthetic dataset you can run locally to iterate before wiring to HealthLake.

**Medical References**

1. None  
   DOI: file-GyjWQ4uZnVrr59g9ERjYRW

