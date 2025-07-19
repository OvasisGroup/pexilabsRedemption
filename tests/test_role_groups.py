#!/usr/bin/env python3
"""
Test script for role-based group inheritance in the authentication service
"""

import requests
import json
from datetime import datetime

BASE_URL = "http://127.0.0.1:8000/api/auth"

def print_response(response, title):
    """Print formatted response"""
    print(f"\n{'='*60}")
    print(f"{title}")
    print(f"{'='*60}")
    print(f"Status Code: {response.status_code}")
    try:
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    except:
        print(f"Response: {response.text}")

def test_admin_login():
    """Test admin login"""
    url = f"{BASE_URL}/login/"
    data = {
        "email": "admin@example.com",
        "password": "admin123"
    }
    
    response = requests.post(url, json=data)
    print_response(response, "ADMIN LOGIN TEST")
    
    if response.status_code == 200:
        return response.json().get('tokens', {}).get('access')
    return None

def test_user_login():
    """Test regular user login"""
    url = f"{BASE_URL}/login/"
    data = {
        "email": "testuser@example.com",
        "password": "testpassword123"
    }
    
    response = requests.post(url, json=data)
    print_response(response, "USER LOGIN TEST")
    
    if response.status_code == 200:
        return response.json().get('tokens', {}).get('access')
    return None

def test_user_profile_with_groups(access_token, user_type):
    """Test getting user profile including groups"""
    url = f"{BASE_URL}/profile/"
    headers = {"Authorization": f"Bearer {access_token}"}
    
    response = requests.get(url, headers=headers)
    print_response(response, f"GET {user_type.upper()} PROFILE WITH GROUPS")

def test_user_permissions(access_token, user_type):
    """Test getting user permissions"""
    url = f"{BASE_URL}/permissions/"
    headers = {"Authorization": f"Bearer {access_token}"}
    
    response = requests.get(url, headers=headers)
    print_response(response, f"GET {user_type.upper()} PERMISSIONS")

def test_groups_list(access_token, user_type):
    """Test getting groups list"""
    url = f"{BASE_URL}/groups/"
    headers = {"Authorization": f"Bearer {access_token}"}
    
    response = requests.get(url, headers=headers)
    print_response(response, f"GET GROUPS LIST ({user_type.upper()})")

def test_role_groups_list(access_token, user_type):
    """Test getting role group mappings"""
    url = f"{BASE_URL}/role-groups/"
    headers = {"Authorization": f"Bearer {access_token}"}
    
    response = requests.get(url, headers=headers)
    print_response(response, f"GET ROLE GROUP MAPPINGS ({user_type.upper()})")

def test_role_management(admin_token, user_id):
    """Test role management functionality"""
    # First, get the user's current role
    url = f"{BASE_URL}/users/{user_id}/role/"
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    response = requests.get(url, headers=headers)
    print_response(response, "GET USER ROLE INFO")
    
    if response.status_code == 200:
        current_role = response.json().get('role')
        
        # Try to change role to moderator
        new_role = 'moderator' if current_role == 'user' else 'user'
        update_data = {'role': new_role}
        
        response = requests.put(url, json=update_data, headers=headers)
        print_response(response, f"UPDATE USER ROLE TO {new_role.upper()}")
        
        # Change it back
        if response.status_code == 200:
            restore_data = {'role': current_role}
            response = requests.put(url, json=restore_data, headers=headers)
            print_response(response, f"RESTORE USER ROLE TO {current_role.upper()}")

def test_assign_role_endpoint(admin_token, user_id):
    """Test the assign role endpoint"""
    url = f"{BASE_URL}/users/{user_id}/assign-role/"
    headers = {"Authorization": f"Bearer {admin_token}"}
    data = {'role': 'moderator'}
    
    response = requests.post(url, json=data, headers=headers)
    print_response(response, "ASSIGN USER ROLE (MODERATOR)")
    
    # Restore original role
    if response.status_code == 200:
        restore_data = {'role': 'user'}
        response = requests.post(url, json=restore_data, headers=headers)
        print_response(response, "RESTORE USER ROLE (USER)")

def test_permission_denied_scenarios(user_token):
    """Test scenarios where regular users should be denied access"""
    headers = {"Authorization": f"Bearer {user_token}"}
    
    # Try to access groups (should be denied)
    response = requests.get(f"{BASE_URL}/groups/", headers=headers)
    print_response(response, "USER TRYING TO ACCESS GROUPS (SHOULD BE DENIED)")
    
    # Try to access role groups (should be denied)
    response = requests.get(f"{BASE_URL}/role-groups/", headers=headers)
    print_response(response, "USER TRYING TO ACCESS ROLE GROUPS (SHOULD BE DENIED)")

def get_user_id_from_profile(access_token):
    """Get user ID from profile"""
    url = f"{BASE_URL}/profile/"
    headers = {"Authorization": f"Bearer {access_token}"}
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json().get('id')
    return None

def main():
    """Run all role-based group tests"""
    print("🚀 Starting Role-Based Group Inheritance Tests")
    print(f"Testing against: {BASE_URL}")
    print(f"Test started at: {datetime.now()}")
    
    # Test admin functionality
    print("\n👑 Testing Admin User with Role-Based Groups...")
    admin_token = test_admin_login()
    
    if admin_token:
        test_user_profile_with_groups(admin_token, "admin")
        test_user_permissions(admin_token, "admin")
        test_groups_list(admin_token, "admin")
        test_role_groups_list(admin_token, "admin")
    
    # Test regular user functionality
    print("\n👤 Testing Regular User with Role-Based Groups...")
    user_token = test_user_login()
    
    if user_token:
        test_user_profile_with_groups(user_token, "user")
        test_user_permissions(user_token, "user")
        
        # Test permission denied scenarios
        print("\n🚫 Testing Permission Denied Scenarios...")
        test_permission_denied_scenarios(user_token)
        
        # Get user ID for role management tests
        user_id = get_user_id_from_profile(user_token)
        
        if admin_token and user_id:
            print("\n⚙️ Testing Role Management...")
            test_role_management(admin_token, user_id)
            test_assign_role_endpoint(admin_token, user_id)
    
    print(f"\n✅ Role-based group tests completed at: {datetime.now()}")
    print("Check the results above for proper group inheritance and permissions.")

if __name__ == "__main__":
    main()
