"""
Admin Manager Lambda Function
Handles system administration tasks including monitoring, reprocessing, and audit trails
"""

import json
import os
import boto3
from typing import Dict, List, Any
from datetime import datetime, timedelta
from decimal import Decimal
from botocore.exceptions import ClientError


class DecimalEncoder(json.JSONEncoder):
    """Helper to convert Decimal to int/float for JSON serialization"""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return int(obj) if obj % 1 == 0 else float(obj)
        return super(DecimalEncoder, self).default(obj)


# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
s3_client = boto3.client('s3')
textract_client = boto3.client('textract')
lambda_client = boto3.client('lambda')
logs_client = boto3.client('logs')

# Environment variables
CRITERIA_CACHE_TABLE = os.environ.get('CRITERIA_CACHE_TABLE', 'TrialEnrollmentAgentStack-CriteriaCacheTable')
MATCHES_TABLE = os.environ.get('MATCHES_TABLE', 'TrialEnrollmentMatches')
S3_BUCKET = os.environ.get('S3_BUCKET')
TEXTRACT_FUNCTION = os.environ.get('TEXTRACT_FUNCTION', 'TrialEnrollmentAgentStack-TextractProcessor')
CLASSIFIER_FUNCTION = os.environ.get('CLASSIFIER_FUNCTION', 'TrialEnrollmentAgentStack-SectionClassifier')


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler for admin and PI operations

    Admin Routes:
    - GET /admin/dashboard -> get_dashboard_metrics()
    - GET /admin/processing-status -> get_processing_status()
    - GET /admin/logs -> get_system_logs()
    - GET /admin/audit-trail -> get_audit_trail()
    - POST /admin/reprocess/{trial_id} -> reprocess_trial()
    - DELETE /admin/trials/{trial_id} -> delete_trial()
    - GET /admin/trials -> get_all_trials_admin()

    PI Routes:
    - GET /pi/dashboard -> get_pi_dashboard_metrics()
    - GET /pi/trials -> get_pi_trials()
    - GET /pi/trials/{trial_id} -> get_pi_trial_details()
    - GET /pi/export/enrollment-summary -> export_enrollment_summary()
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

    # Handle OPTIONS request for CORS preflight
    if http_method == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': json.dumps({'message': 'CORS preflight OK'})
        }

    try:
        # PI Routes (accessible by PI and StudyAdmin)
        if path.startswith('/pi/'):
            if 'PI' not in groups and 'StudyAdmin' not in groups:
                return {
                    'statusCode': 403,
                    'headers': cors_headers(),
                    'body': json.dumps({'error': 'Access denied. PI or StudyAdmin role required.'})
                }

            if path == '/pi/dashboard' and http_method == 'GET':
                return get_pi_dashboard_metrics()
            elif path == '/pi/trials' and http_method == 'GET':
                return get_pi_trials()
            elif path.startswith('/pi/trials/') and http_method == 'GET':
                trial_id = path_parameters.get('id') or path.split('/')[-1]
                return get_pi_trial_details(trial_id)
            elif path == '/pi/export/enrollment-summary' and http_method == 'GET':
                trial_id = query_parameters.get('trial_id')
                return export_enrollment_summary(trial_id)
            else:
                return {
                    'statusCode': 404,
                    'headers': cors_headers(),
                    'body': json.dumps({'error': 'PI route not found'})
                }

        # Admin Routes (StudyAdmin only)
        if 'StudyAdmin' not in groups:
            return {
                'statusCode': 403,
                'headers': cors_headers(),
                'body': json.dumps({'error': 'Access denied. StudyAdmin role required.'})
            }

        # Route to appropriate handler
        if path == '/admin/dashboard' and http_method == 'GET':
            return get_dashboard_metrics()
        elif path == '/admin/processing-status' and http_method == 'GET':
            return get_processing_status()
        elif path == '/admin/logs' and http_method == 'GET':
            return get_system_logs(query_parameters)
        elif path == '/admin/audit-trail' and http_method == 'GET':
            return get_audit_trail(query_parameters)
        elif path.startswith('/admin/reprocess/') and http_method == 'POST':
            trial_id = path_parameters.get('id') or path.split('/')[-1]
            body = json.loads(event.get('body', '{}'))
            return reprocess_trial(trial_id, body, username)
        elif path.startswith('/admin/trials/') and http_method == 'DELETE':
            trial_id = path_parameters.get('id') or path.split('/')[-1]
            return delete_trial(trial_id, username)
        elif path == '/admin/trials' and http_method == 'GET':
            return get_all_trials_admin(query_parameters)
        else:
            return {
                'statusCode': 404,
                'headers': cors_headers(),
                'body': json.dumps({'error': 'Not found'})
            }

    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()

        return {
            'statusCode': 500,
            'headers': cors_headers(),
            'body': json.dumps({'error': str(e)})
        }


