#!/usr/bin/env python
"""
Simple test to check registration flow
"""
import os
import sys
import django

# Add the project directory to Python path  
sys.path.append('/Users/asd/Desktop/desktop/pexilabs')

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pexilabs.settings')
django.setup()

from authentication.models import CustomUser, MerchantCategory

print("=== Testing Registration Process ===")

# Clear test user
CustomUser.objects.filter(email='simple@example.com').delete()

# Get a valid category
category = MerchantCategory.objects.first()
print(f"Using category: {category.id} - {category.name}")

from django.test import Client
client = Client()

print("Posting registration...")
response = client.post('/auth/register/', {
    'first_name': 'Simple',
    'last_name': 'Test',
    'email': 'simple@example.com',
    'password': 'testpassword123',
    'confirm_password': 'testpassword123',
    'phone': '+1234567890',
    'business_name': 'Test Business',
    'merchant_category': str(category.id)
})

print(f"Response status: {response.status_code}")

if response.status_code == 302:
    location = response.get('Location', 'No location')
    print(f"Redirect to: {location}")
    
    # Check if user was created
    try:
        user = CustomUser.objects.get(email='simple@example.com')
        print(f"✓ User created: {user.id}")
        print(f"User verified: {user.is_verified}")
        
        # Check OTP
        from authentication.models import EmailOTP
        otp_count = EmailOTP.objects.filter(user=user).count()
        print(f"OTP records: {otp_count}")
        
        if '/auth/verify/' in location:
            print("✓ Correctly redirected to OTP verification")
        else:
            print("✗ Not redirected to OTP verification")
            
    except CustomUser.DoesNotExist:
        print("✗ User not created")
else:
    print(f"✗ Unexpected response status: {response.status_code}")

print("\nDone!")
