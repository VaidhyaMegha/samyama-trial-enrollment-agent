# FHIR Search Integration

**Overview:** This functional area covers how the agent queries patient data to check criteria. We use a FHIR-compliant data source for patient records (conditions, labs, demographics, etc.), enabling interoperability. The agent will use a tool that translates a parsed criterion into a FHIR search (or other data lookup) and returns whether the patient meets that criterion.

## Tasks

* \[ \] **Set up FHIR datastore** – Choose and configure a FHIR database for patient data. The recommended choice is **Amazon HealthLake**, which provides a managed FHIR endpoint (and is HIPAA-eligible for health data)[\[4\]](https://aws.amazon.com/blogs/machine-learning/get-started-with-the-redox-amazon-healthlake-connector/#:~:text=Amazon%20HealthLake%20is%20a%20new%2C,and%20their%20Amazon%20HealthLake%20Connector). Alternatively, set up a local HAPI FHIR server for development purposes. Document the base FHIR endpoint URL and any auth required (HealthLake uses AWS SigV4 or Cognito OAuth for access).

* \[ \] **Load synthetic patient data** – Populate the FHIR store with test patient records. Use **Synthea** (an open-source synthetic patient generator) to create realistic patient data and convert to FHIR format. AWS’s sample code provides guidance on importing Synthea data into HealthLake[\[6\]](https://github.com/aws-samples/patient-matching-of-clinical-trials-using-generative-ai#:~:text=Inferencing%20in%20Part%203,highly%20encouraged%20for%20part%203). Ensure we have a diverse set of patients to test various criteria (age ranges, conditions, lab results).

* \[ \] **Identify relevant FHIR resources** – For each type of criterion, determine which FHIR resource and fields are involved:

* *Demographic criteria* (age, gender) → **Patient** resource (e.g., Patient.birthDate for age).

* *Condition criteria* (diagnoses, medical history) → **Condition** resource (with Condition.code for diagnosis codes or descriptions, and possibly clinical status).

* *Laboratory criteria* (lab values, vitals) → **Observation** resource (with Observation.code for test type and Observation.valueQuantity for the value).

* *Medication criteria* → **MedicationStatement** or **MedicationRequest**.

* etc.

* \[ \] **Implement search logic** – Write a function (or set of functions) to query the FHIR API for a given patient and criterion. For example:

* *Age criterion:* Calculate age from Patient.birthDate and compare.

* *Condition criterion:* FHIR search like GET /Condition?subject=Patient/\[id\]\&code=${conditionCode} (or search by condition text if codes aren’t used, though code is preferable).

* *Observation criterion:* GET /Observation?subject=Patient/\[id\]\&code=${loincCode}\&value${operator}=${value} (using FHIR search parameters for value comparisons, e.g., value-quantity). Use the FHIR REST API via HTTPS requests or an AWS SDK if available. This could be done within a Lambda for ease of integration.

* \[ \] **Tool interface contract** – Define the agent tool that will perform these searches. For example, a tool CheckCriterion might accept input {"patient\_id": "...", "criterion": {...}} where the criterion is one element of the structured criteria JSON. It will return a boolean or a small JSON indicating *met/not met* (and possibly the data evidence). Using AgentCore’s Gateway, we can expose this functionality securely as an API endpoint the agent can call[\[5\]](https://aws.amazon.com/bedrock/agentcore/#:~:text=Enable%20intelligent%2C%20personalized%20experiences%20with,tasks%20such%20as%20generating%20visualizations). Document how the agent should call this tool (in the prompt, e.g., *“use CheckCriterion to verify if the patient meets a criterion.”*).

* \[ \] **Test queries on sample data** – Manually verify that for a known patient, the queries work. For example, if a synthetic patient is 45 years old and the criterion is “Age ≥ 18”, ensure the age check logic returns true. If a patient has no diabetes in their Condition list and criterion is “No history of diabetes (exclusion)”, ensure the query (or logic) correctly returns that the criterion is satisfied (patient *does* meet the “no diabetes” criterion) – or handle the logic inversion appropriately (exclusion criteria might be marked as met if the condition is absent).

* \[ \] **Optimize query performance** – Ensure that each check is as efficient as possible. FHIR $everything endpoint can fetch an entire patient record in one call[\[11\]](https://aws.amazon.com/blogs/industries/ai-powered-patient-profiles-using-aws-healthlake-and-amazon-bedrock/#:~:text=The%20solution%20leverages%20several%20key,FHIR%20operations%20provided%20by%20HealthLake), which we could use to pull data once and then check criteria locally in memory. This might be more efficient when checking many criteria for one patient (reducing multiple HTTP calls). Evaluate this approach: for initial implementation, simple targeted queries are fine; for a stretch improvement, a single fetch and in-memory filter could be done. Comment in code where optimizations are possible.

* \[ \] **Error and edge-case handling** – Implement robust checks: if the FHIR server returns an error or times out, the tool should handle it (maybe retry or return a clear error to the agent). If a patient’s data is missing a field (e.g., no lab result for a required test), decide how the agent should interpret that (likely the patient does *not* meet that criterion, or the criterion is unknown – clarify this logic).

* \[ \] **Security considerations** – Ensure that the FHIR queries are read-only and that credentials (keys, tokens) are handled securely (never hard-coded in code, use AWS Secrets Manager or environment variables for any keys). Also, log minimally – do not log full patient records. Enable CloudWatch logs for queries for debugging, but sanitize any personal data in logs if possible. HealthLake being HIPAA-eligible means it has encryption and audit features; still, our use of it should adhere to least privilege (the Lambda/tool IAM role only can read from this HealthLake datastore).

* \[ \] **Stretch Goal – Complex criteria support**: Some criteria might be logically complex (e.g., “Patient has either condition X or Y *and* at least one of lab A or B above a threshold”). Currently, our parser might split these into separate atomic criteria, and the agent logic will handle the AND/OR. If time allows, verify the agent can handle combined logic – if not, consider enhancing the parser to preserve some structure (like a criterion group with sub-criteria). Additionally, consider temporal criteria (e.g., “within last 6 months”) – this would involve adding date filters in FHIR queries (\_lastUpdated or observation date filters). Mark this as an advanced feature to tackle if core functionality is done.

---

