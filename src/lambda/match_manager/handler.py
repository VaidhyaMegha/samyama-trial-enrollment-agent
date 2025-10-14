"""
Match Manager Lambda Function
Manages patient-protocol matches, including creation, retrieval, and status updates.
"""

import json
import os
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional
from decimal import Decimal
import boto3
from botocore.exceptions import ClientError


class DecimalEncoder(json.JSONEncoder):
    """Helper to convert Decimal to int/float for JSON serialization"""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return int(obj) if obj % 1 == 0 else float(obj)
        return super(DecimalEncoder, self).default(obj)


# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')

# Get table name from environment
MATCHES_TABLE_NAME = os.environ.get('MATCHES_TABLE', 'TrialEnrollmentMatches')

def lambda_handler(event, context):
    """
    Main Lambda handler for match management operations.

    Supported operations:
    - GET /matches - List matches with optional filters
    - POST /matches - Create a new match
    - GET /matches/{id} - Get a specific match
    - PUT /matches/{id} - Update match status
    - DELETE /matches/{id} - Delete a match
    """

    http_method = event.get('httpMethod', '').upper()
    path = event.get('path', '')
    path_parameters = event.get('pathParameters') or {}
    query_parameters = event.get('queryStringParameters') or {}

    try:
        body = json.loads(event.get('body', '{}')) if event.get('body') else {}
    except json.JSONDecodeError:
        return {
            'statusCode': 400,
            'headers': get_cors_headers(),
            'body': json.dumps({'error': 'Invalid JSON in request body'})
        }

    # Route to appropriate handler
    try:
        if http_method == 'GET':
            if path_parameters.get('id'):
                result = get_match(path_parameters['id'])
            else:
                result = list_matches(query_parameters)
        elif http_method == 'POST':
            result = create_match(body)
        elif http_method == 'PUT' and path_parameters.get('id'):
            result = update_match(path_parameters['id'], body)
        elif http_method == 'DELETE' and path_parameters.get('id'):
            result = delete_match(path_parameters['id'])
        else:
            return {
                'statusCode': 404,
                'headers': get_cors_headers(),
                'body': json.dumps({'error': 'Route not found'})
            }

        return {
            'statusCode': result.get('statusCode', 200),
            'headers': get_cors_headers(),
            'body': json.dumps(result.get('body', result), cls=DecimalEncoder)
        }

    except Exception as e:
        print(f"Error processing request: {str(e)}")
        import traceback
        traceback.print_exc()

        return {
            'statusCode': 500,
            'headers': get_cors_headers(),
            'body': json.dumps({
                'error': 'Internal server error',
                'message': str(e)
            }, cls=DecimalEncoder)
        }


def get_cors_headers() -> Dict[str, str]:
    """Get CORS headers for response."""
    return {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,Authorization',
        'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
    }