def get_dashboard_metrics() -> Dict[str, Any]:
    """
    Get system-wide dashboard metrics

    Returns:
    - Total protocols
    - Processing status counts
    - Recent activity
    - System health
    """

    try:
        criteria_cache = dynamodb.Table(CRITERIA_CACHE_TABLE)
        matches_table = dynamodb.Table(MATCHES_TABLE)

        # Get all protocols
        protocols_response = criteria_cache.scan()
        protocols = protocols_response.get('Items', [])

        # Get all matches
        matches_response = matches_table.scan()
        matches = matches_response.get('Items', [])

        # Calculate metrics
        total_protocols = len(protocols)

        # Processing status breakdown
        status_counts = {
            'ready': 0,
            'processing': 0,
            'failed': 0
        }

        for protocol in protocols:
            status = protocol.get('processing_status', 'ready')
            if status in status_counts:
                status_counts[status] += 1
            else:
                status_counts['ready'] += 1

        # Match statistics
        match_stats = {
            'pending': 0,
            'pending_pi_approval': 0,
            'approved': 0,
            'rejected': 0
        }

        for match in matches:
            status = match.get('status', 'pending')
            if status in match_stats:
                match_stats[status] += 1

        # Recent activity (last 7 days)
        seven_days_ago = (datetime.utcnow() - timedelta(days=7)).isoformat()
        recent_protocols = [p for p in protocols if p.get('processed_at', '') >= seven_days_ago]
        recent_matches = [m for m in matches if m.get('created_at', '') >= seven_days_ago]

        # System health metrics
        health = {
            'database': 'healthy',
            'processing_pipeline': 'operational',
            'api_gateway': 'operational'
        }

        # Calculate average processing time (if metadata available)
        avg_processing_time = None
        processing_times = []
        for protocol in protocols:
            metadata = protocol.get('metadata', {})
            if 'processing_time' in metadata:
                processing_times.append(metadata['processing_time'])

        if processing_times:
            avg_processing_time = sum(processing_times) / len(processing_times)

        # Get recent protocols for display
        recent_protocols_list = []
        for protocol in sorted(protocols, key=lambda x: x.get('timestamp', ''), reverse=True)[:10]:
            inclusion_count = len(protocol.get('inclusion_criteria', []))
            exclusion_count = len(protocol.get('exclusion_criteria', []))

            recent_protocols_list.append({
                'trial_id': protocol.get('trial_id'),
                'title': protocol.get('trial_id'),
                'status': protocol.get('processing_status', 'completed'),
                'upload_date': protocol.get('timestamp'),
                'criteria_count': inclusion_count + exclusion_count
            })

        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': json.dumps({
                'total_protocols': total_protocols,
                'active_protocols': status_counts['ready'],
                'processing_protocols': status_counts['processing'],
                'failed_protocols': status_counts['failed'],
                'completed_protocols': status_counts['ready'],
                'recent_protocols': recent_protocols_list,
                'recent_activity': [],  # Can be populated with monthly stats if needed
                'timestamp': datetime.utcnow().isoformat()
            }, cls=DecimalEncoder)
        }

    except Exception as e:
        print(f"Error getting dashboard metrics: {str(e)}")
        raise


