#!/usr/bin/env python
"""
Test OTP verification and merchant dashboard fixes
"""
import os
import django
import sys

sys.path.append('/Users/asd/Desktop/desktop/pexilabs')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pexilabs.settings')
django.setup()

from django.test import Client
from django.urls import reverse
from authentication.models import CustomUser, EmailOTP
from django.contrib.auth import authenticate
import json

def test_otp_verification():
    """Test OTP verification process"""
    print("=== Testing OTP Verification ===")
    
    # Find a user with an OTP
    users_with_otp = CustomUser.objects.filter(
        is_verified=False,
        email_otps__is_used=False
    ).distinct()
    
    if not users_with_otp.exists():
        print("No unverified users with OTP found, creating one...")
        # Use an existing test user or create one
        test_email = "otp_test_user@example.com"
        CustomUser.objects.filter(email=test_email).delete()
        
        user = CustomUser.objects.create_user(
            email=test_email,
            first_name="OTP",
            last_name="Test",
            password="otptest123"
        )
        
        # Generate OTP
        otp_instance = EmailOTP.generate_otp(user, purpose='registration')
        print(f"Created test user with OTP: {otp_instance.otp_code}")
    else:
        user = users_with_otp.first()
        otp_instance = EmailOTP.objects.filter(
            user=user, 
            is_used=False
        ).order_by('-created_at').first()
        print(f"Using existing user: {user.email}")
        print(f"OTP code: {otp_instance.otp_code}")
    
    # Test OTP verification page loads
    client = Client()
    verify_url = f"/auth/verify/{user.id}/"
    
    # Test GET request
    response = client.get(verify_url)
    print(f"OTP page status: {response.status_code}")
    
    if response.status_code == 200:
        print("✅ OTP verification page loads correctly")
        
        # Test POST with correct OTP
        response = client.post(verify_url, {
            'otp_code': otp_instance.otp_code
        })
        
        print(f"OTP verification response: {response.status_code}")
        
        if response.status_code == 302:
            redirect_url = response.get('Location', '')
            print(f"Redirect URL: {redirect_url}")
            
            # Check if user is now verified
            user.refresh_from_db()
            if user.is_verified:
                print("✅ OTP verification successful - user is now verified")
                return True
            else:
                print("❌ OTP verification failed - user still unverified")
                return False
        else:
            print(f"❌ Expected redirect but got {response.status_code}")
            return False
    else:
        print(f"❌ OTP page failed to load: {response.status_code}")
        return False

def test_merchant_dashboard():
    """Test merchant dashboard access"""
    print("\n=== Testing Merchant Dashboard ===")
    
    # Find a user with merchant account
    merchants = CustomUser.objects.filter(
        merchant_account__isnull=False,
        is_verified=True
    )
    
    if not merchants.exists():
        print("No verified merchants found, skipping dashboard test")
        return True
    
    merchant_user = merchants.first()
    print(f"Testing with merchant: {merchant_user.email}")
    
    # Login as merchant
    client = Client()
    client.force_login(merchant_user)
    
    # Access merchant dashboard
    try:
        response = client.get('/dashboard/merchant/')
        print(f"Merchant dashboard status: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Merchant dashboard loads successfully")
            return True
        else:
            print(f"❌ Merchant dashboard failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Merchant dashboard error: {e}")
        return False

def test_resend_otp():
    """Test resend OTP functionality"""
    print("\n=== Testing Resend OTP ===")
    
    # Find unverified user
    user = CustomUser.objects.filter(is_verified=False).first()
    
    if not user:
        print("No unverified users found, skipping resend test")
        return True
    
    print(f"Testing resend OTP for: {user.email}")
    
    client = Client()
    resend_url = f"/auth/resend-otp/{user.id}/"
    
    try:
        response = client.post(resend_url)
        print(f"Resend OTP status: {response.status_code}")
        
        if response.status_code == 200:
            # Parse JSON response
            data = json.loads(response.content)
            if data.get('success'):
                print("✅ Resend OTP successful")
                return True
            else:
                print(f"❌ Resend OTP failed: {data.get('message', 'Unknown error')}")
                return False
        else:
            print(f"❌ Unexpected status code: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Resend OTP error: {e}")
        return False

def main():
    print("Testing OTP and Dashboard fixes...\n")
    
    success = True
    
    # Test OTP verification
    if not test_otp_verification():
        success = False
    
    # Test merchant dashboard
    if not test_merchant_dashboard():
        success = False
    
    # Test resend OTP
    if not test_resend_otp():
        success = False
    
    if success:
        print("\n🎉 All tests passed!")
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)

if __name__ == '__main__':
    main()
