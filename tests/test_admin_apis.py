#!/usr/bin/env python3
"""
Test script for Admin APIs with Cognito SRP authentication
"""

import requests
import json
from pycognito import Cognito

# Cognito Configuration
USER_POOL_ID = 'us-east-1_zLcYERVQI'
CLIENT_ID = '37ef9023q0b9q6lsdvc5rlvpo1'
REGION = 'us-east-1'

# Test user credentials
USERNAME = 'studyadmin_test'
PASSWORD = 'TestAdmin@2025!'

# API Gateway URL
API_URL = 'https://gt7dlyqj78.execute-api.us-east-1.amazonaws.com/prod'

def authenticate():
    """Authenticate user and get ID token using SRP"""
    try:
        user = Cognito(
            user_pool_id=USER_POOL_ID,
            client_id=CLIENT_ID,
            username=USERNAME,
            user_pool_region=REGION
        )

        user.authenticate(password=PASSWORD)
        id_token = user.id_token

        print(f"✅ Authentication successful for {USERNAME}")
        return id_token

    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_admin_dashboard(token):
    """Test GET /admin/dashboard"""
    print("\n🧪 Testing GET /admin/dashboard...")

    response = requests.get(
        f"{API_URL}/admin/dashboard",
        headers={'Authorization': f'Bearer {token}'}
    )

    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Dashboard metrics retrieved:")
        print(json.dumps(data, indent=2))
    else:
        print(f"❌ Error: {response.text}")

    return response.status_code == 200


def test_admin_processing_status(token):
    """Test GET /admin/processing-status"""
    print("\n🧪 Testing GET /admin/processing-status...")

    response = requests.get(
        f"{API_URL}/admin/processing-status",
        headers={'Authorization': f'Bearer {token}'}
    )

    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Processing status retrieved:")
        print(f"   Total protocols: {len(data.get('protocols', []))}")
        print(f"   Protocols: {json.dumps(data, indent=2)}")
    else:
        print(f"❌ Error: {response.text}")

    return response.status_code == 200


def test_admin_trials(token):
    """Test GET /admin/trials"""
    print("\n🧪 Testing GET /admin/trials...")

    response = requests.get(
        f"{API_URL}/admin/trials",
        headers={'Authorization': f'Bearer {token}'}
    )

    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Trials retrieved:")
        print(f"   Total trials: {data.get('count', 0)}")
        if data.get('trials'):
            print(f"   First trial: {data['trials'][0].get('trial_id', 'N/A')}")
    else:
        print(f"❌ Error: {response.text}")

    return response.status_code == 200


def test_admin_audit_trail(token):
    """Test GET /admin/audit-trail"""
    print("\n🧪 Testing GET /admin/audit-trail...")

    response = requests.get(
        f"{API_URL}/admin/audit-trail",
        headers={'Authorization': f'Bearer {token}'}
    )

    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Audit trail retrieved:")
        print(f"   Total events: {data.get('count', 0)}")
    else:
        print(f"❌ Error: {response.text}")

    return response.status_code == 200


def test_admin_logs(token):
    """Test GET /admin/logs"""
    print("\n🧪 Testing GET /admin/logs...")

    response = requests.get(
        f"{API_URL}/admin/logs?limit=10",
        headers={'Authorization': f'Bearer {token}'}
    )

    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"✅ System logs retrieved:")
        print(f"   Total logs: {len(data.get('logs', []))}")
        if data.get('logs'):
            print(f"   First log: {data['logs'][0].get('message', 'N/A')[:100]}")
    else:
        print(f"❌ Error: {response.text}")

    return response.status_code == 200


def main():
    """Run all admin API tests"""
    print("=" * 60)
    print("Admin API Test Suite - StudyAdmin Persona")
    print("=" * 60)

    # Authenticate
    token = authenticate()
    if not token:
        print("\n❌ Cannot proceed without authentication token")
        return

    # Run tests
    results = {
        'Dashboard': test_admin_dashboard(token),
        'Processing Status': test_admin_processing_status(token),
        'Trials List': test_admin_trials(token),
        'Audit Trail': test_admin_audit_trail(token),
        'System Logs': test_admin_logs(token)
    }

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary:")
    print("=" * 60)
    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")

    print(f"\nTotal: {passed}/{total} tests passed")
    print("=" * 60)


if __name__ == '__main__':
    main()
