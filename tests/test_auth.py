#!/usr/bin/env python3
"""
Test script for the custom authentication service
Run this script to test various authentication endpoints
"""

import requests
import json
from datetime import datetime

BASE_URL = "http://127.0.0.1:8000/api/auth"

def print_response(response, title):
    """Print formatted response"""
    print(f"\n{'='*50}")
    print(f"{title}")
    print(f"{'='*50}")
    print(f"Status Code: {response.status_code}")
    try:
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    except:
        print(f"Response: {response.text}")

def test_registration():
    """Test user registration"""
    url = f"{BASE_URL}/register/"
    data = {
        "email": "testuser@example.com",
        "first_name": "Test",
        "last_name": "User",
        "phone_number": "+1234567890",
        "password": "testpassword123",
        "password_confirm": "testpassword123"
    }
    
    response = requests.post(url, json=data)
    print_response(response, "USER REGISTRATION TEST")
    
    if response.status_code == 201:
        return response.json().get('tokens', {}).get('access')
    return None

def test_login():
    """Test user login"""
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

def test_profile(access_token):
    """Test getting user profile"""
    url = f"{BASE_URL}/profile/"
    headers = {"Authorization": f"Bearer {access_token}"}
    
    response = requests.get(url, headers=headers)
    print_response(response, "GET USER PROFILE TEST")

def test_countries():
    """Test getting countries list"""
    url = f"{BASE_URL}/countries/"
    
    response = requests.get(url)
    print_response(response, "GET COUNTRIES TEST")
    
    if response.status_code == 200:
        countries = response.json().get('results', [])
        if countries:
            return countries[0]['id']  # Return first country ID for testing
    return None

def test_currencies():
    """Test getting currencies list"""
    url = f"{BASE_URL}/currencies/"
    
    response = requests.get(url)
    print_response(response, "GET CURRENCIES TEST")
    
    if response.status_code == 200:
        currencies = response.json().get('results', [])
        if currencies:
            return currencies[0]['id']  # Return first currency ID for testing
    return None

def test_profile_update(access_token, country_id, currency_id):
    """Test updating user profile"""
    url = f"{BASE_URL}/profile/"
    headers = {"Authorization": f"Bearer {access_token}"}
    data = {
        "first_name": "Updated",
        "last_name": "Name",
        "phone_number": "+9876543210",
        "country_id": country_id,
        "preferred_currency_id": currency_id
    }
    
    response = requests.put(url, json=data, headers=headers)
    print_response(response, "UPDATE USER PROFILE TEST")

def test_sessions(access_token):
    """Test getting user sessions"""
    url = f"{BASE_URL}/sessions/"
    headers = {"Authorization": f"Bearer {access_token}"}
    
    response = requests.get(url, headers=headers)
    print_response(response, "GET USER SESSIONS TEST")

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

def test_user_stats(admin_token):
    """Test getting user statistics (admin only)"""
    url = f"{BASE_URL}/stats/"
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    response = requests.get(url, headers=headers)
    print_response(response, "GET USER STATS TEST (ADMIN)")

def main():
    """Run all tests"""
    print("🚀 Starting Authentication Service Tests")
    print(f"Testing against: {BASE_URL}")
    print(f"Test started at: {datetime.now()}")
    
    # Test basic endpoints that don't require authentication
    print("\n📋 Testing reference data endpoints...")
    country_id = test_countries()
    currency_id = test_currencies()
    
    # Test user registration
    print("\n👤 Testing user authentication...")
    access_token = test_registration()
    
    # If registration fails (user might already exist), try login
    if not access_token:
        print("\n🔄 Registration failed, trying login...")
        access_token = test_login()
    
    if access_token:
        # Test authenticated endpoints
        print("\n🔐 Testing authenticated endpoints...")
        test_profile(access_token)
        
        if country_id and currency_id:
            test_profile_update(access_token, country_id, currency_id)
            test_profile(access_token)  # Check updated profile
        
        test_sessions(access_token)
        
        # Test admin endpoints
        print("\n👑 Testing admin endpoints...")
        admin_token = test_admin_login()
        if admin_token:
            test_user_stats(admin_token)
    else:
        print("\n❌ Could not obtain access token. Check your server and try again.")
    
    print(f"\n✅ Tests completed at: {datetime.now()}")
    print("Check the results above for any errors.")

if __name__ == "__main__":
    main()
