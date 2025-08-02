#!/usr/bin/env python
"""
Test registration to OTP verification flow
"""
import os
import django
import sys

sys.path.append('/Users/asd/Desktop/desktop/pexilabs')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pexilabs.settings')
django.setup()

from django.test import Client
from django.urls import reverse
from authentication.models import CustomUser, Country, PreferredCurrency, MerchantCategory

def test_registration_flow():
    print("=== Testing Registration -> OTP Verification Flow ===")
    
    # Clean up test user
    test_email = "flow_test@example.com"
    CustomUser.objects.filter(email=test_email).delete()
    
    # Get reference data
    country = Country.objects.first()
    currency = PreferredCurrency.objects.first()
    category = MerchantCategory.objects.first()
    
    print(f"Using: {country.name}, {currency.name}, {category.name}")
    
    # Registration data
    data = {
        'first_name': 'Flow',
        'last_name': 'Test',
        'email': test_email,
        'password': 'flowtest123',
        'confirm_password': 'flowtest123',
        'phone': '+1234567890',
        'country': str(country.id),
        'currency': str(currency.id),
        'business_name': 'Flow Test Business',
        'merchant_category': str(category.id),
    }
    
    # Submit registration
    client = Client()
    response = client.post('/auth/register/', data)
    
    print(f"Response status: {response.status_code}")
    
    if response.status_code == 302:
        redirect_url = response.get('Location', '')
        print(f"Redirect URL: {redirect_url}")
        
        # Check if user was created
        if CustomUser.objects.filter(email=test_email).exists():
            user = CustomUser.objects.get(email=test_email)
            print(f"✅ User created: {user}")
            
            # Check OTP
            from authentication.models import EmailOTP
            otp_count = EmailOTP.objects.filter(user=user).count()
            print(f"✅ OTP records: {otp_count}")
            
            # Check expected redirect
            expected_url = f"/auth/verify/{user.id}/"
            print(f"Expected URL: {expected_url}")
            
            if expected_url in redirect_url:
                print("✅ SUCCESS: Registration -> OTP flow working!")
                return True
            else:
                print("❌ Wrong redirect URL")
                return False
        else:
            print("❌ User not created")
            return False
    else:
        print(f"❌ Expected redirect (302) but got {response.status_code}")
        return False

if __name__ == '__main__':
    success = test_registration_flow()
    if success:
        print("\n🎉 Registration flow is working correctly!")
    else:
        print("\n❌ Registration flow has issues!")
        sys.exit(1)
