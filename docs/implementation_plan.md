# Implementation Plan

## Overview

Clinical trial enrollment often requires matching patients to complex eligibility criteria, a process that is time-consuming and error-prone if done manually[\[1\]](https://www.nature.com/articles/s41467-024-53081-z?error=cookies_not_supported&code=c5425ed2-be05-4606-8ac4-56a14adc40bb#:~:text=potentially%20improve%20their%20health%20outcomes,and%20prone%20to%20human%20errors). This project proposes an AI agent that automates patient-trial matching using a Large Language Model (LLM) on AWS Bedrock. The agent will parse trial eligibility criteria and cross-reference them with patient electronic health records (EHR) in FHIR format to determine eligibility. By converting free-text criteria into structured queries and applying them to patient data, the agent follows a proven "trial-to-patient" matching approach[\[2\]](https://www.nature.com/articles/s41467-024-53081-z?error=cookies_not_supported&code=c5425ed2-be05-4606-8ac4-56a14adc40bb#:~:text=directionality%2C%20there%20are%20two%20types,explore%20a%20large%20set%20of). The goal is to streamline clinical trial recruitment and ensure the solution meets the AWS AI Agent Hackathon requirements for functionality and robustness.

## System Architecture

The solution's architecture consists of several components working in concert:

* **LLM Agent (Amazon Bedrock)**: At the core is a Bedrock-hosted LLM (such as Amazon Titan or Anthropic Claude) that handles reasoning and decision-making. We use Amazon Bedrock AgentCore to orchestrate the agent, providing a secure, isolated runtime for agent execution[\[3\]](https://blog.radixia.ai/serverless-ai-agents-with-amazon-bedrock-agentcore/#:~:text=Amazon%20Bedrock%20AgentCore%20is%20structured,The%20microVMs%20are).

* **Eligibility Criteria Parser**: A tool powered by the LLM that transforms unstructured trial eligibility criteria text into a structured representation (e.g., JSON or FHIR queries). This allows logical checks against patient data.

* **FHIR Patient Data Store**: Patient health records are stored in a FHIR-compliant database. We recommend Amazon HealthLake, a HIPAA-eligible service for storing and querying health data at scale[\[4\]](https://aws.amazon.com/blogs/machine-learning/get-started-with-the-redox-amazon-healthlake-connector/#:~:text=Amazon%20HealthLake%20is%20a%20new%2C,and%20their%20Amazon%20HealthLake%20Connector). (For development or testing, a local HAPI FHIR server can be used as an alternative.)

* **FHIR Search Tool**: An integration (via API or Lambda) that allows the agent to query the FHIR store for specific patient information. This tool takes structured criteria (e.g., "Patient has condition X" or "Lab result Y \> Z") and returns whether the patient meets that criterion by checking the FHIR data.

* **Agent Orchestration**: The agent uses Bedrock AgentCore to manage tool usage and maintain context. Using the AgentCore Gateway, we expose the parser and FHIR search functionalities as tools the agent can invoke securely[\[5\]](https://aws.amazon.com/bedrock/agentcore/#:~:text=Enable%20intelligent%2C%20personalized%20experiences%20with,tasks%20such%20as%20generating%20visualizations). The agent’s workflow involves parsing criteria, iteratively checking patient data, and compiling an eligibility decision with rationale.

* **User Interface (Optional)**: For demonstration, a simple interface (CLI or web UI) or an API endpoint can be provided for users to input a patient ID and retrieve matching trial results. This is not required by the core logic but improves presentation and usability.

This architecture will be illustrated in a diagram included in the repository (e.g. docs/architecture\_diagram.png) showing the flow from user query to LLM agent to tools and data stores, and back to the result.

## Implementation Steps

1. **Environment Setup** – Configure AWS resources and data. This includes creating an Amazon Bedrock workspace, setting up Amazon HealthLake (with a synthetic dataset, e.g., using Synthea for sample patient records[\[6\]](https://github.com/aws-samples/patient-matching-of-clinical-trials-using-generative-ai#:~:text=Inferencing%20in%20Part%203,highly%20encouraged%20for%20part%203)), and ensuring the Bedrock foundation model (LLM) is accessible. Also, prepare the GitHub repository structure with a clear README, this implementation plan, and placeholders for code.

2. **Develop Criteria Parser** – Implement the criteria parsing logic. Begin with prompt engineering for the LLM to convert eligibility criteria text into a structured form. Create a Bedrock Lambda function or AgentCore tool for this parser. Test the parser on sample criteria and refine the prompt until the output correctly captures inclusion/exclusion rules.

3. **Implement FHIR Search Integration** – Set up a method to query the HealthLake (or other FHIR server) for patient data. This may be a Lambda function that, given a patient ID and a criterion (or a query template), returns whether the criterion is met. Use AWS SDK or FHIR APIs to retrieve necessary resources (Patient, Observation, Condition, etc.). Ensure this works for various types of criteria (demographics, lab values, diagnoses).

4. **Agent Workflow Construction** – Using Bedrock AgentCore, define the agent’s prompt and tool usage. Register the parser and search functions as tools via the AgentCore Gateway or SDK. Craft the agent's system prompt to instruct it on how to use the tools (for example, *“First parse the criteria, then for each structured criterion call the FHIR search, then decide if the patient qualifies”*). If not using AgentCore’s built-in planner, implement a custom loop: the agent decides an action, the code executes it, and the result is fed back until completion.

5. **Testing & Validation** – Run end-to-end tests with known scenarios (e.g., a patient who should match a trial and one who should not). Verify the agent's outputs – it should correctly identify unmet criteria or confirm eligibility and provide an explanation grounded in the patient data. Debug issues (e.g., incorrect parsing or edge cases where data is missing).

6. **Iteration and Optimization** – Improve the system based on test feedback. This could include refining prompts, adding more parsing rules for edge cases (such as complex logical criteria or date-based criteria), and optimizing FHIR queries (ensuring they are not too slow or costly by retrieving only necessary fields).

7. **Implement Guardrails** – Apply safety and compliance measures. Enable Bedrock’s content filtering on the LLM output to prevent any disallowed content. Because patient data is sensitive, ensure that the agent does not expose personally identifiable information in outputs beyond what's needed for the decision. The use of Amazon HealthLake (HIPAA-eligible) and AgentCore’s isolated execution environment adds compliance assurance[\[3\]](https://blog.radixia.ai/serverless-ai-agents-with-amazon-bedrock-agentcore/#:~:text=Amazon%20Bedrock%20AgentCore%20is%20structured,The%20microVMs%20are). Document how PHI is protected (for example, no raw data is logged, and all access to health data is through secure APIs with proper IAM permissions).

8. **Documentation & Demo Prep** – Prepare final documentation and presentation materials. This includes polishing the README, this implementation plan, and creating the docs/todo task breakdown files (to show detailed design of each component). Additionally, outline the demo script and record a short video (≈3 minutes) showcasing the agent in action. Ensure the demo highlights how the agent works and meets the hackathon criteria (functionality, etc.).

9. **Deployment (Optional Stretch)** – If time permits, deploy the solution for external access. This could involve hosting the agent behind an API Gateway endpoint or providing a simple web UI. Ensure any deployment includes instructions for judges to invoke the agent (e.g., a URL or a script), and verify that no sensitive data is exposed in a public setting.

Throughout implementation, we will use agile iterations, verifying that each component works before integrating them. By the end, we aim to have a functional, scalable agent that can be run with minimal setup from the repository.

## Timeline

* **Day 1–2:** Project setup on AWS and data import – set up Bedrock and AgentCore environment, create the HealthLake datastore and load synthetic patient data, configure IAM roles, and scaffold the code repository.

* **Day 3–4:** Build and test the Criteria Parser – design the prompt, implement the parsing function (Bedrock call or Lambda), and verify it works on multiple example criteria.

* **Day 5–6:** Build and test the FHIR Search tool – implement FHIR queries (via HealthLake or HAPI FHIR) and ensure the tool correctly returns matches for given criteria. Test with sample patient records.

* **Day 7–8:** Develop the Agent workflow – integrate the LLM reasoning with tool usage. Set up the AgentCore agent (or custom loop), write the system prompt guiding the agent, and test end-to-end on a sample patient-trial scenario. Iterate on any failures (adjust prompt, fix tool bugs).

* **Day 9:** Implement guardrails & refinements – enable content moderation, double-check that the agent’s responses are accurate and safe. Optimize performance (e.g., ensure the number of Bedrock calls is minimal and queries are efficient). Begin crafting the demo narrative.

* **Day 10:** Final testing, documentation, and presentation – run a final full demo to ensure reliability. Freeze the code and prepare submission materials: finalize the documentation (with architecture diagram), upload the demo video, and ensure the public repo is comprehensive and well-organized for judging.

*(Note: “Day” labels are approximate work days. Some tasks can be done in parallel by team members; for example, one person can work on the parser while another sets up the FHIR backend. The timeline assumes focused effort and may adjust based on project complexity.)*

## Recommended AWS Technologies & Tools

* **Amazon Bedrock (LLM Models)** – Hosts the foundation model (such as Amazon Titan or Anthropic Claude) that powers the agent’s reasoning and natural language understanding.

* **Amazon Bedrock AgentCore** – Provides managed infrastructure for the agent. We leverage AgentCore’s primitives like **Runtime** for secure, isolated execution and long-running sessions, **Memory** for cross-interaction context if needed, and **Gateway** to expose our custom logic as tools with minimal integration effort[\[5\]](https://aws.amazon.com/bedrock/agentcore/#:~:text=Enable%20intelligent%2C%20personalized%20experiences%20with,tasks%20such%20as%20generating%20visualizations). This eliminates undifferentiated heavy lifting, allowing us to deploy a highly capable agent securely and at scale[\[7\]](https://aws.amazon.com/bedrock/agentcore/#:~:text=Amazon%20Bedrock%20AgentCore%20enables%20you,can%20accelerate%20agents%20to%20production).

* **Amazon HealthLake** – Serves as the FHIR-compatible EHR data store for patient records. Amazon HealthLake is a HIPAA-eligible service designed to store, transform, query, and analyze health data at scale[\[4\]](https://aws.amazon.com/blogs/machine-learning/get-started-with-the-redox-amazon-healthlake-connector/#:~:text=Amazon%20HealthLake%20is%20a%20new%2C,and%20their%20Amazon%20HealthLake%20Connector). Using HealthLake ensures we can reliably query patient data (via FHIR APIs) and maintain compliance with healthcare data standards and privacy requirements.

* **HAPI FHIR (Open Source)** – (For development/testing) A Java-based open-source implementation of the HL7 FHIR standard[\[8\]](https://hapifhir.io/#:~:text=HAPI%20FHIR%20is%20a%20complete,product%20of%20Smile%20Digital%20Health). We can use a local HAPI FHIR server to simulate FHIR endpoints and test our integration without incurring cloud costs. This is useful for early development or if HealthLake setup is not immediately available.

* **AWS Lambda** – Used for implementing serverless functions such as the criteria parsing logic (if run outside the LLM) and the FHIR querying operations. Lambda provides scalability and a straightforward way to wrap Python/JavaScript logic for the agent to call. For instance, the agent could invoke a Lambda (via API Gateway or AgentCore Gateway) to fetch patient data for a given criterion.

* **Amazon API Gateway** – If we expose the agent or its tools as HTTP endpoints, API Gateway will front those Lambda functions to provide RESTful APIs. This could be how the agent calls the FHIR search tool (though AgentCore Gateway might also handle it internally) or how external users invoke the agent (e.g., a web client calls an API to get trial matching results).

* **Amazon DynamoDB** – A fast NoSQL database used for storing metadata or caching results. DynamoDB can store pre-processed trial criteria (structured format) for quick reuse, or keep a log of which patients were matched to which trials (if needed for audit). It provides millisecond read times, which helps keep the agent responsive.

* **Amazon S3** – Used for storing any static assets and outputs: for example, the architecture diagram image in docs, sample input/output files, or even the transcript of agent conversations for debugging. S3 could also store the content of large language model prompts or results if needed for asynchronous processing.

* **Amazon CloudWatch & Bedrock Observability** – For logging and monitoring. CloudWatch will collect logs from Lambda functions and any application logs, while Bedrock AgentCore’s observability features (integrated with CloudWatch or OpenTelemetry) will allow us to trace agent actions, tool usage, and performance metrics. This is crucial for debugging and for demonstrating reliability to judges.

* **IAM (Identity and Access Management)** – We will set up fine-grained IAM roles and policies to ensure each component only accesses what it should. For example, the Lambda that queries HealthLake will have an IAM role permitting only HealthLake read access. Bedrock AgentCore’s Identity primitive can also manage temporary credentials if the agent needs to assume roles securely[\[9\]](https://aws.amazon.com/bedrock/agentcore/#:~:text=Identity%20Secure%2C%20scalable%20agent%20identity,authorized%20user%20consent.%20Learn%20more). Proper IAM setup is part of our security guardrails.

By leveraging these AWS services and tools, our solution remains **cloud-native, scalable, and secure**. We ensure the technology choices directly support the project requirements (for instance, using HealthLake for FHIR data to avoid building a FHIR server from scratch, and using Bedrock AgentCore to handle the heavy lifting of agent management).

## Satisfying the Hackathon Scoring Rubric

* **Functionality:** The agent provides a functional solution to a real problem – it can be deployed on AWS and consistently match patients to clinical trials automatically. We will ensure the final submission includes clear setup instructions and a working demo (or live endpoint) showing the agent performing the task as described. The core features (parsing criteria, searching patient data, determining eligibility with explanations) will be demonstrated in the video and documentation, proving that the project meets the required functionality and behaves as promised in our description.

* **Technical Execution:** Our project makes full use of the required AWS technologies. We utilize an LLM hosted on Amazon Bedrock and at least one Bedrock AgentCore primitive (tool integration via Gateway, plus the secure runtime) to meet the hackathon’s technical requirements[\[10\]](https://aws-agent-hackathon.devpost.com/rules#:~:text=1,DIY%20agents%20using%20AWS%20infrastructure). The solution is engineered following AWS best practices: it’s **well-architected** (decoupled components, stateless Lambdas, etc.), **reproducible** (infrastructure configuration and code in a public repo with instructions), and integrates multiple services (Bedrock, HealthLake, Lambda, etc.) smoothly. We will highlight how we addressed technical challenges (like parsing natural language criteria and interfacing with FHIR data) in the documentation. The use of serverless components and managed services showcases modern, efficient development, and we handle errors and edge cases to ensure reliability (for example, what if a criterion cannot be parsed or no patient data is found – the agent handles this gracefully).

* **Architecture:** The system architecture is **modular, scalable, and secure**. We include an architecture diagram to communicate this clearly. The design leverages AWS’s scalable services (so it can handle increasing data or more trials/patients in the future) and isolates concerns (LLM reasoning vs. data retrieval vs. data storage are separate). The architecture also addresses the specific needs of the use case: using a FHIR store for interoperability and Health data compliance, and using AgentCore for long-running, tool-augmented reasoning. We will explain our architecture choices in the documentation (why each component was chosen and how they interact). This clarity and reasoning demonstrate a strong architectural understanding, which will score well in the judging.

* **Presentation:** We will present the project in a polished manner. The repository is organized with clear documentation (including this implementation plan and detailed TODO files per feature), making it easy for developers and judges to navigate. The README will serve as an introduction and user guide. We will prepare a concise \~3 minute demo video that **clearly shows the agent in action**, likely walking through a scenario: e.g., *“Given Patient X’s record and Trial Y’s criteria, watch how the agent parses the criteria, checks each condition, and outputs whether Patient X qualifies.”* The video will highlight key features and also mention how we used AWS technologies. Our writing and visuals will be professional and accessible, ensuring that the value of the project is understood even without deep background. This attention to presentation will meet and exceed the expectations in the Presentation category.

* **Guardrails:** Our solution is designed with **safety, privacy, and responsibility** in mind. We handle **patient data carefully**: all data stays in a secure, HIPAA-eligible environment (HealthLake) and we do not include any real personal health information in the demo (using synthetic data instead). The Bedrock LLM’s output will be constrained to the task (we instruct it to only discuss trial eligibility), minimizing risk of inappropriate content. Nonetheless, we will enable Amazon Bedrock’s content moderation features to filter any potentially unsafe or sensitive outputs. We also utilize AgentCore’s security features – for example, each agent session runs in an isolated microVM which prevents any data leakage between sessions[\[3\]](https://blog.radixia.ai/serverless-ai-agents-with-amazon-bedrock-agentcore/#:~:text=Amazon%20Bedrock%20AgentCore%20is%20structured,The%20microVMs%20are). From a compliance perspective, every access to data is through authorized APIs with audit logging (via CloudWatch and the AgentCore observability primitive), so we have an audit trail of the agent’s actions. If the agent were to be extended or integrated in a real setting, these guardrails ensure it could be done in a manner that respects patient privacy and follows responsible AI guidelines. By proactively addressing guardrails (both from an AI perspective and a cloud security perspective), we align with the hackathon’s emphasis on building safe and trustworthy AI agents.

By addressing each of the above criteria in our plan and implementation, we intend to deliver a project that is **highly competitive** in the hackathon – showcasing not only a cool functional agent, but one that is technically robust, well-designed, well-presented, and responsibly engineered.

---

