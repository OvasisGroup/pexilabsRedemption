#!/usr/bin/env python
import os
import django
import sys

sys.path.insert(0, '/Users/asd/Desktop/desktop/pexilabs')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pexilabs.settings')
django.setup()

from authentication.models import CustomUser, EmailOTP
from authentication.utils import send_otp_email

print("=== Testing OTP and Email Functionality ===")

# Create a test user
test_email = "otp_test@example.com"
CustomUser.objects.filter(email=test_email).delete()

try:
    user = CustomUser.objects.create_user(
        email=test_email,
        first_name="Test",
        last_name="User",
        password="testpass123"
    )
    print(f"✓ User created: {user}")
    
    # Test OTP generation
    try:
        otp_instance = EmailOTP.generate_otp(user, purpose='registration', validity_minutes=15)
        print(f"✓ OTP generated: {otp_instance.otp_code}")
        print(f"  - Expires at: {otp_instance.expires_at}")
        print(f"  - Purpose: {otp_instance.purpose}")
        
        # Test email sending (this might fail but let's see the error)
        try:
            result = send_otp_email(user, otp_instance, purpose='registration')
            print(f"✓ Email function returned: {result}")
        except Exception as email_error:
            print(f"✗ Email sending failed: {email_error}")
            import traceback
            traceback.print_exc()
            
    except Exception as otp_error:
        print(f"✗ OTP generation failed: {otp_error}")
        import traceback
        traceback.print_exc()
        
except Exception as user_error:
    print(f"✗ User creation failed: {user_error}")
    import traceback
    traceback.print_exc()

print("=== Test Complete ===")
