"""
AWS Lambda Authorizer for API Gateway
Validates JWT tokens from AWS Cognito and implements role-based access control (RBAC)
"""

import json
import os
import re
from typing import Dict, Any, List, Optional
import urllib.request
from jose import jwt, JWTError
from functools import lru_cache

# Environment variables
USER_POOL_ID = os.environ.get('USER_POOL_ID', 'us-east-1_zLcYERVQI')
CLIENT_ID = os.environ.get('CLIENT_ID', '37ef9023q0b9q6lsdvc5rlvpo1')
REGION = os.environ['AWS_REGION']  # Automatically set by Lambda runtime

# Cognito JWKS URL
JWKS_URL = f'https://cognito-idp.{REGION}.amazonaws.com/{USER_POOL_ID}/.well-known/jwks.json'


@lru_cache(maxsize=1)
def get_cognito_public_keys() -> Dict[str, Any]:
    """
    Fetch and cache Cognito public keys for JWT verification

    Returns:
        Dictionary of public keys indexed by key ID (kid)
    """
    try:
        with urllib.request.urlopen(JWKS_URL) as response:
            jwks = json.loads(response.read())

        keys = {}
        for key in jwks['keys']:
            keys[key['kid']] = key

        return keys

    except Exception as e:
        print(f"Error fetching Cognito public keys: {str(e)}")
        raise Exception("Unable to fetch public keys for token verification")


def verify_jwt_token(token: str) -> Dict[str, Any]:
    """
    Verify JWT token signature and claims

    Args:
        token: JWT access token from Authorization header

    Returns:
        Decoded token claims

    Raises:
        Exception if token is invalid
    """
    try:
        # Get the key ID from token headers
        headers = jwt.get_unverified_headers(token)
        kid = headers.get('kid')

        if not kid:
            raise Exception("Token missing 'kid' header")

        # Get the public key
        keys = get_cognito_public_keys()
        key = keys.get(kid)

        if not key:
            raise Exception(f"Public key not found for kid: {kid}")

        # Verify token signature and claims
        claims = jwt.decode(
            token,
            key,
            algorithms=['RS256'],
            audience=CLIENT_ID,
            issuer=f'https://cognito-idp.{REGION}.amazonaws.com/{USER_POOL_ID}',
            options={
                'verify_signature': True,
                'verify_aud': True,
                'verify_iss': True,
                'verify_exp': True
            }
        )

        return claims

    except JWTError as e:
        print(f"JWT verification failed: {str(e)}")
        raise Exception(f"Unauthorized: {str(e)}")
    except Exception as e:
        print(f"Token verification error: {str(e)}")
        raise Exception(f"Unauthorized: {str(e)}")


def extract_user_groups(claims: Dict[str, Any]) -> List[str]:
    """
    Extract user groups from JWT token claims

    Args:
        claims: Decoded JWT claims

    Returns:
        List of group names (e.g., ['CRC', 'StudyAdmin'])
    """
    # Groups are in 'cognito:groups' claim
    groups = claims.get('cognito:groups', [])
    return groups if isinstance(groups, list) else []


def check_permission(groups: List[str], resource: str, method: str) -> bool:
    """
    Check if user has permission to access the resource based on their groups

    RBAC Matrix:
    - CRC: GET /protocols/*, POST /eligibility/check, GET /eligibility/*
    - StudyAdmin: All CRC permissions + POST /protocols/upload, PUT /protocols/*, DELETE /protocols/*
    - PI: All permissions (read-only for most, plus approval actions)

    Args:
        groups: List of user group names
        resource: API resource path (e.g., '/protocols/123')
        method: HTTP method (GET, POST, PUT, DELETE)

    Returns:
        True if access allowed, False otherwise
    """
    # PI has access to everything
    if 'PI' in groups:
        return True

    # StudyAdmin permissions
    if 'StudyAdmin' in groups:
        # StudyAdmin can do everything except PI-specific analytics
        if '/enrollment/' in resource or '/analytics/' in resource:
            return method == 'GET'  # Read-only for PI dashboards
        return True

    # CRC permissions (most restrictive)
    if 'CRC' in groups:
        # CRC can view protocols (list and individual)
        if resource == '/protocols' and method == 'GET':
            return True
        if re.match(r'/protocols/.*', resource) and method == 'GET':
            return True

        # CRC can check eligibility and criteria
        if resource.startswith('/eligibility/'):
            return method in ['GET', 'POST']
        if resource == '/check-criteria' and method == 'POST':
            return True
        if resource == '/parse-criteria' and method == 'POST':
            return True

        # CRC can search protocols
        if resource == '/protocols/search' and method == 'POST':
            return True

        # CRC can manage patients (view, create, search)
        if resource == '/patients' and method in ['GET', 'POST']:
            return True
        if resource == '/patients/search' and method == 'POST':
            return True
        if re.match(r'/patients/.*', resource) and method == 'GET':
            return True

        # CRC can manage matches (view, create, review)
        if resource == '/matches' and method in ['GET', 'POST']:
            return True
        if re.match(r'/matches/.*', resource) and method in ['GET', 'PUT', 'DELETE']:
            return True

        return False

    # No recognized groups - deny access
    return False


