"""
Protocol Manager Lambda Function
Handles protocol listing, searching, and metadata retrieval
"""

import json
import os
import boto3
from typing import Dict, List, Any
from datetime import datetime
from decimal import Decimal

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
criteria_cache_table = dynamodb.Table(os.environ.get('CRITERIA_CACHE_TABLE', 'TrialEnrollmentAgentStack-CriteriaCacheTable'))


class DecimalEncoder(json.JSONEncoder):
    """Helper to convert Decimal to int/float for JSON serialization"""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return int(obj) if obj % 1 == 0 else float(obj)
        return super(DecimalEncoder, self).default(obj)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler for protocol management operations

    Routes:
    - GET /protocols -> list_protocols()
    - POST /protocols/search -> search_protocols()
    - GET /protocols/{id} -> get_protocol()
    """

    print(f"Event: {json.dumps(event)}")

    http_method = event.get('httpMethod', 'GET')
    path = event.get('path', '').rstrip('/')
    path_parameters = event.get('pathParameters') or {}
    query_parameters = event.get('queryStringParameters') or {}

    # Extract user context from authorizer
    authorizer_context = event.get('requestContext', {}).get('authorizer', {})
    username = authorizer_context.get('username', 'unknown')
    groups = authorizer_context.get('groups', '').split(',') if authorizer_context.get('groups') else []

    print(f"User: {username}, Groups: {groups}")

    try:
        # Route to appropriate handler
        if path == '/protocols' and http_method == 'GET':
            return list_protocols(query_parameters)
        elif path == '/protocols/search' and http_method == 'POST':
            body = json.loads(event.get('body', '{}'))
            return search_protocols(body)
        elif path.startswith('/protocols/') and http_method == 'GET':
            protocol_id = path_parameters.get('id') or path.split('/')[-1]
            return get_protocol(protocol_id)
        else:
            return {
                'statusCode': 404,
                'headers': cors_headers(),
                'body': json.dumps({'error': 'Not found'})
            }

    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': cors_headers(),
            'body': json.dumps({'error': str(e)})
        }


def list_protocols(query_params: Dict[str, str]) -> Dict[str, Any]:
    """
    List all protocols with optional pagination

    Query params:
    - limit: Number of results (default: 50)
    - lastKey: Pagination token
    """

    limit = int(query_params.get('limit', 50))
    last_key = query_params.get('lastKey')

    try:
        # Scan DynamoDB for all protocols
        scan_kwargs = {
            'Limit': limit
        }

        if last_key:
            scan_kwargs['ExclusiveStartKey'] = {'trial_id': last_key}

        response = criteria_cache_table.scan(**scan_kwargs)

        items = response.get('Items', [])
        last_evaluated_key = response.get('LastEvaluatedKey')

        # Transform to frontend-expected format
        protocols = []
        for item in items:
            # Safely get parsed_criteria count
            parsed_criteria = item.get('parsed_criteria', {})
            criteria_count = 0
            if isinstance(parsed_criteria, dict):
                criteria_count = len(parsed_criteria.get('inclusion', [])) + len(parsed_criteria.get('exclusion', []))

            protocols.append({
                'id': item.get('trial_id'),
                'nctId': item.get('trial_id'),
                'title': item.get('title', 'Unknown Protocol'),
                'disease': item.get('disease', 'Unknown'),
                'phase': item.get('phase', 'Unknown'),
                'status': item.get('status', 'Active'),
                'uploadDate': item.get('processed_at', datetime.now().isoformat()),
                'enrollmentTarget': item.get('enrollment_target', 0),
                'enrollmentCurrent': item.get('enrollment_current', 0),
                'criteriaCount': criteria_count
            })

        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': json.dumps({
                'protocols': protocols,
                'lastKey': last_evaluated_key.get('trial_id') if last_evaluated_key else None,
                'count': len(protocols)
            }, cls=DecimalEncoder)
        }

    except Exception as e:
        print(f"Error listing protocols: {str(e)}")
        raise


def search_protocols(body: Dict[str, Any]) -> Dict[str, Any]:
    """
    Search protocols by query string (title, disease, ID)

    Body:
    - query: Search string
    """

    query = body.get('query', '').lower()

    if not query:
        return list_protocols({})

    try:
        # Scan all protocols and filter (for MVP - in production use GSI)
        response = criteria_cache_table.scan()
        items = response.get('Items', [])

        # Filter by query
        filtered_protocols = []
        for item in items:
            trial_id = item.get('trial_id', '').lower()
            title = item.get('title', '').lower()
            disease = item.get('disease', '').lower()

            if query in trial_id or query in title or query in disease:
                filtered_protocols.append({
                    'id': item.get('trial_id'),
                    'nctId': item.get('trial_id'),
                    'title': item.get('title', 'Unknown Protocol'),
                    'disease': item.get('disease', 'Unknown'),
                    'phase': item.get('phase', 'Unknown'),
                    'status': item.get('status', 'Active'),
                    'uploadDate': item.get('processed_at', datetime.now().isoformat()),
                    'enrollmentTarget': item.get('enrollment_target', 0),
                    'enrollmentCurrent': item.get('enrollment_current', 0)
                })

        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': json.dumps({
                'protocols': filtered_protocols,
                'count': len(filtered_protocols)
            }, cls=DecimalEncoder)
        }

    except Exception as e:
        print(f"Error searching protocols: {str(e)}")
        raise


def get_protocol(protocol_id: str) -> Dict[str, Any]:
    """
    Get detailed protocol information including parsed criteria
    """

    try:
        response = criteria_cache_table.get_item(
            Key={'trial_id': protocol_id}
        )

        item = response.get('Item')
        if not item:
            return {
                'statusCode': 404,
                'headers': cors_headers(),
                'body': json.dumps({'error': 'Protocol not found'})
            }

        protocol = {
            'id': item.get('trial_id'),
            'nctId': item.get('trial_id'),
            'title': item.get('title', 'Unknown Protocol'),
            'disease': item.get('disease', 'Unknown'),
            'phase': item.get('phase', 'Unknown'),
            'status': item.get('status', 'Active'),
            'uploadDate': item.get('processed_at', datetime.now().isoformat()),
            'enrollmentTarget': item.get('enrollment_target', 0),
            'enrollmentCurrent': item.get('enrollment_current', 0),
            'parsedCriteria': item.get('parsed_criteria', {}),
            'rawCriteria': item.get('raw_criteria_text', ''),
            'metadata': item.get('metadata', {})
        }

        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': json.dumps(protocol, cls=DecimalEncoder)
        }

    except Exception as e:
        print(f"Error getting protocol: {str(e)}")
        raise


def cors_headers() -> Dict[str, str]:
    """Return CORS headers for API Gateway"""
    return {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,Authorization,X-Requested-With',
        'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
    }
