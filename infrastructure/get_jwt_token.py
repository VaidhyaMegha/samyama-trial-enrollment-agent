#!/usr/bin/env python3
"""
Helper script to get JWT access token from Cognito
Useful for testing API Gateway with Lambda Authorizer
"""

import boto3
import json
import sys
import argparse
from typing import Dict


def load_config(filename: str = 'cognito-config.json') -> Dict:
    """Load Cognito configuration"""
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"❌ Error: {filename} not found!")
        sys.exit(1)


def load_test_users(filename: str = 'test-users.json') -> Dict:
    """Load test users"""
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"❌ Error: {filename} not found!")
        sys.exit(1)


def get_jwt_token(user_pool_id: str, client_id: str, username: str, password: str) -> Dict:
    """
    Authenticate user and get JWT tokens

    Args:
        user_pool_id: Cognito User Pool ID
        client_id: Cognito App Client ID
        username: Username
        password: Password

    Returns:
        Dict with AccessToken, IdToken, RefreshToken
    """
    client = boto3.client('cognito-idp', region_name='us-east-1')

    try:
        response = client.initiate_auth(
            ClientId=client_id,
            AuthFlow='USER_PASSWORD_AUTH',
            AuthParameters={
                'USERNAME': username,
                'PASSWORD': password
            }
        )

        return response['AuthenticationResult']

    except client.exceptions.NotAuthorizedException:
        print(f"❌ Authentication failed: Invalid username or password")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        sys.exit(1)


def decode_token_payload(token: str) -> Dict:
    """
    Decode JWT token payload (without verification, for display only)

    Args:
        token: JWT token

    Returns:
        Decoded payload
    """
    import base64
    try:
        # JWT format: header.payload.signature
        parts = token.split('.')
        if len(parts) != 3:
            return {}

        # Decode payload (add padding if needed)
        payload = parts[1]
        padding = 4 - (len(payload) % 4)
        if padding != 4:
            payload += '=' * padding

        decoded = base64.urlsafe_b64decode(payload)
        return json.loads(decoded)
    except Exception:
        return {}


def main():
    parser = argparse.ArgumentParser(description='Get JWT token from Cognito for testing')
    parser.add_argument('--username', '-u', help='Username (e.g., crc_test)')
    parser.add_argument('--password', '-p', help='Password')
    parser.add_argument('--role', '-r', choices=['crc', 'studyadmin', 'pi'],
                        help='Role shortcut (crc, studyadmin, or pi)')
    parser.add_argument('--show-payload', action='store_true',
                        help='Show decoded token payload')

    args = parser.parse_args()

    # Load configuration
    config = load_config()
    user_pool_id = config['UserPoolId']
    client_id = config['ClientId']

    # If role is specified, use test user credentials
    if args.role:
        test_users = load_test_users()
        role_map = {
            'crc': 'CRC',
            'studyadmin': 'StudyAdmin',
            'pi': 'PI'
        }
        target_role = role_map[args.role]

        # Find user with matching role
        user = next((u for u in test_users['users'] if u['role'] == target_role), None)
        if not user:
            print(f"❌ Error: No test user found for role {target_role}")
            sys.exit(1)

        username = user['username']
        password = user['password']
        print(f"🔑 Authenticating as {user['name']} ({user['role']})...")
    elif args.username and args.password:
        username = args.username
        password = args.password
        print(f"🔑 Authenticating as {username}...")
    else:
        print("❌ Error: Please specify either --role or --username and --password")
        parser.print_help()
        sys.exit(1)

    # Get JWT tokens
    tokens = get_jwt_token(user_pool_id, client_id, username, password)

    print("\n" + "=" * 70)
    print("✅ Authentication Successful!")
    print("=" * 70)

    # Access Token (for API Gateway)
    print("\n📝 Access Token (use this for API Gateway):")
    print("-" * 70)
    print(tokens['AccessToken'])

    if args.show_payload:
        payload = decode_token_payload(tokens['AccessToken'])
        print("\n📋 Access Token Payload:")
        print(json.dumps(payload, indent=2))

    # ID Token (contains user info and groups)
    print("\n📝 ID Token (contains user info and groups):")
    print("-" * 70)
    print(tokens['IdToken'])

    if args.show_payload:
        payload = decode_token_payload(tokens['IdToken'])
        print("\n📋 ID Token Payload:")
        print(json.dumps(payload, indent=2))

        # Highlight groups
        if 'cognito:groups' in payload:
            print(f"\n👥 User Groups: {', '.join(payload['cognito:groups'])}")

    # Token expiration
    print(f"\n⏰ Token Expiration: {tokens.get('ExpiresIn', 3600)} seconds ({tokens.get('ExpiresIn', 3600) // 60} minutes)")

    # Usage example
    api_url = config.get('ApiUrl', '<API_GATEWAY_URL>')
    print("\n📌 Usage Example:")
    print("-" * 70)
    print(f"curl -X POST {api_url}parse-criteria \\")
    print(f"     -H 'Authorization: Bearer {tokens['AccessToken'][:50]}...' \\")
    print(f"     -H 'Content-Type: application/json' \\")
    print(f"     -d '{{\"trial_id\": \"test\", \"criteria_text\": \"Age >= 18\"}}'")

    print("\n" + "=" * 70)


if __name__ == '__main__':
    main()
