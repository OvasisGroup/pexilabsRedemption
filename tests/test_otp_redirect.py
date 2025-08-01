#!/usr/bin/env python
"""
Simple test to debug OTP verification redirect
"""
import os
import sys
import django

# Add the project directory to Python path  
sys.path.append('/Users/asd/Desktop/desktop/pexilabs')

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pexilabs.settings')
django.setup()

from django.test import Client
from authentication.models import CustomUser, EmailOTP

# Create a fresh test user
CustomUser.objects.filter(email='redirect_test@example.com').delete()

user = CustomUser.objects.create_user(
    email='redirect_test@example.com',
    password='testpassword123',
    first_name='Redirect',
    last_name='Test'
)
user.is_verified = False
user.save()

# Create OTP
otp_instance = EmailOTP.generate_otp(user, purpose='registration', validity_minutes=15)

print(f"Created user: {user.id} - {user.email}")
print(f"User verified: {user.is_verified}")
print(f"OTP code: {otp_instance.otp_code}")

client = Client()

# Test OTP verification 
print(f"\nTesting OTP verification...")
verify_response = client.post(f'/auth/verify/{user.id}/', {
    'otp_code': otp_instance.otp_code
}, follow=False)  # Don't follow redirects

print(f"Response status: {verify_response.status_code}")
print(f"Response type: {type(verify_response)}")

if verify_response.status_code == 302:
    location = verify_response.get('Location', 'No Location header')
    print(f"Redirect Location header: {location}")
    
    # Check user status
    user.refresh_from_db()
    print(f"User verified after POST: {user.is_verified}")
    
    # Check OTP status
    otp_instance.refresh_from_db()
    print(f"OTP used: {otp_instance.is_used}")

print("\nDone!")
