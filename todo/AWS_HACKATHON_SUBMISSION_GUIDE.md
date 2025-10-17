# AWS AI Agent Global Hackathon - Submission Guide for AWS Trial Enrollment System

**Project:** AWS Trial Enrollment System/Agent
**Organization:** Samyama.ai
**Submission Deadline:** October 20, 2025, 5:00 PM PDT

---

## 📋 Table of Contents

1. [Project Overview](#project-overview)
2. [Hackathon Requirements Compliance](#hackathon-requirements-compliance)
3. [Submission Checklist](#submission-checklist)
4. [Submission Process](#submission-process)
5. [Prize Categories We're Eligible For](#prize-categories-were-eligible-for)
6. [Judging Criteria Alignment](#judging-criteria-alignment)
7. [Three User Personas & Workflows](#three-user-personas--workflows)
8. [Next Steps & Action Items](#next-steps--action-items)

---

## 🎯 Project Overview

**AWS Trial Enrollment System** (frontend alias: Trial Compass Pro) is a comprehensive HIPAA-compliant clinical trial enrollment and eligibility management platform powered by AWS AI services. Our AI agent automates the complex process of matching patients to clinical trials by:

- Parsing clinical trial protocols using **AWS Bedrock with Mistral Large 2**
- Extracting and analyzing patient health data from FHIR resources via **AWS HealthLake**
- Processing protocol documents with **AWS Textract**
- Performing intelligent medical entity extraction with **AWS Comprehend Medical**
- Providing real-time recommendations and autonomous eligibility decision-making

**Real-World Impact:** Reduces trial enrollment time from weeks to minutes, potentially accelerating drug development and improving patient access to cutting-edge treatments.

---

## ✅ Hackathon Requirements Compliance

### 1. **LLM Source** ✅

- **Using:** Amazon Bedrock with **Mistral Large 2** (`mistral.mistral-large-2402-v1:0`)
- **Location:** `src/lambda/criteria_parser/handler.py` (line 1995)
- **Purpose:**
  - Protocol criteria parsing and extraction
  - Eligibility reasoning and decision-making
  - Natural language understanding of medical criteria

**Code Reference:**
```python
def parse_criteria_with_bedrock(criteria_text: str, model_id: str = "mistral.mistral-large-2402-v1:0")
```

### 2. **Required AWS Services** ✅

Our project uses multiple AWS services:

#### Core Services:

- **Amazon Bedrock** (LLM - Mistral Large 2) - AI agent reasoning
- **AWS Lambda** - 10 serverless functions for agent execution:
  - `TrialEnrollment-CriteriaParser` - Bedrock-powered criteria parsing
  - `TrialEnrollment-FHIRSearch` - Patient eligibility checking
  - `TrialEnrollment-ProtocolManager` - Protocol management
  - `TrialEnrollment-PatientManager` - Patient data management
  - `TrialEnrollment-MatchManager` - Patient-protocol matching
  - `TrialEnrollment-AdminManager` - System administration
  - `TrialEnrollment-Authorizer` - JWT authentication
  - `TrialEnrollment-TextractProcessor` - Document text extraction
  - `TrialEnrollment-SectionClassifier` - Medical section classification
  - `TrialEnrollment-ProtocolOrchestrator` - Pipeline orchestration
- **Amazon DynamoDB** - 3 tables for state management:
  - `CriteriaCacheTable` - Parsed criteria caching
  - `EvaluationResultsTable` - Eligibility results
  - `MatchesTable` - Patient-protocol matches with GSIs
- **Amazon Comprehend Medical** - Medical entity extraction and NER
- **Amazon Textract** - OCR for protocol PDF documents
- **AWS HealthLake** - FHIR R4 patient data management
- **Amazon Cognito** - User authentication with 3 user groups
- **Amazon API Gateway** - RESTful API endpoints
- **Amazon S3** - Protocol document storage and static website hosting
- **Amazon CloudFront** - Global CDN for frontend delivery

#### Infrastructure:

- **AWS CDK (Python)** - Infrastructure as Code
- **CloudWatch** - Monitoring, logging, and observability

### 3. **Agent Qualification** ✅

Our AI agent demonstrates:

**a) Reasoning Capabilities:**

- Analyzes complex inclusion/exclusion criteria using Mistral Large 2
- Makes intelligent eligibility decisions based on patient FHIR data
- Provides confidence scores and reasoning explanations
- Handles edge cases and ambiguous medical criteria
- Performs medical entity recognition with Comprehend Medical

**b) Autonomous Execution:**

- Automatically processes protocol PDF uploads via S3 triggers
- Self-initiates eligibility evaluations through orchestration Lambda
- Manages state across multi-step workflows (Textract → Classifier → Parser)
- Error handling and recovery without human intervention
- Async pipeline processing with retry logic

**c) External Integration:**

- **APIs:** AWS HealthLake FHIR API, Bedrock API, Comprehend Medical API, Textract API
- **Tools:** AWS Textract for document processing, DynamoDB for data persistence
- **Databases:** DynamoDB for criteria cache, HealthLake for patient FHIR data
- **Authentication:** AWS Cognito with SigV4 for HealthLake

---

## 📝 Submission Checklist

### Required Materials

- [X] **Public Code Repository**

  - Frontend: https://github.com/VaidhyaMegha/trial-compass-pro
  - Backend: https://github.com/VaidhyaMegha/aws-trial-enrollment-agent
  - Complete source code ✅
  - Setup/installation instructions ✅
  - README with architecture details ✅

- [ ] **Architecture Diagram**

  - **TODO:** Create comprehensive architecture diagram showing:
    - All AWS services and their interactions
    - Data flow from protocol upload to eligibility results
    - AI agent decision-making pipeline with Mistral Large 2
    - FHIR integration architecture
    - Three user personas and their access patterns
  - **Format:** PNG/SVG, high resolution
  - **Tools to use:** draw.io, Lucidchart, or AWS Architecture Icons

- [ ] **Text Description**

  - **TODO:** Write compelling description including:
    - Problem statement (clinical trial enrollment challenges)
    - Solution approach (AI-powered automation with Mistral)
    - Three user personas (CRC, StudyAdmin, PI)
    - Key features and capabilities
    - Real-world impact and value
    - Technical innovation highlights
  - **Length:** 500-1000 words
  - **Tone:** Clear, professional, impact-focused

- [ ] **Demonstration Video**

  - **TODO:** Create 3-minute demo video showing:
    - Quick intro (15s): Problem and solution
    - Three user personas overview (30s)
    - Live demo (2m): End-to-end workflow
      - StudyAdmin: Upload protocol document (Textract + Mistral parsing)
      - CRC: Patient eligibility check with HealthLake data
      - PI: Review matches and enrollment dashboard
      - AI eligibility evaluation with Mistral reasoning
      - Match results and PDF export with Samyama branding
    - Impact summary (15s): Value proposition
  - **Platform:** YouTube (unlisted/public)
  - **Quality:** 1080p minimum, clear audio
  - **Screen recording tools:** Loom, OBS Studio, or built-in tools

- [X] **URL to Deployed Project**

  - **Frontend URL:** https://enrollment.samyama.care
  - **CloudFront Distribution:** https://d25df0kqd06e10.cloudfront.net
  - **API Endpoint:** https://gt7dlyqj78.execute-api.us-east-1.amazonaws.com/prod/
  - **Status:** ✅ Fully deployed and operational with custom domain

---

## 🚀 Submission Process

### Step 1: Prepare Submission Materials (Current Focus)

1. **Create Architecture Diagram**

   ```
   Location: aws-trial-enrollment-agent/docs/architecture-diagram.png

   Must show:
   - Three user personas (CRC, StudyAdmin, PI) and their workflows
   - User flow (Login → Protocol Upload → Patient Selection → Eligibility Check)
   - AWS service topology
   - AI agent reasoning pipeline with Mistral Large 2
   - Data persistence layer
   - FHIR resource types (11 supported)
   ```

2. **Write Project Description**

   ```
   Location: aws-trial-enrollment-agent/docs/project-description.md

   Structure:
   - Problem: Clinical trial enrollment inefficiency
   - Solution: AI-powered automation with AWS Bedrock (Mistral Large 2)
   - Three User Personas:
     * Clinical Research Coordinator (CRC) - Patient screening
     * Study Administrator (StudyAdmin) - Protocol management
     * Principal Investigator (PI) - Match review and enrollment
   - Features: 11 FHIR resources, automated matching, PDF reports
   - Impact: Faster enrollment, better patient outcomes
   - Innovation: Multi-service AI orchestration with Mistral
   ```

3. **Record Demo Video**

   ```
   Script:
   [0:00-0:15] Problem: "Clinical trials fail due to slow enrollment"
   [0:15-0:45] Solution: "AWS Trial Enrollment System automates matching"
                         "Three personas: CRC, StudyAdmin, PI"
   [0:45-2:30] Demo:
     - Login with Cognito (show role selection)
     - StudyAdmin: Upload protocol (Textract + Mistral parsing)
     - CRC: Select patient from HealthLake
     - CRC: Run eligibility check (Comprehend Medical + Mistral reasoning)
     - PI: View dashboard and match results with confidence scores
     - Export PDF report with Samyama.ai branding
   [2:30-3:00] Impact: "Reduces weeks to minutes, accelerates drug discovery"

   Upload to: YouTube (recommended) or Vimeo
   Title: "AWS Trial Enrollment System - AI Clinical Trial Matching | AWS Agent Hackathon"
   ```

### Step 2: Create Devpost Submission

1. **Go to:** https://aws-agent-hackathon.devpost.com/
2. **Click:** "Submit a Project" or "Start a Submission"
3. **Fill Out Form:**

   **Basic Information:**

   - Project Name: `AWS Trial Enrollment System`
   - Tagline: `AI-Powered Clinical Trial Matching with AWS Bedrock Mistral`
   - Category: Select relevant categories (see below)

   **Built With (Technologies):**

   - Amazon Bedrock
   - Mistral Large 2
   - AWS Lambda
   - Amazon Comprehend Medical
   - AWS Textract
   - AWS HealthLake
   - Amazon DynamoDB
   - Amazon Cognito
   - Amazon API Gateway
   - Amazon S3
   - Amazon CloudFront
   - AWS CDK
   - React
   - TypeScript
   - Python
   - FHIR R4

   **Links:**

   - GitHub Repository 1 (Frontend): https://github.com/VaidhyaMegha/trial-compass-pro
   - GitHub Repository 2 (Backend): https://github.com/VaidhyaMegha/aws-trial-enrollment-agent
   - Live Demo: https://enrollment.samyama.care
   - Video Demo: [YouTube URL - to be added]

   **Description:**

   - Paste the prepared project description (see Step 1.2)

   **Image/Screenshots:**

   - Upload 5-6 key screenshots:
     1. Dashboard showing three persona options
     2. StudyAdmin: Protocol upload interface
     3. CRC: Patient eligibility check with AI reasoning
     4. PI: Enrollment dashboard with metrics
     5. Patient-protocol match visualization
     6. Architecture diagram

### Step 3: Select Prize Categories

Check the boxes for categories we're eligible for:

- [X] **Grand Prize** ($16,000 / $9,000 / $5,000)
- [X] **Best Amazon Bedrock Application** ($3,000)
  - Strong candidate: Core AI reasoning with Mistral Large 2
- [ ] **Best Amazon Bedrock AgentCore Implementation** ($3,000)
  - Only if we use Bedrock AgentCore (we don't currently)
- [ ] **Best Amazon Q Application** ($3,000)
  - We haven't integrated Amazon Q
- [ ] **Best Amazon Nova Act Integration** ($3,000)
  - Only if we integrate Nova Act
- [ ] **Best Strands SDK Implementation** ($3,000)
  - Only if we use Strands SDK

**Recommendation:** Focus on **Grand Prize** and **Best Amazon Bedrock Application**

### Step 4: Review and Submit

1. **Preview submission** - Check all links work
2. **Proofread** all text
3. **Test video** plays correctly
4. **Verify GitHub repos** are public with clear README
5. **Click "Submit"** before deadline: **October 20, 2025, 5:00 PM PDT**

### Step 5: Post-Submission (Optional but Recommended)

1. **Share on social media:**

   - Twitter/X with #AWSAgentHackathon
   - LinkedIn with project details
   - Tag @awscloud

2. **Engage with community:**

   - Comment on other submissions
   - Share learning insights

---

## 🏆 Prize Categories We're Eligible For

### 1. Grand Prize (Top 3)

- **1st Place:** $16,000 + AWS marketplace/marketing support
- **2nd Place:** $9,000 + support
- **3rd Place:** $5,000 + support

**Why We Qualify:**

- Comprehensive AWS AI integration with Mistral Large 2
- Real-world healthcare impact
- Production-ready architecture
- Novel problem-solving approach
- Three distinct user personas with comprehensive workflows

**Our Strengths:**

- Multi-service orchestration (Bedrock/Mistral, Comprehend Medical, Textract, HealthLake)
- HIPAA-compliant healthcare solution
- Fully deployed and functional
- Measurable impact on clinical trial efficiency
- Role-based access control with Cognito

### 2. Best Amazon Bedrock Application ($3,000)

**Why We're a Strong Candidate:**

- Core AI reasoning powered by Bedrock with **Mistral Large 2**
- Multiple Bedrock use cases:
  - Protocol criteria extraction from natural language
  - Intelligent eligibility matching
  - Confidence scoring and reasoning explanations
- Advanced prompt engineering for medical domain
- Production deployment at scale
- Integration with Comprehend Medical for medical NER

**Key Differentiators:**

- Healthcare-specific LLM application using Mistral
- Integration with medical NLP services
- FHIR R4 standard compliance
- Real clinical trial workflows
- 11 FHIR resource type support

---

## 👥 Three User Personas & Workflows

### 1. Clinical Research Coordinator (CRC)

**Role:** Screens patients for clinical trial eligibility

**Primary Tasks:**

- Search for eligible patients in HealthLake
- Run eligibility checks against trial protocols
- Review patient matches with confidence scores
- Track screening metrics

**Key Features:**

- Quick access to eligibility check interface
- Patient search functionality
- Recent matches dashboard
- Success rate tracking

**User Flow:**

```
CRC Login → Dashboard (Patients Screened, Active Matches, Success Rate)
         → Search Protocols
         → Select Patient from HealthLake
         → Run Eligibility Check (AI powered by Mistral)
         → View Results with confidence scores
         → Export PDF report
```

**Dashboard Metrics:**

- Patients Screened: 247
- Active Matches: 42
- Success Rate: 78%

### 2. Study Administrator (StudyAdmin)

**Role:** Manages clinical trial protocols and system configuration

**Primary Tasks:**

- Upload and process protocol PDFs
- Monitor protocol processing pipeline
- View system-wide statistics
- Manage trial inventory

**Key Features:**

- Protocol upload with drag-and-drop
- Processing status monitoring
- Protocol status distribution charts
- Recent protocol activity tracking

**User Flow:**

```
StudyAdmin Login → Dashboard (Total/Active/Processing/Failed Protocols)
                → Upload Protocol PDF
                → Textract extraction + Mistral parsing
                → View parsed criteria
                → Monitor processing pipeline
                → Manage protocol library
```

**Dashboard Metrics:**

- Total Protocols: 10
- Active Protocols: 8
- Processing: 1
- Failed: 1

**Processing Pipeline:**

```
PDF Upload (S3) → Textract Processor → Section Classifier (Comprehend Medical)
                → Criteria Parser (Mistral) → DynamoDB Cache
```

### 3. Principal Investigator (PI)

**Role:** Reviews patient matches and approves enrollments

**Primary Tasks:**

- Monitor trial enrollment metrics
- Review pending patient matches
- Approve/reject enrollments
- Track enrollment progress

**Key Features:**

- Enrollment dashboard with real-time metrics
- Match confidence distribution charts
- Pending review queue
- Trial-specific enrollment tracking
- Export enrollment summaries

**User Flow:**

```
PI Login → Dashboard (Active Trials, Total Enrolled, Pending Review, Match Rate)
        → View Match Confidence Distribution
        → Review Active Trial Enrollment Progress
        → Approve/Reject Pending Matches
        → Export Enrollment Summary
```

**Dashboard Metrics:**

- Active Trials: 5
- Total Enrolled: 38
- Pending Review: 12
- Match Rate: 67%

**Confidence Distribution:**

- High (≥80%): Green
- Medium (50-79%): Yellow
- Low (<50%): Red

---

## 🎯 Judging Criteria Alignment

### 1. Potential Value/Impact (20%)

**What Judges Look For:**

- Solves real-world problem
- Measurable outcomes
- Scalability potential

**Our Story:**

- **Problem:** Clinical trials fail 85% of the time due to slow patient enrollment
- **Solution:** Automates matching with Mistral Large 2, reducing enrollment time from weeks to minutes
- **Impact:**
  - Accelerates drug development timelines
  - Improves patient access to treatments
  - Reduces trial costs by millions
  - Supports 11 FHIR resource types
  - Serves 3 distinct user personas
- **Scale:** Applicable to thousands of trials globally

**Evidence:**

- Live deployment with real protocol data
- Support for all major FHIR resources (Patient, Condition, Observation, MedicationStatement, AllergyIntolerance, Procedure, etc.)
- Production-grade AWS architecture
- Role-based access control

### 2. Creativity (10%)

**What Judges Look For:**

- Novel approach to problem
- Innovative use of technology

**Our Innovation:**

- **Novel Approach:** First AI agent for HIPAA-compliant FHIR-based trial matching using Mistral Large 2
- **Creative Tech Use:**
  - Multi-modal AI (Bedrock/Mistral + Comprehend Medical + Textract)
  - Automated medical reasoning pipeline
  - FHIR-native patient data integration with HealthLake
- **Unique Features:**
  - Three distinct user personas with tailored workflows
  - Confidence scoring with explainable reasoning
  - Async document processing pipeline with orchestration
  - Theme-aware branding (light/dark mode with Samyama.ai logos)
  - PDF export with company branding

### 3. Technical Execution (50%) - MOST IMPORTANT

**What Judges Look For:**

- Architecture quality
- Code reproducibility
- Correct use of required technologies
- Best practices

**Our Strengths:**

**Architecture:**

- ✅ Infrastructure as Code (AWS CDK Python)
- ✅ Serverless architecture (10 Lambda functions + DynamoDB)
- ✅ Microservices pattern with clear separation
- ✅ Event-driven architecture (S3 triggers → Lambda pipeline)
- ✅ Security best practices (IAM roles, Cognito, JWT authorizer)
- ✅ FHIR R4 compliance

**Reproducibility:**

- ✅ Complete source code in public repos
- ✅ Detailed README with step-by-step setup
- ✅ CDK deployment scripts (`infrastructure/app.py`)
- ✅ Environment configuration examples (`.env.example`)
- ✅ Comprehensive deployment documentation

**Required Tech Usage:**

- ✅ Amazon Bedrock (Mistral Large 2) - Core reasoning engine
- ✅ AWS Lambda - Agent execution (10 functions)
- ✅ Multiple AWS services properly integrated
- ✅ Agent demonstrates autonomy and reasoning

**Best Practices:**

- ✅ AWS Lambda Powertools for observability
- ✅ Error handling and retry logic
- ✅ Async processing for long operations (Textract)
- ✅ Caching strategy (DynamoDB)
- ✅ HIPAA compliance considerations
- ✅ Frontend/backend separation
- ✅ CloudWatch logging and tracing

**Code Quality:**

```python
# Example: Mistral model configuration
def parse_criteria_with_bedrock(
    criteria_text: str,
    model_id: str = "mistral.mistral-large-2402-v1:0"
) -> List[Dict[str, Any]]:
    """
    Use Bedrock to parse eligibility criteria into structured format.

    Args:
        criteria_text: Free-text eligibility criteria
        model_id: Bedrock model ID (default: Mistral Large)
    """
```

### 4. Functionality (10%)

**What Judges Look For:**

- Agent works reliably
- Demonstrates scalability
- Handles edge cases

**Our Capabilities:**

- ✅ **Reliability:** Production deployment with error handling
- ✅ **Performance:** Async processing, caching, sub-minute eligibility checks
- ✅ **Scalability:** Serverless auto-scaling, CDN for frontend
- ✅ **Robustness:** Handles missing data, confidence thresholds, retry logic
- ✅ **Edge Cases:** Ambiguous criteria, partial matches, empty results
- ✅ **Multi-tenancy:** Three user personas with role-based access

**Supported FHIR Resources (11 types):**

1. Patient (demographics, birthDate)
2. Condition (diagnoses, ICD-10)
3. Observation (lab values, vital signs)
4. MedicationStatement (current medications)
5. AllergyIntolerance (allergies)
6. Procedure (surgical history)
7. Immunization (vaccination records)
8. DiagnosticReport (lab reports)
9. Encounter (healthcare visits)
10. CarePlan (treatment plans)
11. FamilyMemberHistory (family history)

### 5. Demo Presentation (10%)

**What Judges Look For:**

- Clear end-to-end workflow
- Professional presentation
- Demonstrates key features

**Our Demo Plan:**

- ✅ **Clear narrative:** Problem → Solution → Three Personas → Impact
- ✅ **Live demonstration:** Actual deployment, not mockup
- ✅ **Complete workflow:** Upload → Process → Match → Review → Export
- ✅ **AI highlights:** Show Mistral reasoning, Comprehend Medical entities, confidence scores
- ✅ **Professional quality:** Smooth recording, clear audio, Samyama branding
- ✅ **Persona demonstration:** Show CRC, StudyAdmin, and PI workflows

---

## 📋 Next Steps & Action Items

### Immediate Actions (Before Submission)

#### 1. Create Architecture Diagram (Priority: HIGH)

- [ ] Design comprehensive architecture diagram
- [ ] Show all AWS services and data flow
- [ ] Highlight three user personas and their access patterns
- [ ] Show Mistral Large 2 integration
- [ ] Export as high-res PNG/SVG
- [ ] Save to: `aws-trial-enrollment-agent/docs/architecture-diagram.png`

**Tools:**

- draw.io (free, recommended)
- Lucidchart
- AWS Architecture Icons: https://aws.amazon.com/architecture/icons/

**Elements to include:**

```
User Personas:
├── CRC (Clinical Research Coordinator) - Patient Screening
├── StudyAdmin (Study Administrator) - Protocol Management
└── PI (Principal Investigator) - Match Review & Enrollment

Frontend Layer:
├── CloudFront CDN
├── S3 Static Website
└── React Application (TypeScript)
    ├── CRC Dashboard
    ├── StudyAdmin Dashboard
    └── PI Dashboard

API Layer:
├── API Gateway (REST API)
├── Lambda Authorizer (JWT)
└── Cognito User Pool (3 groups: CRC, StudyAdmin, PI)

AI Agent Layer:
├── Lambda: Textract Processor (PDF OCR)
├── Lambda: Section Classifier (Comprehend Medical)
├── Lambda: Protocol Orchestrator (Pipeline)
├── Lambda: Criteria Parser (Bedrock + Mistral Large 2)
├── Lambda: FHIR Search (HealthLake)
├── Lambda: Patient Manager
├── Lambda: Protocol Manager
├── Lambda: Match Manager
└── Lambda: Admin Manager

AI Services:
├── Amazon Bedrock (Mistral Large 2 - mistral.mistral-large-2402-v1:0)
├── AWS Textract (PDF OCR)
├── AWS Comprehend Medical (Medical NER)
└── AWS HealthLake (FHIR R4 datastore)

Data Layer:
├── DynamoDB: CriteriaCacheTable (parsed criteria)
├── DynamoDB: EvaluationResultsTable (eligibility results)
├── DynamoDB: MatchesTable (patient-protocol matches with GSIs)
├── S3: Protocol Documents Bucket
└── HealthLake: Patient FHIR Data (11 resource types)

Monitoring:
└── CloudWatch (Logs, Metrics, Tracing)
```

#### 2. Write Project Description (Priority: HIGH)

- [ ] Draft compelling 500-1000 word description
- [ ] Highlight three user personas
- [ ] Explain Mistral Large 2 integration
- [ ] Include measurable outcomes
- [ ] Save to: `aws-trial-enrollment-agent/docs/project-description.md`

**Structure:**

```markdown
# AWS Trial Enrollment System - AI-Powered Clinical Trial Matching

## The Problem

[Clinical trial enrollment challenges, statistics, impact]

## Our Solution

[AI agent overview, Mistral Large 2, AWS services, key capabilities]

## Three User Personas

### Clinical Research Coordinator (CRC)

[Patient screening workflow, features, metrics]

### Study Administrator (StudyAdmin)

[Protocol management workflow, processing pipeline]

### Principal Investigator (PI)

[Match review workflow, enrollment dashboard]

## How It Works

[Step-by-step user journey with AI agent actions]

## Technical Innovation

[Architecture highlights, Mistral integration, FHIR support]

## Real-World Impact

[Measurable benefits, scalability, future potential]

## Built With AWS

[Service list with justification for each]
```

#### 3. Record Demo Video (Priority: HIGH)

- [ ] Write video script
- [ ] Prepare test data (protocol + patients)
- [ ] Record screen capture (1080p minimum)
- [ ] Add voiceover narration
- [ ] Show all three user personas
- [ ] Edit and add titles/transitions
- [ ] Upload to YouTube (unlisted)
- [ ] Test video plays correctly
- [ ] Save YouTube URL

**Video Script Outline:**

```
[00:00-00:15] Hook & Problem
"85% of clinical trials fail due to slow patient enrollment.
 What if AI could match patients to trials in minutes?"

[00:15-00:45] Solution Introduction
"AWS Trial Enrollment System is an AI agent powered by Amazon Bedrock
 with Mistral Large 2 that automates clinical trial eligibility screening.
 Three personas: CRC screens patients, StudyAdmin manages protocols,
 PI reviews and approves enrollments."

[00:45-02:30] Live Demo
1. Login (Cognito authentication with role selection)
2. StudyAdmin Flow:
   - Upload Protocol PDF
   - Show AWS Textract OCR extraction
   - Show Mistral parsing criteria
   - View processing pipeline
3. CRC Flow:
   - Select Patient from HealthLake (show FHIR resources)
   - Run Eligibility Check
   - Show AI agent reasoning (Mistral)
   - Medical entity extraction (Comprehend Medical)
   - Confidence scores and explanations
4. PI Flow:
   - View enrollment dashboard
   - Match confidence distribution
   - Review pending matches
   - Export enrollment summary
5. Export PDF Report with Samyama.ai branding

[02:30-03:00] Impact & Call to Action
"From weeks to minutes. From manual to automated.
 Three personas working seamlessly with AI.
 AWS Trial Enrollment System accelerates drug discovery and
 improves patient access to life-saving treatments."
```

#### 4. Gather Screenshots (Priority: MEDIUM)

- [ ] Login page with Samyama.ai branding
- [ ] CRC Dashboard with patient screening metrics
- [ ] StudyAdmin Dashboard with protocol status
- [ ] PI Dashboard with enrollment metrics
- [ ] Protocol upload interface with Textract processing
- [ ] Patient selection from HealthLake with FHIR resources
- [ ] Eligibility results with Mistral AI reasoning
- [ ] Match visualization with confidence scores
- [ ] PDF export sample with Samyama branding
- [ ] Architecture diagram

#### 5. Update GitHub READMEs (Priority: MEDIUM)

- [ ] Ensure both repos have comprehensive READMEs
- [ ] Update project name to "AWS Trial Enrollment System"
- [ ] Mention Mistral Large 2 as the LLM
- [ ] Add three user personas section
- [ ] Add "AWS AI Agent Hackathon" badge/mention
- [ ] Include setup/deployment instructions
- [ ] Add architecture overview
- [ ] Link to live demo
- [ ] Add screenshots

#### 6. Final Testing (Priority: HIGH)

- [ ] Test all three user personas (CRC, StudyAdmin, PI)
- [ ] Verify complete workflow end-to-end
- [ ] Test protocol upload and Mistral parsing
- [ ] Test patient eligibility check with HealthLake
- [ ] Verify all APIs are working
- [ ] Check CloudFront deployment is live
- [ ] Test on different browsers
- [ ] Mobile responsiveness check
- [ ] Verify PDF export with Samyama branding

---

## 📊 Competition Strategy

### Our Competitive Advantages

1. **Real Healthcare Impact**

   - Addresses critical industry problem
   - HIPAA-compliant solution
   - Production-ready architecture
   - 11 FHIR resource types supported

2. **Comprehensive AWS Integration**

   - 10+ AWS services
   - Multi-modal AI (Bedrock/Mistral + Comprehend Medical + Textract)
   - Serverless scalability
   - FHIR-native integration with HealthLake

3. **Technical Excellence**

   - Infrastructure as Code (AWS CDK Python)
   - Best practices throughout
   - Fully deployed and functional
   - Three user personas with tailored workflows

4. **Innovation**

   - FHIR R4-native patient matching
   - Explainable AI reasoning with Mistral
   - Healthcare-specific LLM application
   - Role-based access control

### Target Prize Categories

**Primary Target:** Grand Prize (Top 3)

- Confidence: HIGH
- Reasoning: Strong technical execution + real-world impact + comprehensive multi-persona system

**Secondary Target:** Best Amazon Bedrock Application

- Confidence: VERY HIGH
- Reasoning: Mistral Large 2 is core to our AI agent, healthcare domain expertise, production deployment

---

## ✅ Submission Status

**Last Updated:** October 16, 2025

### Completed

- ✅ Project fully developed and deployed
- ✅ Frontend: https://enrollment.samyama.care (custom domain)
- ✅ Backend: API Gateway + 10 Lambda functions
- ✅ Mistral Large 2 integration via Bedrock
- ✅ Three user personas (CRC, StudyAdmin, PI)
- ✅ 11 FHIR resource types supported
- ✅ Samyama.ai branding integrated
- ✅ GitHub repositories public
- ✅ Git workflow (feature branch + PR)
- ✅ Custom domain setup with Route 53

### In Progress

- 🔄 Architecture diagram (showing three personas)
- 🔄 Project description (highlighting Mistral)
- 🔄 Demo video (demonstrating all personas)
- 🔄 Screenshots collection

### Pending

- ⏳ Devpost submission form
- ⏳ Final testing
- ⏳ Submission (Deadline: October 20, 5:00 PM PDT)

---

## 🚀 Let's Win This!

**Our Mission:** Demonstrate how AI agents on AWS with Mistral Large 2 can transform healthcare and save lives.

**Our Advantage:** Real-world solution, production deployment, comprehensive AWS integration, three distinct user personas.

**Our Goal:** Grand Prize + Best Amazon Bedrock Application

**Time to Submission:** 4 days (as of October 16, 2025)

---

**Good luck, Team Samyama! 🎉**