def get_processing_status() -> Dict[str, Any]:
    """
    Get detailed processing pipeline status
    """

    try:
        criteria_cache = dynamodb.Table(CRITERIA_CACHE_TABLE)

        # Get all protocols with processing metadata
        response = criteria_cache.scan()
        protocols_items = response.get('Items', [])

        # Transform to frontend-expected format
        protocols = []
        for protocol in protocols_items:
            metadata = protocol.get('metadata', {})
            inclusion_count = len(protocol.get('inclusion_criteria', []))
            exclusion_count = len(protocol.get('exclusion_criteria', []))

            protocols.append({
                'trial_id': protocol.get('trial_id'),
                'status': protocol.get('processing_status', 'completed'),
                'upload_date': protocol.get('timestamp'),
                'last_updated': protocol.get('timestamp'),
                'criteria_count': inclusion_count + exclusion_count,
                'inclusion_count': inclusion_count,
                'exclusion_count': exclusion_count,
                'textract_confidence': metadata.get('textract_confidence'),
                'overall_confidence': metadata.get('overall_confidence'),
                'error_message': metadata.get('error')
            })

        # Sort by upload_date (most recent first), handle None values
        protocols.sort(key=lambda x: x.get('upload_date') or '', reverse=True)

        # Calculate summary
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
        raise


def get_system_logs(query_params: Dict[str, str]) -> Dict[str, Any]:
    """
    Get CloudWatch logs for the system

    Query params:
    - log_group: CloudWatch log group name
    - start_time: Start timestamp (ISO format)
    - limit: Number of log entries (default: 50)
    """

    try:
        log_group = query_params.get('log_group', f'/aws/lambda/{TEXTRACT_FUNCTION}')
        limit = int(query_params.get('limit', 50))

        # Default to last 24 hours
        start_time = query_params.get('start_time')
        if start_time:
            start_timestamp = int(datetime.fromisoformat(start_time.replace('Z', '+00:00')).timestamp() * 1000)
        else:
            start_timestamp = int((datetime.utcnow() - timedelta(days=1)).timestamp() * 1000)

        # Get log streams
        streams_response = logs_client.describe_log_streams(
            logGroupName=log_group,
            orderBy='LastEventTime',
            descending=True,
            limit=5
        )

        log_streams = streams_response.get('logStreams', [])

        # Get logs from streams
        log_entries = []

        for stream in log_streams[:3]:  # Get logs from most recent 3 streams
            try:
                events_response = logs_client.get_log_events(
                    logGroupName=log_group,
                    logStreamName=stream['logStreamName'],
                    startTime=start_timestamp,
                    limit=limit,
                    startFromHead=False
                )

                for event in events_response.get('events', []):
                    log_entries.append({
                        'timestamp': datetime.fromtimestamp(event['timestamp'] / 1000).isoformat(),
                        'message': event['message'],
                        'stream': stream['logStreamName']
                    })
            except Exception as e:
                print(f"Error reading log stream {stream['logStreamName']}: {e}")
                continue

        # Sort by timestamp (most recent first)
        log_entries.sort(key=lambda x: x['timestamp'], reverse=True)

        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': json.dumps({
                'success': True,
                'logs': log_entries[:limit],
                'log_group': log_group,
                'count': len(log_entries[:limit]),
                'timestamp': datetime.utcnow().isoformat()
            }, cls=DecimalEncoder)
        }

    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            return {
                'statusCode': 200,
                'headers': cors_headers(),
                'body': json.dumps({
                    'success': True,
                    'logs': [],
                    'log_group': log_group,
                    'count': 0,
                    'message': 'Log group not found or empty'
                })
            }
        raise

    except Exception as e:
        print(f"Error getting system logs: {str(e)}")
        raise


