# AWS Trial Enrollment System - AI-Powered Clinical Trial Matching

## The Problem: A Healthcare Crisis in Clinical Trials

Clinical trials are the backbone of medical innovation, yet **85% fail to meet enrollment targets**, with patient recruitment taking an average of 600+ days. This bottleneck costs the pharmaceutical industry billions annually and delays life-saving treatments from reaching patients who need them most. The root cause? Manual eligibility screening is slow, error-prone, and overwhelmed by complex medical criteria spanning hundreds of pages across dozens of FHIR resource types.

Healthcare coordinators spend countless hours manually reviewing patient records against intricate inclusion/exclusion criteria, only to find most patients ineligible. Meanwhile, eligible patients remain undiscovered in fragmented electronic health record systems. The result: drug development timelines stretch for years, trial costs skyrocket, and patients lose access to potentially life-saving treatments.

## Our Solution: Intelligent Automation Powered by AWS AI

**AWS Trial Enrollment System** (accessible at [enrollment.samyama.care](https://enrollment.samyama.care)) is an AI-powered clinical trial enrollment and eligibility management platform that transforms this manual, week-long process into an automated, minute-long workflow. By leveraging Amazon Bedrock with **Mistral Large 2**, AWS HealthLake, and a suite of specialized AI services, we've built a HIPAA-compliant agentic system that autonomously processes clinical trial protocols, searches FHIR patient data, and generates intelligent eligibility recommendations with confidence scores and explainable reasoning.

Our solution doesn't just automate—it orchestrates a sophisticated multi-phase AI pipeline that mimics and surpasses human clinical reasoning while maintaining complete transparency and auditability.

## Three User Personas: Serving Every Stakeholder

### 1. Clinical Research Coordinator (CRC) - The Frontline Screener

CRCs are responsible for day-to-day patient screening and trial enrollment. Our platform empowers them with:

- **Quick Patient Search**: Search across 11 FHIR resource types in AWS HealthLake (Patient, Condition, Observation, MedicationStatement, AllergyIntolerance, Procedure, and more)
- **Instant Eligibility Checks**: AI-powered matching using Mistral Large 2 returns results in under 60 seconds
- **Confidence Scoring**: Each match includes a confidence percentage and detailed reasoning
- **Dashboard Metrics**: Real-time tracking of patients screened (247), active matches (42), and success rate (78%)
- **PDF Export**: Generate professional eligibility reports for IRB submission

**CRC Workflow**: Login → Search Protocols → Select Patient → Run AI Eligibility Check → Review Results → Export Report

### 2. Study Administrator (StudyAdmin) - The Protocol Manager

Study administrators manage the trial portfolio and ensure protocols are properly processed. Our platform provides:

- **Drag-and-Drop Upload**: Upload PDF protocol documents directly to S3
- **Automated Pipeline Monitoring**: Track 5-phase processing (PDF Upload → Textract OCR → Comprehend Medical NER → Mistral Parsing → DynamoDB Cache)
- **Protocol Library**: Manage active, processing, and failed protocols with status distribution charts
- **System-Wide Analytics**: Monitor total protocols (10), active protocols (8), processing (1), and failed (1)

**StudyAdmin Workflow**: Login → Dashboard Overview → Upload Protocol PDF → Monitor Processing → View Parsed Criteria → Manage Protocol Library

### 3. Principal Investigator (PI) - The Decision Maker

PIs oversee multiple trials and make final enrollment decisions. Our platform delivers:

- **Enrollment Dashboard**: High-level metrics across active trials (5), total enrolled (38), pending review (12), and match rate (67%)
- **Match Confidence Distribution**: Visual charts showing high (≥80%), medium (50-79%), and low (<50%) confidence matches
- **Trial-Specific Progress**: Track enrollment progress for each active trial
- **Approval Queue**: Review and approve/reject patient matches with full AI reasoning transparency
- **Executive Summaries**: Export enrollment summaries for sponsor reporting

**PI Workflow**: Login → View Enrollment Metrics → Review Match Distribution → Approve/Reject Matches → Export Summaries

## How It Works: The AI Agent Pipeline

Our autonomous AI agent operates through a sophisticated 5-phase pipeline:

**Phase 1: PDF Upload** - StudyAdmin uploads protocol → S3 trigger activates orchestration
**Phase 2: OCR Extraction** - AWS Textract extracts text from multi-page PDF documents
**Phase 3: Medical NER** - AWS Comprehend Medical identifies medical entities, conditions, medications
**Phase 4: AI Parsing** - Amazon Bedrock with **Mistral Large 2** (`mistral.mistral-large-2402-v1:0`) parses complex eligibility criteria into structured, machine-readable format
**Phase 5: Cache Storage** - Parsed criteria stored in DynamoDB for instant retrieval

When a CRC runs an eligibility check, the agent:

1. Retrieves parsed criteria from cache
2. Queries AWS HealthLake for patient FHIR data across 11 resource types
3. Uses Mistral Large 2 to perform intelligent matching with medical reasoning
4. Generates confidence scores and detailed explanations
5. Stores results in DynamoDB for PI review

## Technical Innovation: Multi-Modal AI Orchestration

Our architecture showcases AWS AI services working in concert:

- **Amazon Bedrock (Mistral Large 2)**: Core reasoning engine for criteria parsing and eligibility matching
- **AWS Textract**: Automated PDF document text extraction and layout analysis
- **AWS Comprehend Medical**: Medical entity recognition and NER for clinical text
- **AWS HealthLake**: FHIR R4 compliant patient data store with 11 resource types
- **AWS Lambda**: 10 serverless functions orchestrating the AI agent workflow
- **Amazon DynamoDB**: 3 tables for criteria caching, evaluation results, and patient-protocol matches with GSIs
- **Amazon Cognito**: Role-based authentication for 3 user groups (CRC, StudyAdmin, PI)
- **Amazon API Gateway**: RESTful API with JWT authorization
- **Amazon CloudFront + S3**: Global content delivery for React frontend
- **AWS CDK (Python)**: Infrastructure as Code for reproducible deployment

**Key Innovations:**

- **Explainable AI**: Every eligibility decision includes detailed reasoning from Mistral Large 2
- **FHIR-Native**: Seamless integration with FHIR R4 standard for healthcare interoperability
- **Autonomous Pipeline**: Self-healing, event-driven architecture with retry logic
- **Multi-Tenancy**: Role-based access control serving three distinct user personas
- **Production-Grade**: HIPAA compliance considerations, CloudWatch observability, Lambda Powertools

## Real-World Impact

**From Weeks to Minutes**: What once took coordinators 2-3 weeks now completes in under 5 minutes
**Improved Accuracy**: AI-powered matching reduces human error and finds eligible patients missed by manual review
**Accelerated Drug Development**: Faster enrollment means faster trial completion and earlier FDA approval
**Better Patient Outcomes**: More patients gain access to cutting-edge treatments sooner
**Cost Savings**: Reducing enrollment time saves millions per trial in operational costs
**Scalability**: Supports thousands of trials and millions of patients globally

## Built With AWS: Enterprise-Ready Architecture

Our system leverages 11 AWS services in a serverless, auto-scaling architecture:

- **Compute**: AWS Lambda (10 functions), Amazon API Gateway
- **AI/ML**: Amazon Bedrock (Mistral Large 2), AWS Textract, AWS Comprehend Medical
- **Data**: AWS HealthLake, Amazon DynamoDB (3 tables), Amazon S3
- **Security**: Amazon Cognito, IAM roles, VPC, encryption at rest and in transit
- **Delivery**: Amazon CloudFront, Route 53 (custom domain)
- **Observability**: Amazon CloudWatch (logs, metrics, tracing)
- **IaC**: AWS CDK (Python)

**Live Demo**: [enrollment.samyama.care](https://enrollment.samyama.care)
**Source Code**: [Backend](https://github.com/VaidhyaMegha/aws-trial-enrollment-agent) | [Frontend](https://github.com/VaidhyaMegha/trial-compass-pro)

## Why This Matters

Clinical trial enrollment isn't just a healthcare problem—it's a humanitarian crisis. Every day trials remain understaffed, patients lose access to potentially life-saving treatments. By combining the reasoning power of Amazon Bedrock's Mistral Large 2 with the specialized capabilities of AWS Textract, Comprehend Medical, and HealthLake, we've created an AI agent that doesn't replace healthcare professionals—it empowers them to work faster, smarter, and more accurately.

This is the future of clinical trial enrollment: intelligent, autonomous, and accessible at **enrollment.samyama.care**.

---

**Organization**: Samyama.ai
**Submission for**: AWS AI Agent Global Hackathon
**Categories**: Grand Prize, Best Amazon Bedrock Application