def generate_policy(principal_id: str, effect: str, resource: str, context: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Generate IAM policy for API Gateway

    Args:
        principal_id: User identifier (username)
        effect: 'Allow' or 'Deny'
        resource: ARN of the resource
        context: Additional context to pass to backend (optional)

    Returns:
        IAM policy document
    """
    policy = {
        'principalId': principal_id,
        'policyDocument': {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Action': 'execute-api:Invoke',
                    'Effect': effect,
                    'Resource': resource
                }
            ]
        }
    }

    # Add context if provided (will be available in backend as event['requestContext']['authorizer'])
    if context:
        policy['context'] = context

    return policy


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda Authorizer handler

    Args:
        event: API Gateway authorizer event
        context: Lambda context

    Returns:
        IAM policy allowing or denying access
    """
    print(f"Authorizer invoked for: {event.get('methodArn')}")

    try:
        # Extract token from Authorization header
        token = event.get('authorizationToken', '')

        # Remove 'Bearer ' prefix if present
        if token.startswith('Bearer '):
            token = token[7:]

        if not token:
            print("No token provided")
            raise Exception("Unauthorized: No token provided")

        # Verify token
        claims = verify_jwt_token(token)
        username = claims.get('username') or claims.get('cognito:username', 'unknown')

        print(f"Token verified for user: {username}")

        # Extract user groups
        groups = extract_user_groups(claims)
        print(f"User groups: {groups}")

        if not groups:
            print("User has no groups assigned")
            raise Exception("Unauthorized: User not assigned to any role")

        # Extract resource and method from methodArn
        # Format: arn:aws:execute-api:region:account-id:api-id/stage/METHOD/resource
        method_arn = event['methodArn']
        arn_parts = method_arn.split(':')
        api_gateway_arn = arn_parts[5].split('/')

        method = api_gateway_arn[2]
        resource = '/' + '/'.join(api_gateway_arn[3:]) if len(api_gateway_arn) > 3 else '/'

        print(f"Method: {method}, Resource: {resource}")

        # Check permissions
        has_permission = check_permission(groups, resource, method)

        if not has_permission:
            print(f"Access denied for user {username} to {method} {resource}")
            raise Exception(f"Forbidden: Insufficient permissions")

        # Generate Allow policy
        # Use wildcard for resource to allow all methods on this API
        # API Gateway caches the policy, so we allow all resources for this user
        wildcard_resource = ':'.join(arn_parts[0:5]) + ':' + api_gateway_arn[0] + '/*/*'

        # Context to pass to backend Lambda functions
        auth_context = {
            'username': username,
            'groups': ','.join(groups),  # Must be string
            'sub': claims.get('sub', ''),
            'email': claims.get('email', '')
        }

        print(f"Access granted for user {username}")

        return generate_policy(username, 'Allow', wildcard_resource, auth_context)

    except Exception as e:
        print(f"Authorization failed: {str(e)}")
        # Return Deny policy
        raise Exception('Unauthorized')  # API Gateway expects this format


# For local testing
if __name__ == '__main__':
    # Test event
    test_event = {
        'type': 'TOKEN',
        'authorizationToken': 'Bearer <your-test-token>',
        'methodArn': 'arn:aws:execute-api:us-east-1:123456789012:abcdef123/prod/GET/protocols/search'
    }

    result = lambda_handler(test_event, None)
    print(json.dumps(result, indent=2))
