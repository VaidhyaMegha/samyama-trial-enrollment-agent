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
s3_client = boto3.client('s3')
criteria_cache_table = dynamodb.Table(os.environ.get('CRITERIA_CACHE_TABLE', 'TrialEnrollmentAgentStack-CriteriaCacheTable'))
PROTOCOLS_BUCKET = os.environ.get('PROTOCOLS_BUCKET', 'trial-enrollment-agent-protocols')


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
    - POST /protocols/upload-url -> get_upload_url()
    - GET /protocols/{id} -> get_protocol()
    - GET /protocols/{id}/criteria -> get_protocol_criteria()
    - GET /protocols/{id}/status -> get_protocol_status()
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
        elif path == '/admin/dashboard' and http_method == 'GET':
            # GET /admin/dashboard
            return get_admin_dashboard()
        elif path == '/admin/processing-status' and http_method == 'GET':
            # GET /admin/processing-status
            return get_processing_status()
        elif path == '/protocols/search' and http_method == 'POST':
            body = json.loads(event.get('body', '{}'))
            return search_protocols(body)
        elif path == '/protocols/upload-url' and http_method == 'POST':
            body = json.loads(event.get('body', '{}'))
            return get_upload_url(body)
        elif path.endswith('/status') and http_method == 'GET':
            # GET /protocols/{id}/status
            protocol_id = path_parameters.get('id')
            return get_protocol_status(protocol_id)
        elif path.endswith('/criteria') and http_method == 'GET':
            # GET /protocols/{id}/criteria
            protocol_id = path_parameters.get('id')
            return get_protocol_criteria(protocol_id)
        elif path.startswith('/protocols/') and http_method == 'GET':
            # GET /protocols/{id}
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
            parsed_criteria = item.get('parsed_criteria', [])
            criteria_count = 0
            if isinstance(parsed_criteria, list):
                criteria_count = len(parsed_criteria)
            elif isinstance(parsed_criteria, dict):
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
    Get detailed protocol information including parsed criteria and all extracted data
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

        # Return complete protocol data as stored in DynamoDB
        protocol = {
            'trial_id': item.get('trial_id'),
            'id': item.get('trial_id'),
            'timestamp': item.get('timestamp'),
            'inclusion_criteria': item.get('inclusion_criteria', []),
            'exclusion_criteria': item.get('exclusion_criteria', []),
            'formatted_text': item.get('formatted_text', ''),
            'metadata': item.get('metadata', {}),
            'parsed_criteria': item.get('parsed_criteria', []),
            'fhir_resources': item.get('fhir_resources', {}),
            'processing_status': item.get('processing_status', 'completed'),
            'ttl': item.get('ttl')
        }

        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': json.dumps(protocol, cls=DecimalEncoder)
        }

    except Exception as e:
        print(f"Error getting protocol: {str(e)}")
        raise


def get_protocol_criteria(protocol_id: str) -> Dict[str, Any]:
    """
    Get cached parsed criteria for a specific protocol
    This endpoint is used by the frontend eligibility check flow
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
                'body': json.dumps({
                    'success': False,
                    'error': 'Protocol not found or criteria not cached'
                })
            }

        # Get parsed criteria from cache
        parsed_criteria = item.get('parsed_criteria')

        if not parsed_criteria:
            return {
                'statusCode': 404,
                'headers': cors_headers(),
                'body': json.dumps({
                    'success': False,
                    'error': 'Parsed criteria not found for this protocol. Please ensure the protocol has been processed.'
                })
            }

        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': json.dumps({
                'success': True,
                'trial_id': protocol_id,
                'parsed_criteria': parsed_criteria,
                'cached_at': item.get('processed_at', datetime.now().isoformat())
            }, cls=DecimalEncoder)
        }

    except Exception as e:
        print(f"Error getting protocol criteria: {str(e)}")
        return {
            'statusCode': 500,
            'headers': cors_headers(),
            'body': json.dumps({
                'success': False,
                'error': f'Error retrieving criteria: {str(e)}'
            })
        }


def get_upload_url(body: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate a pre-signed S3 URL for uploading a protocol PDF

    Body:
    - filename: Original filename
    - content_type: MIME type (should be application/pdf)
    - trial_id: Optional trial ID (will be generated if not provided)
    """
    import uuid

    filename = body.get('filename', 'protocol.pdf')
    content_type = body.get('content_type', 'application/pdf')
    trial_id = body.get('trial_id') or f"TRIAL-{uuid.uuid4().hex[:8].upper()}"

    # Generate S3 key
    s3_key = f"protocols/{trial_id}/{filename}"

    try:
        # Generate pre-signed URL for PUT operation (expires in 5 minutes)
        upload_url = s3_client.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': PROTOCOLS_BUCKET,
                'Key': s3_key,
                'ContentType': content_type
            },
            ExpiresIn=300  # 5 minutes
        )

        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': json.dumps({
                'upload_url': upload_url,
                's3_key': s3_key,
                'trial_id': trial_id,
                'bucket': PROTOCOLS_BUCKET
            })
        }

    except Exception as e:
        print(f"Error generating upload URL: {str(e)}")
        return {
            'statusCode': 500,
            'headers': cors_headers(),
            'body': json.dumps({'error': f'Failed to generate upload URL: {str(e)}'})
        }


