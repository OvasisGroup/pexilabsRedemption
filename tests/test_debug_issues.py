#!/usr/bin/env python
"""
Debug script to test OTP and merchant dashboard issues
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
from django.contrib.auth import get_user_model
from authentication.models import CustomUser, Merchant, MerchantCategory

def test_registration_and_otp():
    """Test registration and OTP flow"""
    print("=== Testing Registration and OTP Flow ===")
    
    # Clear any existing test user
    CustomUser.objects.filter(email='debug@example.com').delete()
    
    client = Client()
    
    # Test registration
    response = client.post('/auth/register/', {
        'first_name': 'Debug',
        'last_name': 'User',
        'email': 'debug@example.com',
        'password': 'testpassword123',
        'confirm_password': 'testpassword123',
        'phone': '+1234567890',
        'business_name': 'Debug Business',
        'merchant_category': '57bf9724-a2dd-4c2e-b260-b1e284bfda77'  # General Business
    })
    
    print(f"Registration response status: {response.status_code}")
    print(f"Registration response type: {type(response)}")
    
    if hasattr(response, 'url'):
        print(f"Registration redirect URL: {response.url}")
    elif response.status_code == 302:
        print(f"Registration redirect location: {response.get('Location', 'No Location header')}")
    
    # Check if user was created
    try:
        user = CustomUser.objects.get(email='debug@example.com')
        print(f"✓ User created: {user.id} - {user.email}")
        print(f"  User verified: {user.is_verified}")
        
        # Check if merchant was created
        try:
            merchant = Merchant.objects.get(user=user)
            print(f"✓ Merchant created: {merchant.business_name}")
        except Merchant.DoesNotExist:
            print("✗ No merchant account created")
        
        # Test OTP verification page access
        print(f"\nTesting OTP page access...")
        otp_response = client.get(f'/auth/verify/{user.id}/')
        print(f"OTP page response status: {otp_response.status_code}")
        
        # Test OTP verification with mock code
        print(f"\nTesting OTP verification...")
        
        # Get OTP from database for testing
        from authentication.models import EmailOTP
        try:
            otp_instance = EmailOTP.objects.filter(user=user).order_by('-created_at').first()
            if otp_instance:
                print(f"Found OTP: {otp_instance.otp_code}")
                
                # Test OTP verification
                verify_response = client.post(f'/auth/verify/{user.id}/', {
                    'otp_code': otp_instance.otp_code
                })
                print(f"OTP verification response status: {verify_response.status_code}")
                if hasattr(verify_response, 'url'):
                    print(f"OTP verification redirect URL: {verify_response.url}")
                elif verify_response.status_code == 302:
                    print(f"OTP verification redirect: {verify_response.get('Location', 'No Location')}")
                
                # Refresh user to check verification status
                user.refresh_from_db()
                print(f"User verified after OTP: {user.is_verified}")
                
            else:
                print("No OTP found in database")
                
        except Exception as e:
            print(f"Error testing OTP: {e}")
            
    except CustomUser.DoesNotExist:
        print("✗ User was not created")

def test_merchant_dashboard():
    """Test merchant dashboard for FieldError"""
    print("\n=== Testing Merchant Dashboard ===")
    
    # Get a user with merchant account
    try:
        user = CustomUser.objects.filter(merchant_account__isnull=False).first()
        if not user:
            print("No users with merchant accounts found")
            return
            
        print(f"Testing with user: {user.email}")
        
        client = Client()
        client.force_login(user)
        
        # Test merchant dashboard access
        response = client.get('/dashboard/merchant/')
        print(f"Merchant dashboard response status: {response.status_code}")
        
        if response.status_code == 500:
            print("✗ Server error accessing merchant dashboard")
        elif response.status_code == 200:
            print("✓ Merchant dashboard loaded successfully")
        else:
            print(f"Unexpected response status: {response.status_code}")
            
    except Exception as e:
        print(f"Error testing merchant dashboard: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_registration_and_otp()
    test_merchant_dashboard()
