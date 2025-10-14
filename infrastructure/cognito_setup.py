#!/usr/bin/env python3
"""
AWS Cognito User Pool Setup Script
Creates a HIPAA-compliant Cognito User Pool with role-based groups for the Clinical Trial Enrollment System
"""

import boto3
import json
import sys
from typing import Dict, Any

# Initialize Cognito client
cognito = boto3.client('cognito-idp', region_name='us-east-1')


def create_user_pool() -> Dict[str, str]:
    """
    Create Cognito User Pool with HIPAA-compliant security settings

    Returns:
        Dict containing UserPoolId and UserPoolArn
    """
    print("Creating Cognito User Pool...")

    try:
        response = cognito.create_user_pool(
            PoolName='TrialEnrollmentUserPool',
            Policies={
                'PasswordPolicy': {
                    'MinimumLength': 12,
                    'RequireUppercase': True,
                    'RequireLowercase': True,
                    'RequireNumbers': True,
                    'RequireSymbols': True,
                    'TemporaryPasswordValidityDays': 7
                }
            },
            AutoVerifiedAttributes=['email'],
            MfaConfiguration='OFF',  # MFA disabled for now (can enable with SMS config later)
            UserAttributeUpdateSettings={
                'AttributesRequireVerificationBeforeUpdate': ['email']
            },
            Schema=[
                {
                    'Name': 'email',
                    'AttributeDataType': 'String',
                    'Required': True,
                    'Mutable': True
                },
                {
                    'Name': 'name',
                    'AttributeDataType': 'String',
                    'Required': True,
                    'Mutable': True
                },
                {
                    'Name': 'custom:role',
                    'AttributeDataType': 'String',
                    'Mutable': True,
                    'DeveloperOnlyAttribute': False
                }
            ],
            AccountRecoverySetting={
                'RecoveryMechanisms': [
                    {'Priority': 1, 'Name': 'verified_email'}
                ]
            },
            UserPoolTags={
                'Environment': 'Production',
                'Project': 'ClinicalTrialEnrollment',
                'Compliance': 'HIPAA'
            }
        )

        user_pool_id = response['UserPool']['Id']
        user_pool_arn = response['UserPool']['Arn']

        print(f"✅ User Pool created successfully!")
        print(f"   UserPoolId: {user_pool_id}")
        print(f"   ARN: {user_pool_arn}")

        return {
            'UserPoolId': user_pool_id,
            'UserPoolArn': user_pool_arn
        }

    except Exception as e:
        print(f"❌ Error creating User Pool: {str(e)}")
        sys.exit(1)


def create_user_pool_client(user_pool_id: str) -> str:
    """
    Create User Pool Client (App Client) for the web application

    Args:
        user_pool_id: The Cognito User Pool ID

    Returns:
        ClientId string
    """
    print("\nCreating User Pool Client...")

    try:
        response = cognito.create_user_pool_client(
            UserPoolId=user_pool_id,
            ClientName='TrialEnrollmentWebApp',
            GenerateSecret=False,  # For web apps, no secret needed
            RefreshTokenValidity=30,  # 30 days
            AccessTokenValidity=60,  # 60 minutes
            IdTokenValidity=60,  # 60 minutes
            TokenValidityUnits={
                'AccessToken': 'minutes',
                'IdToken': 'minutes',
                'RefreshToken': 'days'
            },
            ReadAttributes=[
                'email',
                'name',
                'custom:role'
            ],
            WriteAttributes=[
                'email',
                'name',
                'custom:role'
            ],
            ExplicitAuthFlows=[
                'ALLOW_USER_PASSWORD_AUTH',
                'ALLOW_REFRESH_TOKEN_AUTH',
                'ALLOW_USER_SRP_AUTH'
            ],
            PreventUserExistenceErrors='ENABLED',
            EnableTokenRevocation=True,
            EnablePropagateAdditionalUserContextData=False
        )

        client_id = response['UserPoolClient']['ClientId']

        print(f"✅ User Pool Client created successfully!")
        print(f"   ClientId: {client_id}")

        return client_id

    except Exception as e:
        print(f"❌ Error creating User Pool Client: {str(e)}")
        sys.exit(1)