def get_protocol_status(protocol_id: str) -> Dict[str, Any]:
    """
    Get the processing status of a protocol
    Returns status: processing, completed, or failed
    """

    try:
        response = criteria_cache_table.get_item(
            Key={'trial_id': protocol_id}
        )

        item = response.get('Item')

        if not item:
            return {
                'statusCode': 200,
                'headers': cors_headers(),
                'body': json.dumps({
                    'trial_id': protocol_id,
                    'status': 'processing',
                    'message': 'Protocol is being processed'
                })
            }

        # Check if parsed_criteria exists
        parsed_criteria = item.get('parsed_criteria')
        has_criteria = parsed_criteria is not None

        # Calculate criteria count based on actual structure
        criteria_count = 0
        if has_criteria:
            if isinstance(parsed_criteria, list):
                criteria_count = len(parsed_criteria)
            elif isinstance(parsed_criteria, dict):
                criteria_count = len(parsed_criteria.get('inclusion', [])) + len(parsed_criteria.get('exclusion', []))

        # Check processing status from metadata
        processing_status = item.get('processing_status', 'processing')
        status = processing_status if processing_status else ('completed' if has_criteria else 'processing')

        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': json.dumps({
                'trial_id': protocol_id,
                'status': status,
                'processed_at': item.get('timestamp'),
                'criteria_count': criteria_count,
                'inclusion_count': len(item.get('inclusion_criteria', [])),
                'exclusion_count': len(item.get('exclusion_criteria', [])),
                'message': 'Processing complete' if status == 'completed' else 'Still processing'
            }, cls=DecimalEncoder)
        }

    except Exception as e:
        print(f"Error getting protocol status: {str(e)}")
        return {
            'statusCode': 500,
            'headers': cors_headers(),
            'body': json.dumps({'error': f'Error getting status: {str(e)}'})
        }


def get_admin_dashboard() -> Dict[str, Any]:
    """
    Get admin dashboard data with summary statistics and recent protocols
    """

    try:
        # Scan all protocols from DynamoDB
        response = criteria_cache_table.scan()
        items = response.get('Items', [])

        # Calculate statistics
        total_protocols = len(items)
        completed_protocols = len([p for p in items if p.get('processing_status') == 'completed'])
        processing_protocols = len([p for p in items if p.get('processing_status') == 'processing'])
        failed_protocols = len([p for p in items if p.get('processing_status') == 'failed'])
        active_protocols = completed_protocols  # Completed protocols are considered active

        # Get recent protocols (last 10)
        sorted_items = sorted(items, key=lambda x: x.get('timestamp', ''), reverse=True)
        recent_protocols = []
        for item in sorted_items[:10]:
            inclusion_count = len(item.get('inclusion_criteria', []))
            exclusion_count = len(item.get('exclusion_criteria', []))

            recent_protocols.append({
                'trial_id': item.get('trial_id'),
                'title': item.get('trial_id'),  # Using trial_id as title since we don't extract title
                'status': item.get('processing_status', 'completed'),
                'upload_date': item.get('timestamp'),
                'criteria_count': inclusion_count + exclusion_count,
                'inclusion_count': inclusion_count,
                'exclusion_count': exclusion_count
            })

        # Calculate monthly activity (simplified - just show current month)
        current_month = datetime.utcnow().strftime('%b')
        recent_activity = [
            {'month': current_month, 'protocols': len([p for p in items if p.get('timestamp', '').startswith(datetime.utcnow().strftime('%Y-%m'))])}
        ]

        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': json.dumps({
                'total_protocols': total_protocols,
                'active_protocols': active_protocols,
                'processing_protocols': processing_protocols,
                'failed_protocols': failed_protocols,
                'completed_protocols': completed_protocols,
                'recent_protocols': recent_protocols,
                'recent_activity': recent_activity
            }, cls=DecimalEncoder)
        }

    except Exception as e:
        print(f"Error getting admin dashboard: {str(e)}")
        return {
            'statusCode': 500,
            'headers': cors_headers(),
            'body': json.dumps({'error': f'Error getting admin dashboard: {str(e)}'})
        }


def get_processing_status() -> Dict[str, Any]:
    """
    Get processing status for all protocols (Admin view)
    Returns list of protocols with their processing status
    """

    try:
        # Scan all protocols from DynamoDB
        response = criteria_cache_table.scan()
        items = response.get('Items', [])

        # Transform to admin view format
        protocols = []
        for item in items:
            protocol_data = {
                'trial_id': item.get('trial_id'),
                'status': item.get('processing_status', 'completed'),
                'upload_date': item.get('timestamp'),
                'last_updated': item.get('timestamp'),
                'criteria_count': 0,
            }

            # Count criteria
            inclusion_count = len(item.get('inclusion_criteria', []))
            exclusion_count = len(item.get('exclusion_criteria', []))
            protocol_data['criteria_count'] = inclusion_count + exclusion_count
            protocol_data['inclusion_count'] = inclusion_count
            protocol_data['exclusion_count'] = exclusion_count

            # Add metadata if available
            if 'metadata' in item:
                metadata = item.get('metadata', {})
                protocol_data['textract_confidence'] = metadata.get('textract_confidence')
                protocol_data['overall_confidence'] = metadata.get('overall_confidence')

            protocols.append(protocol_data)

        # Sort by upload date (most recent first)
        protocols.sort(key=lambda x: x.get('upload_date', ''), reverse=True)

        # Calculate summary stats
        summary = {
            'total': len(protocols),
            'completed': len([p for p in protocols if p['status'] == 'completed']),
            'processing': len([p for p in protocols if p['status'] == 'processing']),
            'failed': len([p for p in protocols if p['status'] == 'failed']),
        }

        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': json.dumps({
                'protocols': protocols,
                'summary': summary,
                'last_updated': datetime.utcnow().isoformat()
            }, cls=DecimalEncoder)
        }

    except Exception as e:
        print(f"Error getting processing status: {str(e)}")
        return {
            'statusCode': 500,
            'headers': cors_headers(),
            'body': json.dumps({'error': f'Error getting processing status: {str(e)}'})
        }


def cors_headers() -> Dict[str, str]:
    """Return CORS headers for API Gateway"""
    return {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,Authorization,X-Requested-With',
        'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
    }
