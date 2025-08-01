#!/usr/bin/env python
"""
Test OTP verification by manually calling the view
"""
import os
import sys
import django

# Add the project directory to Python path  
sys.path.append('/Users/asd/Desktop/desktop/pexilabs')

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pexilabs.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.auth import get_user_model
from django.contrib.messages.storage.fallback import FallbackStorage
from authentication.models import CustomUser, EmailOTP
from authentication.auth_views import verify_otp

# Create a fresh test user
CustomUser.objects.filter(email='manual_test@example.com').delete()

user = CustomUser.objects.create_user(
    email='manual_test@example.com',
    password='testpassword123',
    first_name='Manual',
    last_name='Test'
)
user.is_verified = False
user.save()

# Create OTP
otp_instance = EmailOTP.generate_otp(user, purpose='registration', validity_minutes=15)

print(f"Created user: {user.id} - {user.email}")
print(f"OTP code: {otp_instance.otp_code}")

# Test with RequestFactory (more direct)
factory = RequestFactory()
request = factory.post(f'/auth/verify/{user.id}/', {
    'otp_code': otp_instance.otp_code
})

# Add required attributes for Django
request.user = user  # Not logged in yet
request.session = {}

# Add messages framework
setattr(request, '_messages', FallbackStorage(request))

print(f"\nCalling verify_otp view directly...")

try:
    response = verify_otp(request, user.id)
    print(f"Response status: {response.status_code}")
    print(f"Response type: {type(response)}")
    
    if hasattr(response, 'url'):
        print(f"Redirect URL: {response.url}")
    elif hasattr(response, 'get') and response.get('Location'):
        print(f"Location header: {response.get('Location')}")
    
    # Check user status
    user.refresh_from_db()
    print(f"User verified: {user.is_verified}")
    
    # Check OTP status
    otp_instance.refresh_from_db()
    print(f"OTP used: {otp_instance.is_used}")
    
except Exception as e:
    import traceback
    print(f"Error calling view: {e}")
    print(f"Traceback: {traceback.format_exc()}")

print("\nDone!")