def create_user_groups(user_pool_id: str) -> Dict[str, str]:
    """
    Create three user groups for role-based access control:
    - CRC (Clinical Research Coordinator)
    - StudyAdmin (Study Administrator)
    - PI (Principal Investigator)

    Args:
        user_pool_id: The Cognito User Pool ID

    Returns:
        Dict with group names as keys and group descriptions
    """
    print("\nCreating User Groups for RBAC...")

    groups = {
        'CRC': {
            'Description': 'Clinical Research Coordinators - Can check patient eligibility and search protocols',
            'Precedence': 3
        },
        'StudyAdmin': {
            'Description': 'Study Administrators - Can upload protocols, manage trials, and perform all CRC tasks',
            'Precedence': 2
        },
        'PI': {
            'Description': 'Principal Investigators - Can view enrollment analytics, approve matches, and access all data',
            'Precedence': 1
        }
    }

    created_groups = {}

    for group_name, group_config in groups.items():
        try:
            response = cognito.create_group(
                GroupName=group_name,
                UserPoolId=user_pool_id,
                Description=group_config['Description'],
                Precedence=group_config['Precedence']
            )

            print(f"✅ Group '{group_name}' created (Precedence: {group_config['Precedence']})")
            created_groups[group_name] = group_config['Description']

        except cognito.exceptions.GroupExistsException:
            print(f"⚠️  Group '{group_name}' already exists, skipping...")
            created_groups[group_name] = group_config['Description']

        except Exception as e:
            print(f"❌ Error creating group '{group_name}': {str(e)}")

    return created_groups


def save_configuration(config: Dict[str, Any], filename: str = 'cognito-config.json'):
    """
    Save Cognito configuration to JSON file

    Args:
        config: Configuration dictionary
        filename: Output filename
    """
    print(f"\nSaving configuration to {filename}...")

    try:
        with open(filename, 'w') as f:
            json.dump(config, f, indent=2)

        print(f"✅ Configuration saved successfully!")
        print(f"\n📋 Configuration Summary:")
        print(f"   User Pool ID: {config['UserPoolId']}")
        print(f"   Client ID: {config['ClientId']}")
        print(f"   Region: {config['Region']}")
        print(f"   Groups: {', '.join(config['Groups'].keys())}")

    except Exception as e:
        print(f"❌ Error saving configuration: {str(e)}")


def main():
    """Main execution function"""
    print("=" * 70)
    print("AWS Cognito User Pool Setup for Clinical Trial Enrollment System")
    print("=" * 70)

    # Step 1: Create User Pool
    user_pool = create_user_pool()

    # Step 2: Create User Pool Client
    client_id = create_user_pool_client(user_pool['UserPoolId'])

    # Step 3: Create User Groups
    groups = create_user_groups(user_pool['UserPoolId'])

    # Step 4: Save Configuration
    config = {
        'UserPoolId': user_pool['UserPoolId'],
        'UserPoolArn': user_pool['UserPoolArn'],
        'ClientId': client_id,
        'Region': 'us-east-1',
        'Groups': groups
    }

    save_configuration(config)

    print("\n" + "=" * 70)
    print("✅ Cognito Setup Complete!")
    print("=" * 70)
    print("\nNext Steps:")
    print("1. Run 'python3 create_test_users.py' to create test users")
    print("2. Update Lambda functions with UserPoolId and ClientId")
    print("3. Configure API Gateway with Lambda Authorizer")
    print("4. Update Amplify frontend configuration")
    print("\n⚠️  IMPORTANT: Save the cognito-config.json file securely!")


if __name__ == '__main__':
    main()
