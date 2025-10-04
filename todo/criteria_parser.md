# Criteria Parser

**Overview:** This component handles transforming free-form clinical trial eligibility criteria text into a structured format that can be programmatically evaluated against patient data. By parsing the inclusion/exclusion criteria, the agent can systematically check each rule against a patient’s records. (Converting criteria to database queries is a known approach for trial matching[\[2\]](https://www.nature.com/articles/s41467-024-53081-z?error=cookies_not_supported&code=c5425ed2-be05-4606-8ac4-56a14adc40bb#:~:text=directionality%2C%20there%20are%20two%20types,explore%20a%20large%20set%20of).)

## Tasks

* \[ \] **Define structured format** – Decide how to represent parsed criteria. This could be a JSON schema listing each criterion with fields like type (inclusion/exclusion), attribute (what is being checked, e.g. age, condition), operator (e.g. ≥, equals), and value. Alternatively, define a mapping to FHIR search queries (e.g., an age criterion becomes a FHIR query on Patient.birthDate).

* \[ \] **Collect sample criteria** – Gather example eligibility criteria from one or more clinical trials (e.g., from ClinicalTrials.gov or papers) to understand typical phrasing. Use these to inform prompt design and for testing the parser.

* \[ \] **Draft parsing prompt** – Write an initial prompt for the LLM to convert eligibility text into the chosen structured format. Include examples in the prompt (few-shot examples), such as *“Input: Must be between 18 and 65 years old. Output: { field: 'age', operator: 'between', value: \[18, 65\] }”*. Emphasize distinguishing inclusion vs. exclusion and handling units or medical terms.

* \[ \] **Implement parser function** – Create a function (e.g., a Python AWS Lambda) that calls the Bedrock LLM with the prompt. This function takes a blob of criteria text (possibly multiple bullet points) and returns the structured representation. Utilize the Bedrock SDK to call the model. Ensure the function is stateless and can be invoked by the agent as a tool.

* \[ \] **Tool interface contract** – Define how the agent will invoke this parser. For example, using AgentCore’s tool specification, we might define a tool ParseCriteria that accepts {"criteria\_text": "\<string\>"} and returns a JSON list of parsed criteria. Document this contract so the agent’s prompt can refer to it accurately.

* \[ \] **Testing & refinement** – Run the parser on various examples and examine the output. Check that all key criteria are captured and the format is correct. Refine the LLM prompt as needed (e.g., if certain phrases aren’t parsed correctly, add guidance or more examples to the prompt). Aim for the parser to handle common cases like numerical ranges, multiple conditions in one criterion (using logical AND/OR), and negations (“no history of X”).

* \[ \] **Error handling** – Determine how to handle parsing failures or uncertainties. If the LLM is not confident, perhaps the tool can return a flag or an empty result for that criterion, and the agent can decide to mark the trial as uncertain. Alternatively, use a few-shot example in the prompt for “If criteria is unclear, output a best guess and mark it.” Document this decision.

* \[ \] **Performance consideration** – Parsing can be done once per trial and reused for multiple patients. Consider caching parsed criteria results. For example, store the JSON outcome in DynamoDB keyed by trial ID, so if the agent sees the same trial again it can skip re-parsing (this is especially useful if matching one patient against many trials).

* \[ \] **Stretch Goal – Advanced NLP**: Incorporate domain knowledge. For example, integrate a medical ontology or use a library to recognize medical terms in criteria (like SNOMED CT codes). This could make the criteria parser output more standardized (e.g., map “heart attack” to an ICD-10 or SNOMED code). This is optional and only if time permits, as it requires additional data resources.

---