def get_audit_trail(query_params: Dict[str, str]) -> Dict[str, Any]:
    """
    Get audit trail for compliance

    Query params:
    - trial_id: Filter by specific trial
    - action: Filter by action type
    - user: Filter by user
    - start_date: Start date
    - limit: Number of entries (default: 100)
    """

    try:
        # For MVP, we'll compile audit trail from multiple sources
        # In production, this would come from a dedicated audit table

        criteria_cache = dynamodb.Table(CRITERIA_CACHE_TABLE)
        matches_table = dynamodb.Table(MATCHES_TABLE)

        audit_entries = []

        # Get protocol creation/modification events
        protocols_response = criteria_cache.scan()
        protocols = protocols_response.get('Items', [])

        for protocol in protocols:
            audit_entries.append({
                'timestamp': protocol.get('processed_at', datetime.utcnow().isoformat()),
                'action': 'protocol_processed',
                'resource_type': 'protocol',
                'resource_id': protocol.get('trial_id'),
                'user': protocol.get('processed_by', 'system'),
                'details': {
                    'title': protocol.get('title'),
                    'status': protocol.get('processing_status')
                }
            })

        # Get match approval/rejection events
        matches_response = matches_table.scan()
        matches = matches_response.get('Items', [])

        for match in matches:
            # CRC review event
            if match.get('crc_reviewed_at'):
                audit_entries.append({
                    'timestamp': match.get('crc_reviewed_at'),
                    'action': 'match_reviewed_crc',
                    'resource_type': 'match',
                    'resource_id': match.get('match_id'),
                    'user': match.get('crc_reviewed_by', 'unknown'),
                    'details': {
                        'patient_id': match.get('patient_id'),
                        'protocol_id': match.get('protocol_id'),
                        'status': 'pending_pi_approval'
                    }
                })

            # PI review event
            if match.get('pi_reviewed_at'):
                audit_entries.append({
                    'timestamp': match.get('pi_reviewed_at'),
                    'action': 'match_reviewed_pi',
                    'resource_type': 'match',
                    'resource_id': match.get('match_id'),
                    'user': match.get('pi_reviewed_by', 'unknown'),
                    'details': {
                        'patient_id': match.get('patient_id'),
                        'protocol_id': match.get('protocol_id'),
                        'status': match.get('status')
                    }
                })

        # Sort by timestamp (most recent first)
        audit_entries.sort(key=lambda x: x.get('timestamp', ''), reverse=True)

        # Apply filters
        trial_id_filter = query_params.get('trial_id')
        if trial_id_filter:
            audit_entries = [e for e in audit_entries if e.get('details', {}).get('protocol_id') == trial_id_filter or e.get('resource_id') == trial_id_filter]

        action_filter = query_params.get('action')
        if action_filter:
            audit_entries = [e for e in audit_entries if e.get('action') == action_filter]

        user_filter = query_params.get('user')
        if user_filter:
            audit_entries = [e for e in audit_entries if e.get('user') == user_filter]

        # Limit results
        limit = int(query_params.get('limit', 100))
        audit_entries = audit_entries[:limit]

        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': json.dumps({
                'success': True,
                'audit_trail': audit_entries,
                'count': len(audit_entries),
                'timestamp': datetime.utcnow().isoformat()
            }, cls=DecimalEncoder)
        }

    except Exception as e:
        print(f"Error getting audit trail: {str(e)}")
        raise


