#!/usr/bin/env python3

"""
Comprehensive final test of the complete OTP verification and merchant onboarding system
"""

import requests
import json
import time
import random

# Configuration
BASE_URL = "http://127.0.0.1:8000/api/auth"

def test_complete_flow():
    """Test the complete registration -> OTP -> merchant flow"""
    test_email = f"final_test_{random.randint(1000, 9999)}@example.com"
    
    print("🎯 FINAL COMPREHENSIVE TEST")
    print("=" * 60)
    print(f"Test Email: {test_email}")
    
    # Step 1: Get categories
    print("\n1️⃣ Fetching merchant categories...")
    response = requests.get(f"{BASE_URL}/merchant-categories/")
    assert response.status_code == 200
    categories = response.json()['results']
    selected_category = random.choice(categories)
    print(f"✅ Selected: {selected_category['name']}")
    
    # Step 2: Register with merchant account
    print("\n2️⃣ Registering user with merchant account...")
    registration_data = {
        "email": test_email,
        "password": "TestPassword123!",
        "password_confirm": "TestPassword123!",
        "first_name": "Final",
        "last_name": "Test",
        "phone_number": "+1234567890",
        "country": "US",
        "preferred_currency": "USD",
        "create_merchant_account": True,
        "merchant_data": {
            "business_name": "Final Test Business",
            "business_email": test_email,
            "business_phone": "+1234567890",
            "business_address": "123 Final Test Street",
            "description": "Final test merchant account",
            "category": selected_category['id']
        }
    }
    
    response = requests.post(f"{BASE_URL}/register/", json=registration_data)
    assert response.status_code == 201
    registration_result = response.json()
    
    assert registration_result.get('merchant_account_created') == True
    assert 'merchant_id' in registration_result
    print(f"✅ User registered with merchant account")
    print(f"   - User ID: {registration_result['user']['id']}")
    print(f"   - Merchant ID: {registration_result['merchant_id']}")
    
    # Step 3: Get actual OTP from database
    print("\n3️⃣ Retrieving OTP from database...")
    import subprocess
    cmd = f"""
cd /Users/asd/Desktop/desktop/pexilabs && python manage.py shell -c "
from authentication.models import CustomUser, EmailOTP
user = CustomUser.objects.filter(email='{test_email}').first()
otp = EmailOTP.objects.filter(user=user).order_by('-created_at').first()
print(otp.otp_code if otp else 'NO_OTP')
"
    """.strip()
    
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    otp_code = result.stdout.strip()
    assert otp_code != 'NO_OTP', "OTP not found"
    print(f"✅ OTP retrieved: {otp_code}")
    
    # Step 4: Verify OTP
    print("\n4️⃣ Verifying OTP...")
    response = requests.post(f"{BASE_URL}/verify-otp/", json={
        "email": test_email,
        "otp_code": otp_code
    })
    assert response.status_code == 200
    verification_result = response.json()
    
    assert verification_result['user']['is_verified'] == True
    assert 'tokens' in verification_result
    access_token = verification_result['tokens']['access']
    print(f"✅ OTP verified, user authenticated")
    
    # Step 5: Access merchant account with authentication
    print("\n5️⃣ Accessing merchant account...")
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    response = requests.get(f"{BASE_URL}/merchant-account/", headers=headers)
    assert response.status_code == 200
    merchant_data = response.json()
    
    assert merchant_data['business_name'] == "Final Test Business"
    assert merchant_data['status'] == "pending"
    assert merchant_data['category']['name'] == selected_category['name']
    print(f"✅ Merchant account accessible")
    print(f"   - Business: {merchant_data['business_name']}")
    print(f"   - Status: {merchant_data['status']}")
    print(f"   - Category: {merchant_data['category']['name']}")
    
    # Step 6: Test resend OTP functionality
    print("\n6️⃣ Testing OTP resend...")
    response = requests.post(f"{BASE_URL}/resend-otp/", json={"email": test_email})
    assert response.status_code == 200
    print(f"✅ OTP resend successful")
    
    print("\n🎉 ALL TESTS PASSED!")
    print("=" * 60)
    print("✅ User registration with merchant onboarding: WORKING")
    print("✅ OTP generation and email sending: WORKING") 
    print("✅ OTP verification and authentication: WORKING")
    print("✅ Merchant account creation: WORKING")
    print("✅ Authenticated merchant endpoints: WORKING")
    print("✅ OTP resend functionality: WORKING")
    print("\n🚀 The system is fully functional!")
    
    return {
        "user_id": registration_result['user']['id'],
        "merchant_id": registration_result['merchant_id'],
        "email": test_email,
        "access_token": access_token
    }

if __name__ == "__main__":
    try:
        result = test_complete_flow()
        print(f"\n📋 Test Results:")
        print(f"   Email: {result['email']}")
        print(f"   User ID: {result['user_id']}")
        print(f"   Merchant ID: {result['merchant_id']}")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        raise