def create_match(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a new patient-protocol match.

    Required fields:
    - patient_id: Patient identifier
    - protocol_id: Protocol identifier
    - match_score: Eligibility match score (0-100)

    Optional fields:
    - patient_name: Patient name
    - protocol_name: Protocol name
    - criteria_results: List of criteria evaluation results
    - notes: Additional notes
    """

    # Validate required fields
    required_fields = ['patient_id', 'protocol_id', 'match_score']
    for field in required_fields:
        if field not in data:
            return {
                'statusCode': 400,
                'body': {'error': f'Missing required field: {field}'}
            }

    # Generate match ID
    match_id = f"MATCH-{uuid.uuid4().hex[:12].upper()}"

    # Create match item
    match_item = {
        'match_id': match_id,
        'patient_id': data['patient_id'],
        'protocol_id': data['protocol_id'],
        'patient_name': data.get('patient_name', 'Unknown Patient'),
        'protocol_name': data.get('protocol_name', 'Unknown Protocol'),
        'match_score': int(data['match_score']),
        'status': 'pending',  # pending, approved, rejected
        'criteria_results': data.get('criteria_results', []),
        'notes': data.get('notes', ''),
        'created_at': datetime.utcnow().isoformat(),
        'updated_at': datetime.utcnow().isoformat(),
        'created_by': data.get('created_by', 'system'),
        'updated_by': data.get('created_by', 'system')
    }

    # Save to DynamoDB
    try:
        table = dynamodb.Table(MATCHES_TABLE_NAME)
        table.put_item(Item=match_item)

        return {
            'statusCode': 201,
            'body': {
                'success': True,
                'match_id': match_id,
                'match': match_item,
                'message': 'Match created successfully'
            }
        }
    except ClientError as e:
        print(f"DynamoDB error: {e}")
        return {
            'statusCode': 500,
            'body': {'error': 'Failed to create match', 'details': str(e)}
        }


def list_matches(query_params: Dict[str, str]) -> Dict[str, Any]:
    """
    List matches with optional filters.

    Query parameters:
    - status: Filter by status (pending, approved, rejected)
    - patient_id: Filter by patient
    - protocol_id: Filter by protocol
    - limit: Maximum number of matches to return (default: 100)
    """

    try:
        table = dynamodb.Table(MATCHES_TABLE_NAME)

        # Build scan parameters
        scan_params = {}
        filter_expressions = []
        expression_attribute_values = {}

        # Status filter
        if 'status' in query_params:
            filter_expressions.append('#status = :status')
            expression_attribute_values[':status'] = query_params['status']

        # Patient ID filter
        if 'patient_id' in query_params:
            filter_expressions.append('patient_id = :patient_id')
            expression_attribute_values[':patient_id'] = query_params['patient_id']

        # Protocol ID filter
        if 'protocol_id' in query_params:
            filter_expressions.append('protocol_id = :protocol_id')
            expression_attribute_values[':protocol_id'] = query_params['protocol_id']

        # Add filters if any exist
        if filter_expressions:
            scan_params['FilterExpression'] = ' AND '.join(filter_expressions)
            scan_params['ExpressionAttributeValues'] = expression_attribute_values
            if '#status' in ' '.join(filter_expressions):
                scan_params['ExpressionAttributeNames'] = {'#status': 'status'}

        # Limit
        limit = int(query_params.get('limit', 100))
        scan_params['Limit'] = min(limit, 500)  # Max 500

        # Scan table
        response = table.scan(**scan_params)
        matches = response.get('Items', [])

        # Sort by created_at descending (newest first)
        matches.sort(key=lambda x: x.get('created_at', ''), reverse=True)

        return {
            'success': True,
            'matches': matches,
            'count': len(matches),
            'total': len(matches)  # In production, would query total count separately
        }

    except ClientError as e:
        print(f"DynamoDB error: {e}")
        return {
            'statusCode': 500,
            'body': {'error': 'Failed to list matches', 'details': str(e)}
        }


def get_match(match_id: str) -> Dict[str, Any]:
    """Get a specific match by ID."""

    try:
        table = dynamodb.Table(MATCHES_TABLE_NAME)
        response = table.get_item(Key={'match_id': match_id})

        if 'Item' not in response:
            return {
                'statusCode': 404,
                'body': {'error': f'Match not found: {match_id}'}
            }

        return {
            'success': True,
            'match': response['Item']
        }

    except ClientError as e:
        print(f"DynamoDB error: {e}")
        return {
            'statusCode': 500,
            'body': {'error': 'Failed to get match', 'details': str(e)}
        }


def update_match(match_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update a match with 2-level approval workflow support.

    Status Flow:
    - pending -> (CRC approve) -> pending_pi_approval -> (PI approve) -> approved
    - pending -> (CRC reject) -> rejected
    - pending_pi_approval -> (PI reject) -> rejected

    Updatable fields:
    - status: New status (approved, rejected, pending_pi_approval)
    - notes: Review notes
    - reviewed_by: User who reviewed (CRC or PI)
    - crc_reviewed_by: CRC who did first-level review
    - crc_reviewed_at: Timestamp of CRC review
    - pi_reviewed_by: PI who did final approval
    - pi_reviewed_at: Timestamp of PI approval
    """

    try:
        table = dynamodb.Table(MATCHES_TABLE_NAME)

        # First, get the current match to check its status
        current_match = table.get_item(Key={'match_id': match_id})
        if 'Item' not in current_match:
            return {
                'statusCode': 404,
                'body': {'error': f'Match not found: {match_id}'}
            }

        current_status = current_match['Item'].get('status', 'pending')

        # Build update expression
        update_expressions = []
        expression_attribute_values = {}
        expression_attribute_names = {}

        # Handle status changes based on 2-level workflow
        if 'status' in data:
            new_status = data['status']

            # Validate status transitions
            valid_transitions = {
                'pending': ['pending_pi_approval', 'rejected'],  # CRC can approve (move to PI review) or reject
                'pending_pi_approval': ['approved', 'rejected'],  # PI can approve or reject
                'approved': [],  # Final state
                'rejected': []   # Final state
            }

            if new_status not in valid_transitions.get(current_status, []):
                return {
                    'statusCode': 400,
                    'body': {
                        'error': f'Invalid status transition from {current_status} to {new_status}',
                        'current_status': current_status,
                        'requested_status': new_status,
                        'valid_transitions': valid_transitions.get(current_status, [])
                    }
                }

            update_expressions.append('#status = :status')
            expression_attribute_values[':status'] = new_status
            expression_attribute_names['#status'] = 'status'

            # Track CRC approval (transition from pending to pending_pi_approval)
            if current_status == 'pending' and new_status == 'pending_pi_approval':
                update_expressions.append('crc_reviewed_by = :crc_reviewed_by')
                update_expressions.append('crc_reviewed_at = :crc_reviewed_at')
                expression_attribute_values[':crc_reviewed_by'] = data.get('reviewed_by', 'CRC')
                expression_attribute_values[':crc_reviewed_at'] = datetime.utcnow().isoformat()

            # Track PI approval (transition from pending_pi_approval to approved)
            elif current_status == 'pending_pi_approval' and new_status == 'approved':
                update_expressions.append('pi_reviewed_by = :pi_reviewed_by')
                update_expressions.append('pi_reviewed_at = :pi_reviewed_at')
                expression_attribute_values[':pi_reviewed_by'] = data.get('reviewed_by', 'PI')
                expression_attribute_values[':pi_reviewed_at'] = datetime.utcnow().isoformat()

        # Notes
        if 'notes' in data:
            update_expressions.append('notes = :notes')
            expression_attribute_values[':notes'] = data['notes']

        # Reviewed by
        if 'reviewed_by' in data:
            update_expressions.append('updated_by = :reviewed_by')
            expression_attribute_values[':reviewed_by'] = data['reviewed_by']

        # Updated timestamp
        update_expressions.append('updated_at = :updated_at')
        expression_attribute_values[':updated_at'] = datetime.utcnow().isoformat()

        if not update_expressions:
            return {
                'statusCode': 400,
                'body': {'error': 'No fields to update'}
            }

        # Perform update
        update_params = {
            'Key': {'match_id': match_id},
            'UpdateExpression': 'SET ' + ', '.join(update_expressions),
            'ExpressionAttributeValues': expression_attribute_values,
            'ReturnValues': 'ALL_NEW'
        }

        if expression_attribute_names:
            update_params['ExpressionAttributeNames'] = expression_attribute_names

        response = table.update_item(**update_params)

        return {
            'success': True,
            'match': response['Attributes'],
            'message': 'Match updated successfully',
            'workflow_stage': response['Attributes'].get('status')
        }

    except ClientError as e:
        print(f"DynamoDB error: {e}")

        if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
            return {
                'statusCode': 404,
                'body': {'error': f'Match not found: {match_id}'}
            }

        return {
            'statusCode': 500,
            'body': {'error': 'Failed to update match', 'details': str(e)}
        }


def delete_match(match_id: str) -> Dict[str, Any]:
    """Delete a match."""

    try:
        table = dynamodb.Table(MATCHES_TABLE_NAME)

        response = table.delete_item(
            Key={'match_id': match_id},
            ReturnValues='ALL_OLD'
        )

        if 'Attributes' not in response:
            return {
                'statusCode': 404,
                'body': {'error': f'Match not found: {match_id}'}
            }

        return {
            'success': True,
            'message': 'Match deleted successfully',
            'deleted_match': response['Attributes']
        }

    except ClientError as e:
        print(f"DynamoDB error: {e}")
        return {
            'statusCode': 500,
            'body': {'error': 'Failed to delete match', 'details': str(e)}
        }