def reprocess_trial(trial_id: str, body: Dict[str, Any], username: str) -> Dict[str, Any]:
    """
    Reprocess a failed or incomplete trial

    Args:
    - trial_id: Trial to reprocess
    - body: Reprocessing options
    - username: Admin user requesting reprocess
    """

    try:
        criteria_cache = dynamodb.Table(CRITERIA_CACHE_TABLE)

        # Get existing trial
        response = criteria_cache.get_item(Key={'trial_id': trial_id})

        if 'Item' not in response:
            return {
                'statusCode': 404,
                'headers': cors_headers(),
                'body': json.dumps({
                    'success': False,
                    'error': f'Trial not found: {trial_id}'
                })
            }

        trial = response['Item']

        # Get S3 location
        s3_key = trial.get('s3_key')
        if not s3_key:
            return {
                'statusCode': 400,
                'headers': cors_headers(),
                'body': json.dumps({
                    'success': False,
                    'error': 'No S3 key found for this trial. Cannot reprocess.'
                })
            }

        # Update status to processing
        criteria_cache.update_item(
            Key={'trial_id': trial_id},
            UpdateExpression='SET processing_status = :status, reprocessed_by = :user, reprocessed_at = :timestamp',
            ExpressionAttributeValues={
                ':status': 'processing',
                ':user': username,
                ':timestamp': datetime.utcnow().isoformat()
            }
        )

        # Invoke Textract processor
        textract_event = {
            's3_bucket': S3_BUCKET,
            's3_key': s3_key,
            'trial_id': trial_id
        }

        lambda_client.invoke(
            FunctionName=TEXTRACT_FUNCTION,
            InvocationType='Event',  # Async invocation
            Payload=json.dumps(textract_event)
        )

        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': json.dumps({
                'success': True,
                'message': f'Reprocessing initiated for trial {trial_id}',
                'trial_id': trial_id,
                'status': 'processing'
            }, cls=DecimalEncoder)
        }

    except Exception as e:
        print(f"Error reprocessing trial: {str(e)}")
        raise


def delete_trial(trial_id: str, username: str) -> Dict[str, Any]:
    """
    Delete a trial (admin only)

    Args:
    - trial_id: Trial to delete
    - username: Admin user requesting deletion
    """

    try:
        criteria_cache = dynamodb.Table(CRITERIA_CACHE_TABLE)

        # Get trial to verify it exists
        response = criteria_cache.get_item(Key={'trial_id': trial_id})

        if 'Item' not in response:
            return {
                'statusCode': 404,
                'headers': cors_headers(),
                'body': json.dumps({
                    'success': False,
                    'error': f'Trial not found: {trial_id}'
                })
            }

        trial = response['Item']

        # Archive metadata for audit purposes (optional)
        # In production, move to archive table instead of deleting

        # Delete from DynamoDB
        criteria_cache.delete_item(Key={'trial_id': trial_id})

        # Log deletion
        print(f"Trial {trial_id} deleted by {username} at {datetime.utcnow().isoformat()}")

        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': json.dumps({
                'success': True,
                'message': f'Trial {trial_id} deleted successfully',
                'deleted_by': username,
                'deleted_at': datetime.utcnow().isoformat()
            }, cls=DecimalEncoder)
        }

    except Exception as e:
        print(f"Error deleting trial: {str(e)}")
        raise


def get_all_trials_admin(query_params: Dict[str, str]) -> Dict[str, Any]:
    """
    Get all trials with admin-level details
    """

    try:
        criteria_cache = dynamodb.Table(CRITERIA_CACHE_TABLE)

        response = criteria_cache.scan()
        trials = response.get('Items', [])

        # Sort by processed_at (most recent first)
        trials.sort(key=lambda x: x.get('processed_at', ''), reverse=True)

        # Apply limit
        limit = int(query_params.get('limit', 50))
        trials = trials[:limit]

        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': json.dumps({
                'success': True,
                'trials': trials,
                'count': len(trials),
                'timestamp': datetime.utcnow().isoformat()
            }, cls=DecimalEncoder)
        }

    except Exception as e:
        print(f"Error getting trials: {str(e)}")
        raise


