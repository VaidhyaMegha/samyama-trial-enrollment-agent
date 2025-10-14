#!/usr/bin/env python3
"""
Create Test Users in Cognito User Pool
Creates test users for each persona (CRC, StudyAdmin, PI) for development and testing
"""

import boto3
import json
import sys
from typing import Dict, List

# Initialize Cognito client
cognito = boto3.client('cognito-idp', region_name='us-east-1')


def load_configuration(filename: str = 'cognito-config.json') -> Dict:
    """
    Load Cognito configuration from JSON file

    Args:
        filename: Configuration file path

    Returns:
        Configuration dictionary
    """
    try:
        with open(filename, 'r') as f:
            config = json.load(f)
        return config
    except FileNotFoundError:
        print(f"❌ Error: {filename} not found!")
        print("   Please run 'python3 cognito_setup.py' first.")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"❌ Error: Invalid JSON in {filename}")
        sys.exit(1)


def create_user(user_pool_id: str, username: str, email: str, name: str, role: str, temp_password: str) -> bool:
    """
    Create a new user in the Cognito User Pool

    Args:
        user_pool_id: The Cognito User Pool ID
        username: Username for the user
        email: Email address
        name: Full name
        role: User role (CRC, StudyAdmin, PI)
        temp_password: Temporary password

    Returns:
        True if successful, False otherwise
    """
    try:
        response = cognito.admin_create_user(
            UserPoolId=user_pool_id,
            Username=username,
            UserAttributes=[
                {'Name': 'email', 'Value': email},
                {'Name': 'email_verified', 'Value': 'true'},
                {'Name': 'name', 'Value': name}
            ],
            TemporaryPassword=temp_password,
            MessageAction='SUPPRESS',  # Don't send email (for testing)
            DesiredDeliveryMediums=['EMAIL']
        )

        print(f"✅ User '{username}' created successfully")
        return True

    except cognito.exceptions.UsernameExistsException:
        print(f"⚠️  User '{username}' already exists, skipping...")
        return True

    except Exception as e:
        print(f"❌ Error creating user '{username}': {str(e)}")
        return False


def set_permanent_password(user_pool_id: str, username: str, password: str) -> bool:
    """
    Set permanent password for a user (skip temporary password flow)

    Args:
        user_pool_id: The Cognito User Pool ID
        username: Username
        password: Permanent password

    Returns:
        True if successful, False otherwise
    """
    try:
        cognito.admin_set_user_password(
            UserPoolId=user_pool_id,
            Username=username,
            Password=password,
            Permanent=True
        )

        print(f"   → Password set to permanent for '{username}'")
        return True

    except Exception as e:
        print(f"❌ Error setting permanent password for '{username}': {str(e)}")
        return False


def add_user_to_group(user_pool_id: str, username: str, group_name: str) -> bool:
    """
    Add user to a Cognito group

    Args:
        user_pool_id: The Cognito User Pool ID
        username: Username
        group_name: Group name (CRC, StudyAdmin, PI)

    Returns:
        True if successful, False otherwise
    """
    try:
        cognito.admin_add_user_to_group(
            UserPoolId=user_pool_id,
            Username=username,
            GroupName=group_name
        )

        print(f"   → Added to group '{group_name}'")
        return True

    except Exception as e:
        print(f"❌ Error adding user to group: {str(e)}")
        return False


def create_test_users(user_pool_id: str) -> List[Dict]:
    """
    Create test users for all three personas

    Args:
        user_pool_id: The Cognito User Pool ID

    Returns:
        List of created user details
    """
    print("\nCreating Test Users...")
    print("=" * 70)

    # Define test users for each persona
    test_users = [
        {
            'username': 'crc_test',
            'email': 'crc.test@example.com',
            'name': 'Sarah Johnson (CRC)',
            'role': 'CRC',
            'group': 'CRC',
            'password': 'TestCRC@2025!'
        },
        {
            'username': 'studyadmin_test',
            'email': 'studyadmin.test@example.com',
            'name': 'Michael Chen (Study Admin)',
            'role': 'StudyAdmin',
            'group': 'StudyAdmin',
            'password': 'TestAdmin@2025!'
        },
        {
            'username': 'pi_test',
            'email': 'pi.test@example.com',
            'name': 'Dr. Emily Rodriguez (PI)',
            'role': 'PI',
            'group': 'PI',
            'password': 'TestPI@2025!'
        }
    ]

    created_users = []

    for user in test_users:
        print(f"\n📝 Creating user: {user['name']}")
        print(f"   Username: {user['username']}")
        print(f"   Email: {user['email']}")
        print(f"   Role: {user['role']}")

        # Create user
        if create_user(
            user_pool_id=user_pool_id,
            username=user['username'],
            email=user['email'],
            name=user['name'],
            role=user['role'],
            temp_password='TempPass@123!'
        ):
            # Set permanent password
            set_permanent_password(user_pool_id, user['username'], user['password'])

            # Add to group
            add_user_to_group(user_pool_id, user['username'], user['group'])

            created_users.append({
                'username': user['username'],
                'email': user['email'],
                'name': user['name'],
                'role': user['role'],
                'password': user['password']
            })

    return created_users


def save_test_users_file(users: List[Dict], filename: str = 'test-users.json'):
    """
    Save test user credentials to JSON file

    Args:
        users: List of user dictionaries
        filename: Output filename
    """
    print(f"\n💾 Saving test user credentials to {filename}...")

    try:
        with open(filename, 'w') as f:
            json.dump({'users': users}, f, indent=2)

        print(f"✅ Test users saved successfully!")

    except Exception as e:
        print(f"❌ Error saving test users: {str(e)}")


def print_summary(users: List[Dict]):
    """
    Print summary of created test users

    Args:
        users: List of created user dictionaries
    """
    print("\n" + "=" * 70)
    print("✅ Test Users Created Successfully!")
    print("=" * 70)
    print("\n📋 Login Credentials:")
    print("-" * 70)

    for user in users:
        print(f"\n{user['name']}")
        print(f"  Role:     {user['role']}")
        print(f"  Username: {user['username']}")
        print(f"  Email:    {user['email']}")
        print(f"  Password: {user['password']}")

    print("\n" + "-" * 70)
    print("\n⚠️  IMPORTANT:")
    print("   - These are TEST users only (not for production)")
    print("   - Passwords are stored in test-users.json")
    print("   - Keep credentials secure and DO NOT commit to Git")
    print("   - Update .gitignore to exclude test-users.json")

    print("\n🔑 Testing Authentication:")
    print("   1. Use these credentials to test login flow")
    print("   2. Verify JWT tokens contain correct groups")
    print("   3. Test role-based access control on API endpoints")


def main():
    """Main execution function"""
    print("=" * 70)
    print("Creating Test Users in Cognito User Pool")
    print("=" * 70)

    # Load configuration
    config = load_configuration()
    user_pool_id = config['UserPoolId']

    print(f"\n📍 Target User Pool: {user_pool_id}")
    print(f"📍 Region: {config['Region']}")

    # Create test users
    created_users = create_test_users(user_pool_id)

    # Save credentials to file
    save_test_users_file(created_users)

    # Print summary
    print_summary(created_users)


if __name__ == '__main__':
    main()
