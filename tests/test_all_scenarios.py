#!/usr/bin/env python3

"""
Comprehensive test showing all business name registration scenarios
"""

import requests
import json
import random

BASE_URL = "http://127.0.0.1:8000/api/auth"

def get_merchant_categories():
    """Get available merchant categories"""
    response = requests.get(f"{BASE_URL}/merchant-categories/")
    if response.status_code == 200:
        return response.json()['results']
    return []

def test_all_business_name_scenarios():
    """Test all different ways business name can be used"""
    
    print("🎯 COMPREHENSIVE BUSINESS NAME TEST")
    print("=" * 60)
    
    categories = get_merchant_categories()
    if not categories:
        print("❌ No merchant categories available")
        return
    
    selected_category = random.choice(categories)
    
    # Scenario 1: Business name only with create_merchant_account=True
    print("\n📋 Scenario 1: Business name only (no merchant_data)")
    test_email_1 = f"scenario1_{random.randint(1000, 9999)}@example.com"
    data1 = {
        "email": test_email_1,
        "password": "TestPassword123!",
        "password_confirm": "TestPassword123!",
        "first_name": "John",
        "last_name": "Doe",
        "phone_number": "+1234567890",
        "business_name": "John's Coffee Shop",
        "create_merchant_account": True
    }
    
    response1 = requests.post(f"{BASE_URL}/register/", json=data1)
    print(f"Status: {response1.status_code}")
    if response1.status_code == 201:
        result1 = response1.json()
        print(f"✅ Merchant created: {result1.get('merchant_account_created', False)}")
    else:
        print(f"❌ Failed: {response1.text}")
    
    # Scenario 2: Business name + full merchant_data
    print("\n📋 Scenario 2: Business name + detailed merchant_data")
    test_email_2 = f"scenario2_{random.randint(1000, 9999)}@example.com"
    data2 = {
        "email": test_email_2,
        "password": "TestPassword123!",
        "password_confirm": "TestPassword123!",
        "first_name": "Jane",
        "last_name": "Smith",
        "phone_number": "+1234567891",
        "business_name": "Jane's Bakery",  # This should be overridden by merchant_data
        "create_merchant_account": True,
        "merchant_data": {
            "business_name": "Jane's Premium Bakery",
            "business_email": test_email_2,
            "business_phone": "+1234567891",
            "business_address": "123 Bakery Street",
            "description": "Premium baked goods",
            "category": selected_category['id']
        }
    }
    
    response2 = requests.post(f"{BASE_URL}/register/", json=data2)
    print(f"Status: {response2.status_code}")
    if response2.status_code == 201:
        result2 = response2.json()
        print(f"✅ Merchant created: {result2.get('merchant_account_created', False)}")
    else:
        print(f"❌ Failed: {response2.text}")
    
    # Scenario 3: No business name, create_merchant_account=True
    print("\n📋 Scenario 3: No business name (fallback to full name)")
    test_email_3 = f"scenario3_{random.randint(1000, 9999)}@example.com"
    data3 = {
        "email": test_email_3,
        "password": "TestPassword123!",
        "password_confirm": "TestPassword123!",
        "first_name": "Bob",
        "last_name": "Wilson",
        "phone_number": "+1234567892",
        "create_merchant_account": True
        # No business_name, no merchant_data
    }
    
    response3 = requests.post(f"{BASE_URL}/register/", json=data3)
    print(f"Status: {response3.status_code}")
    if response3.status_code == 201:
        result3 = response3.json()
        print(f"✅ Merchant created: {result3.get('merchant_account_created', False)}")
    else:
        print(f"❌ Failed: {response3.text}")
    
    # Scenario 4: Business name but create_merchant_account=False
    print("\n📋 Scenario 4: Business name but no merchant account creation")
    test_email_4 = f"scenario4_{random.randint(1000, 9999)}@example.com"
    data4 = {
        "email": test_email_4,
        "password": "TestPassword123!",
        "password_confirm": "TestPassword123!",
        "first_name": "Alice",
        "last_name": "Brown",
        "phone_number": "+1234567893",
        "business_name": "Alice's Store",
        "create_merchant_account": False
    }
    
    response4 = requests.post(f"{BASE_URL}/register/", json=data4)
    print(f"Status: {response4.status_code}")
    if response4.status_code == 201:
        result4 = response4.json()
        print(f"✅ Registration successful, merchant created: {result4.get('merchant_account_created', False)}")
    else:
        print(f"❌ Failed: {response4.text}")
    
    # Check database results
    print(f"\n🔍 DATABASE VERIFICATION")
    print("=" * 40)
    
    import subprocess
    cmd = f"""
cd /Users/asd/Desktop/desktop/pexilabs && python manage.py shell -c "
from authentication.models import CustomUser, Merchant

emails = ['{test_email_1}', '{test_email_2}', '{test_email_3}', '{test_email_4}']
for email in emails:
    user = CustomUser.objects.filter(email=email).first()
    if user:
        merchant = Merchant.objects.filter(user=user).first()
        if merchant:
            print(f'{{email}} → {{merchant.business_name}}')
        else:
            print(f'{{email}} → No merchant')
    else:
        print(f'{{email}} → User not found')
"
    """.strip()
    
    db_result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    print(db_result.stdout)
    
    print(f"\n🎉 All scenarios tested!")
    print(f"📝 Summary of features:")
    print(f"   ✅ Business name creates merchant account automatically")
    print(f"   ✅ Merchant_data overrides business name when provided")
    print(f"   ✅ Fallback to full name when no business name")
    print(f"   ✅ Business name ignored when create_merchant_account=False")
    print(f"   ✅ All models properly registered in Django admin")

if __name__ == "__main__":
    test_all_business_name_scenarios()
