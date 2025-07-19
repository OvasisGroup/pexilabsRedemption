#!/usr/bin/env python3

"""
Test business name integration with user registration and merchant account creation
"""

import requests
import json
import random

# Configuration
BASE_URL = "http://127.0.0.1:8000/api/auth"

def test_business_name_registration():
    """Test user registration with business name and merchant account creation"""
    test_email = f"business_test_{random.randint(1000, 9999)}@example.com"
    business_name = "My Awesome Business"
    
    print("🏢 BUSINESS NAME REGISTRATION TEST")
    print("=" * 60)
    print(f"Test Email: {test_email}")
    print(f"Business Name: {business_name}")
    
    # Test 1: Simple registration with business name and create_merchant_account=True
    print("\n1️⃣ Testing simple registration with business name...")
    registration_data = {
        "email": test_email,
        "password": "TestPassword123!",
        "password_confirm": "TestPassword123!",
        "first_name": "Business",
        "last_name": "Owner",
        "phone_number": "+1234567890",
        "business_name": business_name,
        "create_merchant_account": True
    }
    
    response = requests.post(f"{BASE_URL}/register/", json=registration_data)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 201:
        result = response.json()
        print(f"✅ Registration successful")
        print(f"   - User ID: {result['user']['id']}")
        print(f"   - Merchant Created: {result.get('merchant_account_created', False)}")
        print(f"   - Merchant ID: {result.get('merchant_id', 'N/A')}")
        
        # Get OTP from database
        import subprocess
        cmd = f"""
cd /Users/asd/Desktop/desktop/pexilabs && python manage.py shell -c "
from authentication.models import CustomUser, EmailOTP, Merchant
user = CustomUser.objects.filter(email='{test_email}').first()
otp = EmailOTP.objects.filter(user=user).order_by('-created_at').first()
merchant = Merchant.objects.filter(user=user).first()
print(f'OTP:{{otp.otp_code if otp else \"NO_OTP\"}}')
print(f'MERCHANT_NAME:{{merchant.business_name if merchant else \"NO_MERCHANT\"}}')
print(f'MERCHANT_EMAIL:{{merchant.business_email if merchant else \"NO_EMAIL\"}}')
"
        """.strip()
        
        db_result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        lines = db_result.stdout.strip().split('\n')
        otp_code = None
        merchant_name = None
        merchant_email = None
        
        for line in lines:
            if line.startswith('OTP:'):
                otp_code = line.split(':')[1]
            elif line.startswith('MERCHANT_NAME:'):
                merchant_name = line.split(':')[1]
            elif line.startswith('MERCHANT_EMAIL:'):
                merchant_email = line.split(':')[1]
        
        print(f"\n2️⃣ Checking merchant account creation...")
        if merchant_name and merchant_name == business_name:
            print(f"✅ Merchant account created with correct business name: {merchant_name}")
        else:
            print(f"❌ Merchant business name mismatch. Expected: {business_name}, Got: {merchant_name}")
        
        if merchant_email and merchant_email == test_email:
            print(f"✅ Merchant email linked correctly: {merchant_email}")
        else:
            print(f"❌ Merchant email mismatch. Expected: {test_email}, Got: {merchant_email}")
        
        # Test OTP verification
        if otp_code and otp_code != 'NO_OTP':
            print(f"\n3️⃣ Testing OTP verification...")
            otp_response = requests.post(f"{BASE_URL}/verify-otp/", json={
                "email": test_email,
                "otp_code": otp_code
            })
            
            if otp_response.status_code == 200:
                otp_result = otp_response.json()
                access_token = otp_result['tokens']['access']
                print(f"✅ OTP verified successfully")
                
                # Test merchant account access
                print(f"\n4️⃣ Testing merchant account access...")
                headers = {"Authorization": f"Bearer {access_token}"}
                merchant_response = requests.get(f"{BASE_URL}/merchant-account/", headers=headers)
                
                if merchant_response.status_code == 200:
                    merchant_data = merchant_response.json()
                    print(f"✅ Merchant account accessible")
                    print(f"   - Business Name: {merchant_data['business_name']}")
                    print(f"   - Business Email: {merchant_data['business_email']}")
                    print(f"   - Status: {merchant_data['status']}")
                    
                    if merchant_data['business_name'] == business_name:
                        print(f"✅ Business name correctly linked: {business_name}")
                    else:
                        print(f"❌ Business name mismatch in merchant account")
                else:
                    print(f"❌ Failed to access merchant account: {merchant_response.status_code}")
            else:
                print(f"❌ OTP verification failed: {otp_response.status_code}")
        else:
            print(f"❌ No OTP found for verification")
    else:
        print(f"❌ Registration failed: {response.status_code}")
        print(f"Response: {response.text}")
    
    print(f"\n🎯 Test Summary:")
    print(f"   - Registration with business name: {'✅' if response.status_code == 201 else '❌'}")
    print(f"   - Merchant account auto-creation: {'✅' if merchant_name == business_name else '❌'}")
    print(f"   - Business name linking: {'✅' if merchant_name == business_name else '❌'}")


def test_registration_without_merchant_data():
    """Test that business name creates merchant account even without explicit merchant_data"""
    test_email = f"simple_test_{random.randint(1000, 9999)}@example.com"
    
    print(f"\n\n🔧 SIMPLE BUSINESS REGISTRATION TEST")
    print("=" * 60)
    print(f"Test Email: {test_email}")
    
    registration_data = {
        "email": test_email,
        "password": "TestPassword123!",
        "password_confirm": "TestPassword123!",
        "first_name": "Simple",
        "last_name": "Business",
        "phone_number": "+1234567890",
        "business_name": "Simple Test Business",
        "create_merchant_account": True
        # Note: No merchant_data provided
    }
    
    response = requests.post(f"{BASE_URL}/register/", json=registration_data)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 201:
        result = response.json()
        merchant_created = result.get('merchant_account_created', False)
        print(f"✅ Registration successful")
        print(f"   - Merchant Created: {merchant_created}")
        
        if merchant_created:
            print(f"✅ Merchant account created from business_name only")
        else:
            print(f"❌ Merchant account not created")
    else:
        print(f"❌ Registration failed: {response.status_code}")


if __name__ == "__main__":
    try:
        test_business_name_registration()
        test_registration_without_merchant_data()
        print(f"\n🎉 All business name tests completed!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        raise
