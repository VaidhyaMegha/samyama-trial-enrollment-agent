#!/bin/bash
# Deploy the complete end-to-end protocol processing pipeline

set -e  # Exit on error

echo "=========================================="
echo "Protocol Processing Pipeline Deployment"
echo "=========================================="
echo ""

# Check AWS credentials
echo "Checking AWS credentials..."
if ! aws sts get-caller-identity &> /dev/null; then
    echo "❌ AWS credentials not configured. Please run: aws configure"
    exit 1
fi

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION=$(aws configure get region || echo "us-east-1")

echo "✅ AWS Account: $ACCOUNT_ID"
echo "✅ AWS Region: $REGION"
echo ""

# Deploy infrastructure
echo "Deploying infrastructure with CDK..."
cd infrastructure

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "Installing CDK dependencies..."
    npm install
fi

# Bootstrap CDK (if not already done)
echo "Bootstrapping CDK (if needed)..."
cdk bootstrap aws://$ACCOUNT_ID/$REGION || true

# Deploy the stack
echo ""
echo "Deploying TrialEnrollmentAgentStack..."
cdk deploy --require-approval never

echo ""
echo "=========================================="
echo "✅ Deployment Complete!"
echo "=========================================="
echo ""

# Extract outputs
echo "📋 Stack Outputs:"
aws cloudformation describe-stacks \
  --stack-name TrialEnrollmentAgentStack \
  --query 'Stacks[0].Outputs[*].[OutputKey,OutputValue]' \
  --output table

echo ""
echo "=========================================="
echo "🎯 Next Steps"
echo "=========================================="
echo ""
echo "1. Note your S3 bucket name from the outputs above"
echo ""
echo "2. Upload a protocol PDF:"
echo "   aws s3 cp your-protocol.pdf s3://trial-enrollment-protocols-$ACCOUNT_ID/"
echo ""
echo "3. Watch the pipeline in action:"
echo "   aws logs tail /aws/lambda/TrialEnrollment-TextractProcessor --follow"
echo ""
echo "4. View results in DynamoDB:"
echo "   TABLE_NAME=\$(aws cloudformation describe-stacks --stack-name TrialEnrollmentAgentStack --query 'Stacks[0].Outputs[?OutputKey==\`CriteriaCacheTableName\`].OutputValue' --output text)"
echo "   aws dynamodb get-item --table-name \$TABLE_NAME --key '{\"trial_id\": {\"S\": \"YOUR_TRIAL_ID\"}}'"
echo ""
echo "📖 See END_TO_END_PIPELINE_GUIDE.md for detailed instructions"
echo ""
