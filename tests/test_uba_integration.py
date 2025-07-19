#!/usr/bin/env python3
"""
Test script for UBA Integration API endpoints
Tests all UBA endpoints with API key authentication
"""

import requests
import json
import sys

# Configuration
BASE_URL = "http://127.0.0.1:8000"
API_KEY = "pk_test_partner_h5XrpqSAwmXy7SeZ:LifKgZRFyO5iOe044J7gmPwFrPbbVbs_SKHfOEqaQzc"  # Generated API key

def test_uba_test_connection():
    """Test UBA connection"""
    print("\n=== Testing UBA Test Connection ===")
    
    url = f"{BASE_URL}/api/integrations/uba/test-connection/"
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

def test_uba_create_payment_page():
    """Test UBA payment page creation"""
    print("\n=== Testing UBA Payment Page Creation ===")
    
    url = f"{BASE_URL}/api/integrations/uba/payment-page/"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    payment_data = {
        "amount": "1000.00",
        "currency": "KES",
        "description": "Test payment",
        "reference": "test_payment_001",
        "customer_email": "test@example.com",
        "customer_phone": "+254712345678",
        "callback_url": "https://example.com/callback",
        "redirect_url": "https://example.com/success"
    }
    
    try:
        response = requests.post(url, headers=headers, json=payment_data)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 201:
            response_data = response.json()
            return True, response_data.get('data', {}).get('payment_id')
        return False, None
    except Exception as e:
        print(f"Error: {e}")
        return False, None

def test_uba_payment_status(payment_id):
    """Test UBA payment status"""
    print(f"\n=== Testing UBA Payment Status for {payment_id} ===")
    
    url = f"{BASE_URL}/api/integrations/uba/payment-status/{payment_id}/"
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

def test_uba_account_inquiry():
    """Test UBA account inquiry"""
    print("\n=== Testing UBA Account Inquiry ===")
    
    url = f"{BASE_URL}/api/integrations/uba/account-inquiry/"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    inquiry_data = {
        "account_number": "1234567890",
        "bank_code": "UBA_KE"
    }
    
    try:
        response = requests.post(url, headers=headers, json=inquiry_data)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_uba_balance_inquiry():
    """Test UBA balance inquiry"""
    print("\n=== Testing UBA Balance Inquiry ===")
    
    url = f"{BASE_URL}/api/integrations/uba/balance-inquiry/"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    balance_data = {
        "account_number": "1234567890",
        "bank_code": "UBA_KE"
    }
    
    try:
        response = requests.post(url, headers=headers, json=balance_data)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_uba_fund_transfer():
    """Test UBA fund transfer"""
    print("\n=== Testing UBA Fund Transfer ===")
    
    url = f"{BASE_URL}/api/integrations/uba/fund-transfer/"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    transfer_data = {
        "source_account": "1234567890",
        "destination_account": "0987654321",
        "amount": "500.00",
        "destination_bank_code": "UBA_KE",
        "narration": "Test transfer",
        "reference": "test_transfer_001"
    }
    
    try:
        response = requests.post(url, headers=headers, json=transfer_data)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 201
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_uba_transaction_history():
    """Test UBA transaction history"""
    print("\n=== Testing UBA Transaction History ===")
    
    url = f"{BASE_URL}/api/integrations/uba/transaction-history/"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    history_data = {
        "account_number": "1234567890",
        "start_date": "2025-01-01",
        "end_date": "2025-07-04",
        "limit": 10
    }
    
    try:
        response = requests.post(url, headers=headers, json=history_data)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_uba_bill_payment():
    """Test UBA bill payment"""
    print("\n=== Testing UBA Bill Payment ===")
    
    url = f"{BASE_URL}/api/integrations/uba/bill-payment/"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    bill_data = {
        "source_account": "1234567890",
        "biller_code": "KPLC",
        "customer_reference": "12345678901",
        "amount": "2500.00",
        "narration": "Electricity bill payment"
    }
    
    try:
        response = requests.post(url, headers=headers, json=bill_data)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 201
    except Exception as e:
        print(f"Error: {e}")
        return False

def main():
    """Run all UBA tests"""
    print("Starting UBA Integration Tests...")
    print(f"Base URL: {BASE_URL}")
    print(f"API Key: {API_KEY}")
    
    tests_passed = 0
    total_tests = 8
    
    # Test 1: Connection
    if test_uba_test_connection():
        print("✅ UBA connection test passed")
        tests_passed += 1
    else:
        print("❌ UBA connection test failed")
    
    # Test 2: Payment page creation
    success, payment_id = test_uba_create_payment_page()
    if success:
        print("✅ UBA payment page creation passed")
        tests_passed += 1
    else:
        print("❌ UBA payment page creation failed")
    
    # Test 3: Payment status (if payment was created)
    if payment_id:
        if test_uba_payment_status(payment_id):
            print("✅ UBA payment status check passed")
            tests_passed += 1
        else:
            print("❌ UBA payment status check failed")
    else:
        if test_uba_payment_status("test_payment_id"):
            print("✅ UBA payment status check passed")
            tests_passed += 1
        else:
            print("❌ UBA payment status check failed")
    
    # Test 4: Account inquiry
    if test_uba_account_inquiry():
        print("✅ UBA account inquiry passed")
        tests_passed += 1
    else:
        print("❌ UBA account inquiry failed")
    
    # Test 5: Balance inquiry
    if test_uba_balance_inquiry():
        print("✅ UBA balance inquiry passed")
        tests_passed += 1
    else:
        print("❌ UBA balance inquiry failed")
    
    # Test 6: Fund transfer
    if test_uba_fund_transfer():
        print("✅ UBA fund transfer passed")
        tests_passed += 1
    else:
        print("❌ UBA fund transfer failed")
    
    # Test 7: Transaction history
    if test_uba_transaction_history():
        print("✅ UBA transaction history passed")
        tests_passed += 1
    else:
        print("❌ UBA transaction history failed")
    
    # Test 8: Bill payment
    if test_uba_bill_payment():
        print("✅ UBA bill payment passed")
        tests_passed += 1
    else:
        print("❌ UBA bill payment failed")
    
    print(f"\n🎉 UBA integration tests completed!")
    print(f"Tests passed: {tests_passed}/{total_tests}")
    
    if tests_passed == total_tests:
        print("✅ All tests passed!")
        return True
    else:
        print(f"❌ {total_tests - tests_passed} tests failed")
        return False

if __name__ == "__main__":
    if not main():
        sys.exit(1)
    sys.exit(0)
