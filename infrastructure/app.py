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
