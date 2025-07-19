#!/usr/bin/env python
import os
import django
import sys

sys.path.insert(0, '/Users/asd/Desktop/desktop/pexilabs')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pexilabs.settings')
django.setup()

from django.test import Client
from django.urls import reverse
from authentication.models import CustomUser, Country, PreferredCurrency, MerchantCategory

print("=== Registration Test with Debug Output ===")

# Clean up any existing test user
test_email = "debug_test@example.com"
CustomUser.objects.filter(email=test_email).delete()

# Get reference data
country = Country.objects.first()
currency = PreferredCurrency.objects.first()
category = MerchantCategory.objects.first()

print(f"Using country: {country} (ID: {country.id})")
print(f"Using currency: {currency} (ID: {currency.id})")
print(f"Using category: {category} (ID: {category.id})")

# Prepare test data
test_data = {
    'first_name': 'Debug',
    'last_name': 'Test',
    'email': test_email,
    'password': 'debugtest123',
    'confirm_password': 'debugtest123',
    'phone': '+1234567890',
    'country': str(country.id),
    'currency': str(currency.id),
    'business_name': 'Debug Business',
    'merchant_category': str(category.id),
}

print(f"Test data prepared for: {test_email}")

# Create client and send request
client = Client()
try:
    print("Sending POST request...")
    response = client.post(reverse('auth:register_page'), data=test_data, follow=True)
    
    print(f"Response status: {response.status_code}")
    print(f"Final URL: {response.request.get('PATH_INFO', 'Unknown')}")
    
    # Check if user was created
    if CustomUser.objects.filter(email=test_email).exists():
        user = CustomUser.objects.get(email=test_email)
        print(f"SUCCESS: User created - {user}")
        
        # Check for merchant
        try:
            merchant = user.merchant_account
            print(f"Merchant: {merchant}")
        except:
            print("No merchant account created")
            
        # Check for OTP
        from authentication.models import EmailOTP
        otps = EmailOTP.objects.filter(user=user)
        print(f"OTPs: {otps.count()}")
        if otps.exists():
            latest = otps.latest('created_at')
            print(f"Latest OTP: {latest.otp_code}")
    else:
        print("FAILED: User was not created")
    
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()

print("=== Test Complete ===")
