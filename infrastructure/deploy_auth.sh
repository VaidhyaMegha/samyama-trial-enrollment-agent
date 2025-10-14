#!/bin/bash
################################################################################
# Deploy Authentication Infrastructure
#
# This script:
# 1. Loads Cognito configuration from cognito-config.json
# 2. Deploys Lambda Authorizer with CDK
# 3. Tests authorization with sample JWT tokens
################################################################################

set -e  # Exit on error

echo "======================================================================"
echo "Deploying Authentication Infrastructure"
echo "======================================================================"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if cognito-config.json exists
if [ ! -f "cognito-config.json" ]; then
    echo -e "${RED}❌ Error: cognito-config.json not found!${NC}"
    echo "   Please run 'python3 cognito_setup.py' first."
    exit 1
fi

# Load Cognito configuration
echo -e "\n${GREEN}📋 Loading Cognito Configuration...${NC}"
USER_POOL_ID=$(jq -r '.UserPoolId' cognito-config.json)
CLIENT_ID=$(jq -r '.ClientId' cognito-config.json)
REGION=$(jq -r '.Region' cognito-config.json)

echo "   User Pool ID: $USER_POOL_ID"
echo "   Client ID: $CLIENT_ID"
echo "   Region: $REGION"

# Export environment variables for CDK
export COGNITO_USER_POOL_ID=$USER_POOL_ID
export COGNITO_CLIENT_ID=$CLIENT_ID
export CDK_DEFAULT_REGION=$REGION

# Install dependencies for Lambda Authorizer
echo -e "\n${GREEN}📦 Installing Lambda Authorizer dependencies...${NC}"
cd ../src/lambda/authorizer
pip3 install -r requirements.txt -t . --upgrade
cd ../../../infrastructure

# Bootstrap CDK (if not already done)
echo -e "\n${GREEN}🚀 Bootstrapping CDK (if needed)...${NC}"
cdk bootstrap aws://$(aws sts get-caller-identity --query Account --output text)/$REGION || true

# Synthesize CDK stack
echo -e "\n${GREEN}🔨 Synthesizing CDK Stack...${NC}"
cdk synth

# Deploy CDK stack
echo -e "\n${YELLOW}🚀 Deploying CDK Stack...${NC}"
echo "   This may take 5-10 minutes..."
cdk deploy --require-approval never

# Get API Gateway URL
echo -e "\n${GREEN}📍 Retrieving API Gateway URL...${NC}"
API_URL=$(aws cloudformation describe-stacks \
    --stack-name TrialEnrollmentAgentStack \
    --query 'Stacks[0].Outputs[?OutputKey==`APIEndpoint`].OutputValue' \
    --output text \
    --region $REGION)

echo -e "${GREEN}✅ API Gateway URL: $API_URL${NC}"

# Update cognito-config.json with API URL
echo -e "\n${GREEN}💾 Updating cognito-config.json with API URL...${NC}"
jq --arg api_url "$API_URL" '. + {ApiUrl: $api_url}' cognito-config.json > cognito-config.tmp.json
mv cognito-config.tmp.json cognito-config.json

echo -e "\n======================================================================"
echo -e "${GREEN}✅ Authentication Infrastructure Deployed Successfully!${NC}"
echo "======================================================================"

echo -e "\n📋 Deployment Summary:"
echo "   User Pool ID: $USER_POOL_ID"
echo "   Client ID: $CLIENT_ID"
echo "   API Gateway URL: $API_URL"
echo "   Region: $REGION"

echo -e "\n🧪 Testing Instructions:"
echo "   1. Get JWT token by logging in with test credentials:"
echo "      - CRC: crc_test / TestCRC@2025!"
echo "      - StudyAdmin: studyadmin_test / TestAdmin@2025!"
echo "      - PI: pi_test / TestPI@2025!"
echo ""
echo "   2. Test protected endpoint:"
echo "      curl -X POST $API_URL/parse-criteria \\"
echo "           -H 'Authorization: Bearer <JWT_TOKEN>' \\"
echo "           -H 'Content-Type: application/json' \\"
echo "           -d '{\"trial_id\": \"test\", \"criteria_text\": \"Age >= 18\"}'"
echo ""
echo "   3. Without token (should fail with 401):"
echo "      curl -X POST $API_URL/parse-criteria \\"
echo "           -H 'Content-Type: application/json' \\"
echo "           -d '{\"trial_id\": \"test\", \"criteria_text\": \"Age >= 18\"}'"

echo -e "\n${YELLOW}⚠️  Next Steps:${NC}"
echo "   1. Update Amplify frontend with API Gateway URL"
echo "   2. Test authentication flow end-to-end"
echo "   3. Verify RBAC is working correctly"

echo ""
