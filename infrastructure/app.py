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

        # Table for storing patient-protocol matches
        matches_table = dynamodb.Table(
            self, "MatchesTable",
            partition_key=dynamodb.Attribute(
                name="match_id",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
            point_in_time_recovery=True,
            encryption=dynamodb.TableEncryption.AWS_MANAGED
        )

        # Add GSI for querying matches by patient_id
        matches_table.add_global_secondary_index(
            index_name="PatientIndex",
            partition_key=dynamodb.Attribute(
                name="patient_id",
                type=dynamodb.AttributeType.STRING
            ),
            projection_type=dynamodb.ProjectionType.ALL
        )

        # Add GSI for querying matches by protocol_id
        matches_table.add_global_secondary_index(
            index_name="ProtocolIndex",
            partition_key=dynamodb.Attribute(
                name="protocol_id",
                type=dynamodb.AttributeType.STRING
            ),
            projection_type=dynamodb.ProjectionType.ALL
        )

        # ========================================
        # S3 Bucket for Protocol Documents
        # ========================================

        # Use existing bucket name
        bucket_name = f"trial-enrollment-protocols-{self.account}"

        # Import existing bucket (reference only, doesn't create or fail if missing)
        protocol_bucket = s3.Bucket.from_bucket_name(
            self, "ProtocolDocumentsBucket",
            bucket_name=bucket_name
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
                "healthlake:SearchWithPost",
                "healthlake:CreateResource",
                "healthlake:UpdateResource",
                "healthlake:DeleteResource"
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
                "FHIR_ENDPOINT": os.environ.get("FHIR_ENDPOINT", "https://healthlake.us-east-1.amazonaws.com/datastore/8640ed6b344b85e4729ac42df1c7d00e/r4"),
                "USE_HEALTHLAKE": "true",  # Using HealthLake
                "POWERTOOLS_SERVICE_NAME": "fhir-search",
                "LOG_LEVEL": "INFO"
            },
            log_retention=logs.RetentionDays.ONE_WEEK
        )

        # Grant HealthLake permissions
        fhir_search_function.add_to_role_policy(healthlake_policy)

        # Lambda Authorizer for JWT validation
        authorizer_function = lambda_.Function(
            self, "AuthorizerFunction",
            runtime=lambda_.Runtime.PYTHON_3_11,
            code=lambda_.Code.from_asset("../src/lambda/authorizer"),
            handler="lambda_function.lambda_handler",
            function_name="TrialEnrollment-Authorizer",
            timeout=Duration.seconds(30),
            memory_size=256,
            environment={
                "USER_POOL_ID": os.environ.get("COGNITO_USER_POOL_ID", "us-east-1_zLcYERVQI"),
                "CLIENT_ID": os.environ.get("COGNITO_CLIENT_ID", "37ef9023q0b9q6lsdvc5rlvpo1"),
                "POWERTOOLS_SERVICE_NAME": "authorizer",
                "LOG_LEVEL": "INFO"
            },
            log_retention=logs.RetentionDays.ONE_WEEK
        )

        # Grant authorizer permission to invoke itself (for caching)
        authorizer_function.add_permission(
            "AllowAPIGatewayInvoke",
            principal=iam.ServicePrincipal("apigateway.amazonaws.com")
        )

        # Protocol Manager Lambda for listing and searching protocols
        protocol_manager_function = lambda_.Function(
            self, "ProtocolManagerFunction",
            runtime=lambda_.Runtime.PYTHON_3_11,
            code=lambda_.Code.from_asset("../src/lambda/protocol_manager"),
            handler="handler.lambda_handler",
            function_name="TrialEnrollment-ProtocolManager",
            timeout=Duration.seconds(30),
            memory_size=256,
            environment={
                "CRITERIA_CACHE_TABLE": criteria_cache_table.table_name,
                "PROTOCOLS_BUCKET": protocol_bucket.bucket_name,
                "POWERTOOLS_SERVICE_NAME": "protocol-manager",
                "LOG_LEVEL": "INFO"
            },
            log_retention=logs.RetentionDays.ONE_WEEK
        )

        # Grant permissions
        criteria_cache_table.grant_read_data(protocol_manager_function)
        protocol_bucket.grant_read_write(protocol_manager_function)

        # Patient Manager Lambda for managing patients and FHIR data
        patient_manager_function = lambda_.Function(
            self, "PatientManagerFunction",
            runtime=lambda_.Runtime.PYTHON_3_11,
            code=lambda_.Code.from_asset("../src/lambda/patient_manager"),
            handler="handler.lambda_handler",
            function_name="TrialEnrollment-PatientManager",
            timeout=Duration.seconds(60),
            memory_size=512,
            environment={
                "FHIR_ENDPOINT": os.environ.get("FHIR_ENDPOINT", "https://healthlake.us-east-1.amazonaws.com/datastore/8640ed6b344b85e4729ac42df1c7d00e/r4"),
                "USE_HEALTHLAKE": "true",
                "POWERTOOLS_SERVICE_NAME": "patient-manager",
                "LOG_LEVEL": "INFO"
            },
            log_retention=logs.RetentionDays.ONE_WEEK
        )

        # Grant HealthLake permissions
        patient_manager_function.add_to_role_policy(healthlake_policy)

        # Match Manager Lambda for managing patient-protocol matches
        match_manager_function = lambda_.Function(
            self, "MatchManagerFunction",
            runtime=lambda_.Runtime.PYTHON_3_11,
            code=lambda_.Code.from_asset("../src/lambda/match_manager"),
            handler="handler.lambda_handler",
            function_name="TrialEnrollment-MatchManager",
            timeout=Duration.seconds(30),
            memory_size=256,
            environment={
                "MATCHES_TABLE": matches_table.table_name,
                "POWERTOOLS_SERVICE_NAME": "match-manager",
                "LOG_LEVEL": "INFO"
            },
            log_retention=logs.RetentionDays.ONE_WEEK
        )

        # Grant DynamoDB permissions to Match Manager
        matches_table.grant_read_write_data(match_manager_function)

        # Admin Manager Lambda for system administration
        admin_manager_function = lambda_.Function(
            self, "AdminManagerFunction",
            runtime=lambda_.Runtime.PYTHON_3_11,
            code=lambda_.Code.from_asset("../src/lambda/admin_manager"),
            handler="handler.lambda_handler",
            function_name="TrialEnrollment-AdminManager",
            timeout=Duration.seconds(60),
            memory_size=512,
            environment={
                "CRITERIA_CACHE_TABLE": criteria_cache_table.table_name,
                "MATCHES_TABLE": matches_table.table_name,
                "S3_BUCKET": protocol_bucket.bucket_name,
                "POWERTOOLS_SERVICE_NAME": "admin-manager",
                "LOG_LEVEL": "INFO"
                # TEXTRACT_FUNCTION and CLASSIFIER_FUNCTION set later after they're defined
            },
            log_retention=logs.RetentionDays.ONE_WEEK
        )

        # Grant permissions to Admin Manager
        criteria_cache_table.grant_read_write_data(admin_manager_function)
        matches_table.grant_read_data(admin_manager_function)
        # Allow Admin Manager to read CloudWatch logs
        admin_manager_function.add_to_role_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "logs:DescribeLogStreams",
                    "logs:GetLogEvents",
                    "logs:FilterLogEvents"
                ],
                resources=[f"arn:aws:logs:{self.region}:{self.account}:log-group:/aws/lambda/*"]
            )
        )

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
        # Allow orchestrator to invoke Criteria Parser
        criteria_parser_function.grant_invoke(protocol_orchestrator_function)
        # Allow orchestrator to read/write DynamoDB
        criteria_cache_table.grant_read_write_data(protocol_orchestrator_function)

        # NOTE: Admin Manager environment variables for Textract and Classifier
        # are hardcoded to avoid circular dependency issues with CDK
        admin_manager_function.add_environment(
            "TEXTRACT_FUNCTION",
            "TrialEnrollment-TextractProcessor"
        )
        admin_manager_function.add_environment(
            "CLASSIFIER_FUNCTION",
            "TrialEnrollment-SectionClassifier"
        )

        # Grant invoke permissions to Admin Manager (using wildcard to avoid circular dependency)
        admin_manager_function.add_to_role_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["lambda:InvokeFunction"],
                resources=[
                    f"arn:aws:lambda:{self.region}:{self.account}:function:TrialEnrollment-TextractProcessor",
                    f"arn:aws:lambda:{self.region}:{self.account}:function:TrialEnrollment-SectionClassifier"
                ]
            )
        )
        protocol_bucket.grant_read_write(admin_manager_function)

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

        # Token Authorizer for JWT validation
        token_authorizer = apigw.TokenAuthorizer(
            self, "JWTAuthorizer",
            handler=authorizer_function,
            identity_source="method.request.header.Authorization",
            results_cache_ttl=Duration.minutes(5),  # Cache authorization results
            authorizer_name="CognitoJWTAuthorizer"
        )

        # Criteria Parser endpoint (protected - StudyAdmin and PI only via authorizer)
        parser_resource = api.root.add_resource("parse-criteria")
        parser_integration = apigw.LambdaIntegration(criteria_parser_function)
        parser_resource.add_method(
            "POST",
            parser_integration,
            authorizer=token_authorizer,
            authorization_type=apigw.AuthorizationType.CUSTOM
        )

        # FHIR Search endpoint (protected - all authenticated users)
        search_resource = api.root.add_resource("check-criteria")
        search_integration = apigw.LambdaIntegration(fhir_search_function)
        search_resource.add_method(
            "POST",
            search_integration,
            authorizer=token_authorizer,
            authorization_type=apigw.AuthorizationType.CUSTOM
        )

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

        # Protocol endpoints (protected - all authenticated users can read)
        protocols_resource = api.root.add_resource("protocols")
        protocol_manager_integration = apigw.LambdaIntegration(protocol_manager_function)

        # GET /protocols - List all protocols
        protocols_resource.add_method(
            "GET",
            protocol_manager_integration,
            authorizer=token_authorizer,
            authorization_type=apigw.AuthorizationType.CUSTOM
        )

        # POST /protocols/search - Search protocols
        protocols_search_resource = protocols_resource.add_resource("search")
        protocols_search_resource.add_method(
            "POST",
            protocol_manager_integration,
            authorizer=token_authorizer,
            authorization_type=apigw.AuthorizationType.CUSTOM
        )

        # GET /protocols/{id} - Get specific protocol
        protocol_id_resource = protocols_resource.add_resource("{id}")
        protocol_id_resource.add_method(
            "GET",
            protocol_manager_integration,
            authorizer=token_authorizer,
            authorization_type=apigw.AuthorizationType.CUSTOM
        )

        # GET /protocols/{id}/criteria - Get cached parsed criteria for a protocol
        protocol_criteria_resource = protocol_id_resource.add_resource("criteria")
        protocol_criteria_resource.add_method(
            "GET",
            protocol_manager_integration,
            authorizer=token_authorizer,
            authorization_type=apigw.AuthorizationType.CUSTOM
        )

        # GET /protocols/{id}/status - Get protocol processing status
        protocol_status_resource = protocol_id_resource.add_resource("status")
        protocol_status_resource.add_method(
            "GET",
            protocol_manager_integration,
            authorizer=token_authorizer,
            authorization_type=apigw.AuthorizationType.CUSTOM
        )

        # POST /protocols/upload-url - Get pre-signed S3 URL for upload
        protocols_upload_url_resource = protocols_resource.add_resource("upload-url")
        protocols_upload_url_resource.add_method(
            "POST",
            protocol_manager_integration,
            authorizer=token_authorizer,
            authorization_type=apigw.AuthorizationType.CUSTOM
        )

        # Update Protocol Orchestrator with API endpoint
        protocol_orchestrator_function.add_environment(
            "PARSE_CRITERIA_API_ENDPOINT",
            f"{api.url}parse-criteria"
        )

        # Patient endpoints (protected - all authenticated users)
        patients_resource = api.root.add_resource("patients")
        patient_manager_integration = apigw.LambdaIntegration(patient_manager_function)

        # GET /patients - List all patients
        patients_resource.add_method(
            "GET",
            patient_manager_integration,
            authorizer=token_authorizer,
            authorization_type=apigw.AuthorizationType.CUSTOM
        )

        # POST /patients - Create new patient
        patients_resource.add_method(
            "POST",
            patient_manager_integration,
            authorizer=token_authorizer,
            authorization_type=apigw.AuthorizationType.CUSTOM
        )

        # POST /patients/search - Search patients
        patients_search_resource = patients_resource.add_resource("search")
        patients_search_resource.add_method(
            "POST",
            patient_manager_integration,
            authorizer=token_authorizer,
            authorization_type=apigw.AuthorizationType.CUSTOM
        )

        # GET /patients/{id} - Get specific patient
        patient_id_resource = patients_resource.add_resource("{id}")
        patient_id_resource.add_method(
            "GET",
            patient_manager_integration,
            authorizer=token_authorizer,
            authorization_type=apigw.AuthorizationType.CUSTOM
        )

        # Match endpoints (protected - all authenticated users)
        matches_resource = api.root.add_resource("matches")
        match_manager_integration = apigw.LambdaIntegration(match_manager_function)

        # GET /matches - List all matches with filters
        matches_resource.add_method(
            "GET",
            match_manager_integration,
            authorizer=token_authorizer,
            authorization_type=apigw.AuthorizationType.CUSTOM
        )

        # POST /matches - Create new match
        matches_resource.add_method(
            "POST",
            match_manager_integration,
            authorizer=token_authorizer,
            authorization_type=apigw.AuthorizationType.CUSTOM
        )

        # GET /matches/{id} - Get specific match
        match_id_resource = matches_resource.add_resource("{id}")
        match_id_resource.add_method(
            "GET",
            match_manager_integration,
            authorizer=token_authorizer,
            authorization_type=apigw.AuthorizationType.CUSTOM
        )

        # PUT /matches/{id} - Update match status
        match_id_resource.add_method(
            "PUT",
            match_manager_integration,
            authorizer=token_authorizer,
            authorization_type=apigw.AuthorizationType.CUSTOM
        )

        # DELETE /matches/{id} - Delete match
        match_id_resource.add_method(
            "DELETE",
            match_manager_integration,
            authorizer=token_authorizer,
            authorization_type=apigw.AuthorizationType.CUSTOM
        )

        # Admin endpoints (protected - StudyAdmin only via authorizer)
        admin_resource = api.root.add_resource("admin")
        admin_manager_integration = apigw.LambdaIntegration(admin_manager_function)

        # GET /admin/dashboard - System metrics and overview
        dashboard_resource = admin_resource.add_resource("dashboard")
        dashboard_resource.add_method(
            "GET",
            admin_manager_integration,
            authorizer=token_authorizer,
            authorization_type=apigw.AuthorizationType.CUSTOM
        )

        # GET /admin/processing-status - Pipeline processing status
        processing_status_resource = admin_resource.add_resource("processing-status")
        processing_status_resource.add_method(
            "GET",
            admin_manager_integration,
            authorizer=token_authorizer,
            authorization_type=apigw.AuthorizationType.CUSTOM
        )

        # GET /admin/logs - System logs from CloudWatch
        logs_resource = admin_resource.add_resource("logs")
        logs_resource.add_method(
            "GET",
            admin_manager_integration,
            authorizer=token_authorizer,
            authorization_type=apigw.AuthorizationType.CUSTOM
        )

        # GET /admin/audit-trail - Audit trail for compliance
        audit_trail_resource = admin_resource.add_resource("audit-trail")
        audit_trail_resource.add_method(
            "GET",
            admin_manager_integration,
            authorizer=token_authorizer,
            authorization_type=apigw.AuthorizationType.CUSTOM
        )

        # GET /admin/trials - List all trials with admin details
        trials_resource = admin_resource.add_resource("trials")
        trials_resource.add_method(
            "GET",
            admin_manager_integration,
            authorizer=token_authorizer,
            authorization_type=apigw.AuthorizationType.CUSTOM
        )

        # DELETE /admin/trials/{id} - Delete trial (admin only)
        trial_id_resource = trials_resource.add_resource("{id}")
        trial_id_resource.add_method(
            "DELETE",
            admin_manager_integration,
            authorizer=token_authorizer,
            authorization_type=apigw.AuthorizationType.CUSTOM
        )

        # POST /admin/reprocess/{id} - Reprocess failed trial
        reprocess_resource = admin_resource.add_resource("reprocess")
        reprocess_id_resource = reprocess_resource.add_resource("{id}")
        reprocess_id_resource.add_method(
            "POST",
            admin_manager_integration,
            authorizer=token_authorizer,
            authorization_type=apigw.AuthorizationType.CUSTOM
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

        CfnOutput(
            self, "AuthorizerFunctionName",
            value=authorizer_function.function_name,
            description="Lambda Authorizer function name"
        )

        CfnOutput(
            self, "ProtocolManagerFunctionName",
            value=protocol_manager_function.function_name,
            description="Protocol Manager Lambda function name"
        )

        CfnOutput(
            self, "PatientManagerFunctionName",
            value=patient_manager_function.function_name,
            description="Patient Manager Lambda function name"
        )

        CfnOutput(
            self, "MatchManagerFunctionName",
            value=match_manager_function.function_name,
            description="Match Manager Lambda function name"
        )

        CfnOutput(
            self, "MatchesTableName",
            value=matches_table.table_name,
            description="DynamoDB table for patient-protocol matches"
        )

        CfnOutput(
            self, "AdminManagerFunctionName",
            value=admin_manager_function.function_name,
            description="Admin Manager Lambda function name"
        )

        CfnOutput(
            self, "CognitoUserPoolId",
            value=os.environ.get("COGNITO_USER_POOL_ID", "us-east-1_zLcYERVQI"),
            description="Cognito User Pool ID"
        )

        CfnOutput(
            self, "CognitoClientId",
            value=os.environ.get("COGNITO_CLIENT_ID", "37ef9023q0b9q6lsdvc5rlvpo1"),
            description="Cognito App Client ID"
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
