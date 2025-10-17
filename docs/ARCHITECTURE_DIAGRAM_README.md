# Architecture Diagram - AWS Trial Enrollment System

## File Location
- **Source File**: `architecture-diagram.drawio`
- **Export File**: `architecture-diagram.png` (to be generated)

## How to Open and Edit

### Option 1: draw.io Web (Easiest)
1. Go to: https://app.diagrams.net/
2. Click "Open Existing Diagram"
3. Navigate to this file: `architecture-diagram.drawio`
4. Edit and export

### Option 2: VS Code
1. Install "Draw.io Integration" extension
2. Open `architecture-diagram.drawio` directly in VS Code
3. Edit visually in the editor

## Enhanced Features

### ✅ Improved Frontend Layer
- **CloudFront** with global CDN icons
- **S3** with static hosting details
- **React App** showing all 3 dashboards (CRC, StudyAdmin, PI)
- **Live URL Box**: Prominent display of `enrollment.samyama.care` with:
  - 🔗 Link icon
  - ✓ Fully Operational status
  - ✓ HTTPS Secured badge
  - Custom Domain badge

### ✅ Enhanced Pipeline Visualization
5-phase document processing pipeline with visual flow:

1. **Phase 1: PDF Upload** (S3 Trigger)
2. **Phase 2: OCR Extraction** (AWS Textract)
3. **Phase 3: Medical NER** (Comprehend Medical)
4. **Phase 4: AI Parsing** (Bedrock - Mistral Large 2) - Highlighted
5. **Phase 5: Cache Storage** (DynamoDB)

Each phase has:
- Dedicated box with labels
- Connecting arrows with data labels
- Color coding (green for standard, darker green for AI core)

## Diagram Structure

### 6 Layers (Top to Bottom):

1. **User Personas Layer** (Blue)
   - CRC, StudyAdmin, PI with role descriptions

2. **Frontend Layer** (Orange)
   - CloudFront → S3 → React App → Live URL

3. **Auth & API Layer** (Purple)
   - Cognito (3 user groups) → API Gateway → Lambda Authorizer

4. **AI Agent Layer** (Green)
   - 5-phase pipeline (highlighted)
   - 10 Lambda functions displayed below

5. **AI Services Layer** (Pink)
   - Bedrock (Mistral Large 2) - Prominently featured
   - Textract, Comprehend Medical, HealthLake

6. **Data Persistence Layer** (Red)
   - 3 DynamoDB tables, S3 documents, CloudWatch

## Export Instructions

### To Export as PNG (for Devpost submission):

1. Open in draw.io
2. File → Export as → PNG
3. Settings:
   - ✅ **Transparent Background**: OFF (white background)
   - ✅ **Resolution**: 300 DPI or 4x scale
   - ✅ **Border Width**: 10px
   - ✅ **Selection Only**: OFF (full diagram)
   - ✅ **Include a copy of my diagram**: ON (for future editing)
4. Save as `architecture-diagram.png`

### To Export as SVG (for high quality):

1. File → Export as → SVG
2. Keep defaults
3. Save as `architecture-diagram.svg`

## Color Legend

- **Blue (#BBDEFB)**: User personas and interactions
- **Orange (#FF9800)**: Frontend and delivery
- **Purple (#9C27B0)**: Authentication and API
- **Green (#4CAF50)**: Lambda functions and AI agents
- **Light Green (#81C784)**: Pipeline phases
- **Dark Green (#66BB6A)**: Mistral AI processing (highlighted)
- **Pink (#E91E63)**: AI services
- **Red (#F44336)**: Data storage

## Key Highlights for Hackathon Judges

1. ✅ **Mistral Large 2** prominently featured in Phase 4 and AI Services layer
2. ✅ **5-phase automated pipeline** clearly visualized
3. ✅ **3 user personas** with distinct workflows
4. ✅ **11 AWS services** properly integrated
5. ✅ **Custom domain** professionally displayed
6. ✅ **FHIR R4** integration with HealthLake
7. ✅ **10 Lambda functions** for agent execution
8. ✅ **Production deployment** status indicated

## What to Do Next

1. Open `architecture-diagram.drawio` in draw.io
2. Review the diagram
3. Make any final adjustments
4. Export as PNG (300 DPI)
5. Use PNG in Devpost submission
6. Include in GitHub README

## Notes

- The diagram is production-ready and comprehensive
- All AWS services are represented
- Clear data flow from users → frontend → API → AI agents → services → data
- Pipeline shows autonomous agent workflow
- Custom domain `enrollment.samyama.care` featured prominently
