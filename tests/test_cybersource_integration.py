#!/usr/bin/env python3
"""
Test script for CyberSource Integration API endpoints
Tests all CyberSource endpoints with API key authentication
"""

import requests
import json
import sys

# Configuration
BASE_URL = "http://127.0.0.1:8000"
API_KEY = "pk_test_partner_h5XrpqSAwmXy7SeZ:LifKgZRFyO5iOe044J7gmPwFrPbbVbs_SKHfOEqaQzc"  # Generated from create_api_key command

def test_cybersource_test_connection():
    """Test CyberSource connection"""
    print("\n=== Testing CyberSource Test Connection ===")
    
    url = f"{BASE_URL}/api/integrations/cybersource/test-connection/"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(url, headers=headers)  # Changed to GET
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_cybersource_create_payment():
    """Test CyberSource payment creation"""
    print("\n=== Testing CyberSource Payment Creation ===")
    
    url = f"{BASE_URL}/api/integrations/cybersource/payment/"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    payment_data = {
        "amount": "100.00",
        "currency": "USD",
        "card_number": "4111111111111111",
        "expiry_month": "12",
        "expiry_year": "2025",
        "cvv": "123",
        "cardholder_name": "John Doe",
        "billing_first_name": "John",
        "billing_last_name": "Doe",
        "billing_address1": "123 Main St",
        "billing_city": "New York",
        "billing_state": "NY",
        "billing_postal_code": "10001",
        "billing_country": "US",
        "billing_email": "john.doe@example.com",
        "reference": "test_payment_001"
    }
    
    try:
        response = requests.post(url, headers=headers, json=payment_data)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 201:
            response_data = response.json()
            return True, response_data.get('payment_id')
        return False, None
    except Exception as e:
        print(f"Error: {e}")
        return False, None

def test_cybersource_payment_status(payment_id):
    """Test CyberSource payment status"""
    print(f"\n=== Testing CyberSource Payment Status for {payment_id} ===")
    
    url = f"{BASE_URL}/api/integrations/cybersource/payment-status/{payment_id}/"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(url, headers=headers)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_cybersource_create_customer():
    """Test CyberSource customer creation"""
    print("\n=== Testing CyberSource Customer Creation ===")
    
    url = f"{BASE_URL}/api/integrations/cybersource/customer/"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    customer_data = {
        "customer_id": "test_customer_001",
        "email": "customer@example.com",
        "first_name": "Jane",
        "last_name": "Smith",
        "phone": "+1234567890"
    }
    
    try:
        response = requests.post(url, headers=headers, json=customer_data)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 201
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_cybersource_create_token():
    """Test CyberSource token creation"""
    print("\n=== Testing CyberSource Token Creation ===")
    
    url = f"{BASE_URL}/api/integrations/cybersource/token/"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    token_data = {
        "card_number": "4111111111111111",
        "expiry_month": "12",
        "expiry_year": "2025",
        "cardholder_name": "Jane Smith",
        "customer_id": "test_customer_001"
    }
    
    try:
        response = requests.post(url, headers=headers, json=token_data)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 201
    except Exception as e:
        print(f"Error: {e}")
        return False

def main():
    """Run all CyberSource tests"""
    print("Starting CyberSource Integration Tests...")
    print(f"Base URL: {BASE_URL}")
    print(f"API Key: {API_KEY}")
    
    # Test 1: Connection
    if not test_cybersource_test_connection():
        print("❌ CyberSource connection test failed")
        return False
    else:
        print("✅ CyberSource connection test passed")
    
    # Test 2: Customer creation
    if not test_cybersource_create_customer():
        print("❌ CyberSource customer creation failed")
    else:
        print("✅ CyberSource customer creation passed")
    
    # Test 3: Token creation
    if not test_cybersource_create_token():
        print("❌ CyberSource token creation failed")
    else:
        print("✅ CyberSource token creation passed")
    
    # Test 4: Payment creation
    success, payment_id = test_cybersource_create_payment()
    if not success:
        print("❌ CyberSource payment creation failed")
        return False
    else:
        print("✅ CyberSource payment creation passed")
    
    # Test 5: Payment status (if payment was created)
    if payment_id:
        if not test_cybersource_payment_status(payment_id):
            print("❌ CyberSource payment status check failed")
        else:
            print("✅ CyberSource payment status check passed")
    
    print("\n🎉 All CyberSource integration tests completed!")
    return True

if __name__ == "__main__":
    if not main():
        sys.exit(1)
    sys.exit(0)