def get_pi_dashboard_metrics() -> Dict[str, Any]:
    """
    Get PI-specific dashboard metrics
    Returns: Active trials, pending approvals, match rate, recent pending reviews
    """
    try:
        criteria_cache = dynamodb.Table(CRITERIA_CACHE_TABLE)
        matches_table = dynamodb.Table(MATCHES_TABLE)

        # Get all protocols (trials)
        protocols_response = criteria_cache.scan()
        protocols = protocols_response.get('Items', [])
        total_protocols = len(protocols)

        # Get all matches
        matches_response = matches_table.scan()
        matches = matches_response.get('Items', [])

        # Calculate PI metrics
        pending_pi_approval = len([m for m in matches if m.get('status') == 'pending_pi_approval'])
        approved_matches = len([m for m in matches if m.get('status') == 'approved'])
        rejected_matches = len([m for m in matches if m.get('status') == 'rejected'])
        total_enrolled = approved_matches  # Assuming approved = enrolled

        # Calculate match rate
        total_reviewed = approved_matches + rejected_matches
        match_rate = round((approved_matches / total_reviewed * 100), 2) if total_reviewed > 0 else 0

        # Get pending approvals with details (last 10)
        pending_list = [m for m in matches if m.get('status') == 'pending_pi_approval']
        pending_list.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        pending_reviews = []
        for match in pending_list[:10]:
            pending_reviews.append({
                'id': match.get('match_id'),
                'patient': match.get('patient_id'),
                'protocol': match.get('protocol_id'),
                'confidence': match.get('match_score', 0),
                'date': match.get('created_at')
            })

        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': json.dumps({
                'success': True,
                'metrics': {
                    'active_trials': total_protocols,
                    'total_enrolled': total_enrolled,
                    'pending_pi_approval': pending_pi_approval,
                    'match_rate': match_rate
                },
                'pending_reviews': pending_reviews,
                'timestamp': datetime.utcnow().isoformat()
            }, cls=DecimalEncoder)
        }
    except Exception as e:
        print(f"Error getting PI dashboard metrics: {str(e)}")
        raise


def get_pi_trials() -> Dict[str, Any]:
    """
    Get all trials with enrollment metrics for PI
    """
    try:
        criteria_cache = dynamodb.Table(CRITERIA_CACHE_TABLE)
        matches_table = dynamodb.Table(MATCHES_TABLE)

        # Get all protocols
        protocols_response = criteria_cache.scan()
        protocols = protocols_response.get('Items', [])

        # Get all matches
        matches_response = matches_table.scan()
        matches = matches_response.get('Items', [])

        # Build trial list with enrollment metrics
        trials = []
        for protocol in protocols:
            trial_id = protocol.get('trial_id')

            # Filter matches for this trial
            trial_matches = [m for m in matches if m.get('protocol_id') == trial_id]

            # Calculate metrics
            enrolled = len([m for m in trial_matches if m.get('status') == 'approved'])
            pending = len([m for m in trial_matches if m.get('status') == 'pending_pi_approval'])
            rejected = len([m for m in trial_matches if m.get('status') == 'rejected'])

            # Calculate match rate
            total_reviewed = enrolled + rejected
            match_rate = round((enrolled / total_reviewed * 100), 2) if total_reviewed > 0 else 0

            trials.append({
                'id': trial_id,
                'title': protocol.get('title', trial_id),
                'identifier': trial_id,
                'enrolled': enrolled,
                'pending': pending,
                'rejected': rejected,
                'match_rate': match_rate,
                'target': 100,  # Placeholder, could be in protocol metadata
                'upload_date': protocol.get('timestamp')
            })

        # Sort by enrollment (most active first)
        trials.sort(key=lambda x: x['enrolled'], reverse=True)

        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': json.dumps({
                'success': True,
                'trials': trials,
                'count': len(trials),
                'timestamp': datetime.utcnow().isoformat()
            }, cls=DecimalEncoder)
        }
    except Exception as e:
        print(f"Error getting PI trials: {str(e)}")
        raise


