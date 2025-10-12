#!/usr/bin/env python3
"""
AWS CDK Infrastructure for Trial Enrollment Agent

This stack deploys:
- Lambda functions for Criteria Parser and FHIR Search
- API Gateway for tool endpoints
- DynamoDB for caching
- IAM roles and policies
- CloudWatch logging
"""

import os
from aws_cdk import (
    App,
    Stack,
    Duration,
    RemovalPolicy,
    aws_lambda as lambda_,
    aws_apigateway as apigw,
    aws_dynamodb as dynamodb,
    aws_iam as iam,
    aws_logs as logs,
    aws_s3 as s3,
    aws_s3_notifications as s3n,
    CfnOutput
)
from constructs import Construct


class TrialEnrollmentAgentStack(Stack):
    """
    CDK Stack for Trial Enrollment Agent infrastructure.
    """

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # ========================================
        # DynamoDB Tables
        # ========================================

        # Table for caching parsed criteria
        criteria_cache_table = dynamodb.Table(
            self, "CriteriaCacheTable",
            partition_key=dynamodb.Attribute(
                name="trial_id",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,  # For dev/hackathon only
            point_in_time_recovery=True,
            encryption=dynamodb.TableEncryption.AWS_MANAGED
        )

        # Table for storing evaluation results
        evaluation_results_table = dynamodb.Table(
            self, "EvaluationResultsTable",
            partition_key=dynamodb.Attribute(
                name="evaluation_id",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="timestamp",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
            point_in_time_recovery=True,
            encryption=dynamodb.TableEncryption.AWS_MANAGED
        )

        # ========================================
        # S3 Bucket for Protocol Documents
        # ========================================

        # Bucket for storing protocol PDFs
        # Create new bucket (allows event notifications)
        protocol_bucket = s3.Bucket(
            self, "ProtocolDocumentsBucket",
            bucket_name=f"trial-enrollment-protocols-{self.account}",
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.DESTROY,  # For dev/hackathon only
            auto_delete_objects=True,  # Clean up on stack deletion
            versioning=False,
            enforce_ssl=True
        )

        # ========================================
        # IAM Policies
        # ========================================

        # Bedrock access policy
        bedrock_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "bedrock:InvokeModel",
                "bedrock:InvokeModelWithResponseStream"
            ],
            resources=[
                f"arn:aws:bedrock:{self.region}::foundation-model/amazon.titan-text-express-v1",
                f"arn:aws:bedrock:{self.region}::foundation-model/amazon.titan-*"
            ]
        )

        # Textract access policy
        textract_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "textract:StartDocumentAnalysis",
                "textract:GetDocumentAnalysis",
                "textract:StartDocumentTextDetection",
                "textract:GetDocumentTextDetection"
            ],
            resources=["*"]
        )

        # Comprehend Medical access policy
        comprehend_medical_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "comprehendmedical:DetectEntitiesV2",
                "comprehendmedical:InferICD10CM",
                "comprehendmedical:InferRxNorm",
                "comprehendmedical:DetectPHI"
            ],
            resources=["*"]
        )

        # HealthLake access policy (optional, if using HealthLake)
        healthlake_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "healthlake:ReadResource",
                "healthlake:SearchWithGet",
                "healthlake:SearchWithPost"
            ],
            resources=["*"]  # Scope to specific datastore in production
        )

        # ========================================
        # Lambda Functions
        # ========================================

        # Criteria Parser Lambda
        criteria_parser_function = lambda_.Function(
            self, "CriteriaParserFunction",
            runtime=lambda_.Runtime.PYTHON_3_11,
            code=lambda_.Code.from_asset("../src/lambda/criteria_parser"),
            handler="handler.lambda_handler",
            function_name="TrialEnrollment-CriteriaParser",
            timeout=Duration.seconds(60),
            memory_size=512,
            environment={
                "CRITERIA_CACHE_TABLE": criteria_cache_table.table_name,
                "POWERTOOLS_SERVICE_NAME": "criteria-parser",
                "LOG_LEVEL": "INFO"
            },
            log_retention=logs.RetentionDays.ONE_WEEK
        )

        # Grant permissions
        criteria_parser_function.add_to_role_policy(bedrock_policy)
        criteria_cache_table.grant_read_write_data(criteria_parser_function)

        # FHIR Search Lambda
        fhir_search_function = lambda_.Function(
            self, "FHIRSearchFunction",
            runtime=lambda_.Runtime.PYTHON_3_11,
            code=lambda_.Code.from_asset("../src/lambda/fhir_search"),
            handler="handler.lambda_handler",
            function_name="TrialEnrollment-FHIRSearch",
            timeout=Duration.seconds(60),
            memory_size=512,
            environment={
                "FHIR_ENDPOINT": os.environ.get("FHIR_ENDPOINT", "http://hapi.fhir.org/baseR4"),
                "USE_HEALTHLAKE": "false",  # Set to true when HealthLake is configured
                "POWERTOOLS_SERVICE_NAME": "fhir-search",
                "LOG_LEVEL": "INFO"
            },
            log_retention=logs.RetentionDays.ONE_WEEK
        )

        # Grant permissions (uncomment when HealthLake is used)
        # fhir_search_function.add_to_role_policy(healthlake_policy)

        # Protocol Orchestrator Lambda (declare first, used by Textract Processor)
        protocol_orchestrator_function = lambda_.Function(
            self, "ProtocolOrchestratorFunction",
            runtime=lambda_.Runtime.PYTHON_3_11,
            code=lambda_.Code.from_asset("../src/lambda/protocol_orchestrator"),
            handler="handler.lambda_handler",
            function_name="TrialEnrollment-ProtocolOrchestrator",
            timeout=Duration.minutes(5),  # 5 minutes for full pipeline
            memory_size=512,
            environment={
                "CRITERIA_CACHE_TABLE": criteria_cache_table.table_name,
                "MAX_RETRIES": "3",
                "RETRY_DELAY_SECONDS": "2",
                "POWERTOOLS_SERVICE_NAME": "protocol-orchestrator",
                "LOG_LEVEL": "INFO"
                # SECTION_CLASSIFIER_FUNCTION and PARSE_CRITERIA_API_ENDPOINT set later
            },
            log_retention=logs.RetentionDays.ONE_WEEK
        )

        # Textract Processor Lambda
        textract_processor_function = lambda_.Function(
            self, "TextractProcessorFunction",
            runtime=lambda_.Runtime.PYTHON_3_11,
            code=lambda_.Code.from_asset("../src/lambda/textract_processor"),
            handler="handler.lambda_handler",
            function_name="TrialEnrollment-TextractProcessor",
            timeout=Duration.minutes(10),  # Long timeout for large PDFs
            memory_size=1024,  # Higher memory for faster processing
            environment={
                "TEXTRACT_MAX_WAIT_TIME": "300",  # 5 minutes
                "TEXTRACT_POLL_INTERVAL": "5",  # 5 seconds
                "PROTOCOL_ORCHESTRATOR_FUNCTION": protocol_orchestrator_function.function_name,
                "AUTO_TRIGGER_ORCHESTRATOR": "true",  # Enable automatic pipeline trigger
                "POWERTOOLS_SERVICE_NAME": "textract-processor",
                "LOG_LEVEL": "INFO"
            },
            log_retention=logs.RetentionDays.ONE_WEEK
        )

        # Grant permissions
        textract_processor_function.add_to_role_policy(textract_policy)
        protocol_bucket.grant_read(textract_processor_function)
        # Allow Textract Processor to invoke Protocol Orchestrator
        protocol_orchestrator_function.grant_invoke(textract_processor_function)

        # Add S3 event trigger for automatic processing
        protocol_bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED,
            s3n.LambdaDestination(textract_processor_function),
            s3.NotificationKeyFilter(suffix='.pdf')
        )

        # Section Classifier Lambda
        section_classifier_function = lambda_.Function(
            self, "SectionClassifierFunction",
            runtime=lambda_.Runtime.PYTHON_3_11,
            code=lambda_.Code.from_asset("../src/lambda/section_classifier"),
            handler="handler.lambda_handler",
            function_name="TrialEnrollment-SectionClassifier",
            timeout=Duration.seconds(120),  # 2 minutes
            memory_size=512,
            environment={
                "MIN_CRITERION_LENGTH": "10",
                "MAX_CRITERION_LENGTH": "500",
                "USE_COMPREHEND_MEDICAL": "true",
                "POWERTOOLS_SERVICE_NAME": "section-classifier",
                "LOG_LEVEL": "INFO"
            },
            log_retention=logs.RetentionDays.ONE_WEEK
        )

        # Grant permissions
        section_classifier_function.add_to_role_policy(comprehend_medical_policy)

        # Update Protocol Orchestrator environment with Section Classifier function name
        protocol_orchestrator_function.add_environment(
            "SECTION_CLASSIFIER_FUNCTION",
            section_classifier_function.function_name
        )

        # Grant permissions to Protocol Orchestrator
        # Allow orchestrator to invoke Section Classifier
        section_classifier_function.grant_invoke(protocol_orchestrator_function)
        # Allow orchestrator to read/write DynamoDB
        criteria_cache_table.grant_read_write_data(protocol_orchestrator_function)

        # ========================================
        # API Gateway
        # ========================================

        # REST API
        api = apigw.RestApi(
            self, "TrialEnrollmentAPI",
            rest_api_name="Trial Enrollment Agent API",
            description="API for Trial Enrollment Agent tools",
            deploy_options=apigw.StageOptions(
                stage_name="prod",
                logging_level=apigw.MethodLoggingLevel.INFO,
                data_trace_enabled=True,
                metrics_enabled=True
            ),
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=apigw.Cors.ALL_ORIGINS,
                allow_methods=apigw.Cors.ALL_METHODS,
                allow_headers=["Content-Type", "Authorization"]
            )
        )

        # Criteria Parser endpoint
        parser_resource = api.root.add_resource("parse-criteria")
        parser_integration = apigw.LambdaIntegration(criteria_parser_function)
        parser_resource.add_method("POST", parser_integration)

        # FHIR Search endpoint
        search_resource = api.root.add_resource("check-criteria")
        search_integration = apigw.LambdaIntegration(fhir_search_function)
        search_resource.add_method("POST", search_integration)

        # Health check endpoint
        health_resource = api.root.add_resource("health")
        health_resource.add_method(
            "GET",
            apigw.MockIntegration(
                integration_responses=[{
                    "statusCode": "200",
                    "responseTemplates": {
                        "application/json": '{"status": "healthy"}'
                    }
                }],
                request_templates={
                    "application/json": '{"statusCode": 200}'
                }
            ),
            method_responses=[{"statusCode": "200"}]
        )

        # Update Protocol Orchestrator with API endpoint
        protocol_orchestrator_function.add_environment(
            "PARSE_CRITERIA_API_ENDPOINT",
            f"{api.url}parse-criteria"
        )

        # ========================================
        # Outputs
        # ========================================

        CfnOutput(
            self, "APIEndpoint",
            value=api.url,
            description="API Gateway endpoint URL"
        )

        CfnOutput(
            self, "CriteriaParserFunctionName",
            value=criteria_parser_function.function_name,
            description="Criteria Parser Lambda function name"
        )

        CfnOutput(
            self, "FHIRSearchFunctionName",
            value=fhir_search_function.function_name,
            description="FHIR Search Lambda function name"
        )

        CfnOutput(
            self, "CriteriaCacheTableName",
            value=criteria_cache_table.table_name,
            description="DynamoDB table for criteria cache"
        )

        CfnOutput(
            self, "EvaluationResultsTableName",
            value=evaluation_results_table.table_name,
            description="DynamoDB table for evaluation results"
        )

        CfnOutput(
            self, "ProtocolBucketName",
            value=protocol_bucket.bucket_name,
            description="S3 bucket for protocol documents"
        )

        CfnOutput(
            self, "TextractProcessorFunctionName",
            value=textract_processor_function.function_name,
            description="Textract Processor Lambda function name"
        )

        CfnOutput(
            self, "SectionClassifierFunctionName",
            value=section_classifier_function.function_name,
            description="Section Classifier Lambda function name"
        )

        CfnOutput(
            self, "ProtocolOrchestratorFunctionName",
            value=protocol_orchestrator_function.function_name,
            description="Protocol Orchestrator Lambda function name"
        )


# ========================================
# App
# ========================================

app = App()

TrialEnrollmentAgentStack(
    app, "TrialEnrollmentAgentStack",
    description="Infrastructure for AWS Trial Enrollment Agent",
    env={
        "region": os.environ.get("CDK_DEFAULT_REGION", "us-east-1"),
        "account": os.environ.get("CDK_DEFAULT_ACCOUNT")
    }
)

app.synth()