def get_pi_trial_details(trial_id: str) -> Dict[str, Any]:
    """
    Get detailed enrollment data for a specific trial
    """
    try:
        criteria_cache = dynamodb.Table(CRITERIA_CACHE_TABLE)
        matches_table = dynamodb.Table(MATCHES_TABLE)

        # Get protocol
        protocol_response = criteria_cache.get_item(Key={'trial_id': trial_id})
        if 'Item' not in protocol_response:
            return {
                'statusCode': 404,
                'headers': cors_headers(),
                'body': json.dumps({'error': 'Trial not found'})
            }

        protocol = protocol_response['Item']

        # Get all matches for this trial
        matches_response = matches_table.scan(
            FilterExpression='protocol_id = :protocol_id',
            ExpressionAttributeValues={':protocol_id': trial_id}
        )
        matches = matches_response.get('Items', [])

        # Organize by status
        patient_roster = {
            'approved': [m for m in matches if m.get('status') == 'approved'],
            'pending_pi_approval': [m for m in matches if m.get('status') == 'pending_pi_approval'],
            'pending': [m for m in matches if m.get('status') == 'pending'],
            'rejected': [m for m in matches if m.get('status') == 'rejected']
        }

        # Calculate enrollment metrics
        total_screened = len(matches)
        approved = len(patient_roster['approved'])

        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': json.dumps({
                'success': True,
                'trial': {
                    'id': trial_id,
                    'title': protocol.get('title', trial_id),
                    'identifier': trial_id,
                    'upload_date': protocol.get('timestamp'),
                    'inclusion_criteria_count': len(protocol.get('inclusion_criteria', [])),
                    'exclusion_criteria_count': len(protocol.get('exclusion_criteria', []))
                },
                'enrollment': {
                    'total_screened': total_screened,
                    'approved': approved,
                    'pending_pi_approval': len(patient_roster['pending_pi_approval']),
                    'pending_crc': len(patient_roster['pending']),
                    'rejected': len(patient_roster['rejected']),
                    'enrollment_rate': round((approved / total_screened * 100), 2) if total_screened > 0 else 0
                },
                'patient_roster': patient_roster,
                'timestamp': datetime.utcnow().isoformat()
            }, cls=DecimalEncoder)
        }
    except Exception as e:
        print(f"Error getting trial details: {str(e)}")
        raise


def export_enrollment_summary(trial_id: str = None) -> Dict[str, Any]:
    """
    Generate CSV data for enrollment summary
    Returns CSV string that frontend can download
    """
    try:
        matches_table = dynamodb.Table(MATCHES_TABLE)

        # Get matches (filter by trial if provided)
        if trial_id:
            matches_response = matches_table.scan(
                FilterExpression='protocol_id = :protocol_id',
                ExpressionAttributeValues={':protocol_id': trial_id}
            )
        else:
            matches_response = matches_table.scan()

        matches = matches_response.get('Items', [])

        # Generate CSV
        csv_lines = ['Patient ID,Protocol ID,Match Score,Status,Created At,Reviewed By,Reviewed At']

        for match in matches:
            line = f"{match.get('patient_id')},{match.get('protocol_id')},{match.get('match_score')},{match.get('status')},{match.get('created_at')},{match.get('pi_reviewed_by', 'N/A')},{match.get('pi_reviewed_at', 'N/A')}"
            csv_lines.append(line)

        csv_content = '\n'.join(csv_lines)

        return {
            'statusCode': 200,
            'headers': {
                **cors_headers(),
                'Content-Type': 'text/csv',
                'Content-Disposition': f'attachment; filename="enrollment_summary_{trial_id or "all"}_{datetime.utcnow().strftime("%Y%m%d")}.csv"'
            },
            'body': csv_content
        }
    except Exception as e:
        print(f"Error exporting enrollment summary: {str(e)}")
        raise


def cors_headers() -> Dict[str, str]:
    """Return CORS headers for API Gateway"""
    return {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,Authorization,X-Requested-With',
        'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
    }
