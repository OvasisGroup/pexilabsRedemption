#!/usr/bin/env python
"""
Test OTP verification and dashboard redirect flow
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

def test_otp_verification():
    """Test OTP verification and redirect"""
    print("=== Testing OTP Verification and Redirect ===")
    
    # Find an unverified user with OTP
    unverified_user = CustomUser.objects.filter(is_verified=False).first()
    
    if not unverified_user:
        print("No unverified users found. Creating one...")
        # Create a test user
        unverified_user = CustomUser.objects.create_user(
            email='otp_test@example.com',
            password='testpassword123',
            first_name='OTP',
            last_name='Test'
        )
        unverified_user.is_verified = False
        unverified_user.save()
        
        # Create OTP
        otp_instance = EmailOTP.generate_otp(unverified_user, purpose='registration', validity_minutes=15)
    else:
        # Get or create OTP for existing user
        otp_instance = EmailOTP.objects.filter(
            user=unverified_user, 
            is_used=False
        ).order_by('-created_at').first()
        
        if not otp_instance:
            otp_instance = EmailOTP.generate_otp(unverified_user, purpose='registration', validity_minutes=15)
    
    print(f"Testing with user: {unverified_user.email}")
    print(f"User ID: {unverified_user.id}")
    print(f"User verified: {unverified_user.is_verified}")
    print(f"OTP code: {otp_instance.otp_code}")
    
    client = Client()
    
    # Test OTP verification page access
    print(f"\n1. Testing OTP page access...")
    otp_page_response = client.get(f'/auth/verify/{unverified_user.id}/')
    print(f"   OTP page status: {otp_page_response.status_code}")
    
    if otp_page_response.status_code != 200:
        print(f"   ✗ OTP page not accessible")
        return
    
    # Test OTP verification 
    print(f"\n2. Testing OTP verification...")
    verify_response = client.post(f'/auth/verify/{unverified_user.id}/', {
        'otp_code': otp_instance.otp_code
    })
    
    print(f"   Verification response status: {verify_response.status_code}")
    
    if verify_response.status_code == 302:
        location = verify_response.get('Location', 'No location')
        print(f"   ✓ Redirected to: {location}")
        
        # Check if user is now verified
        unverified_user.refresh_from_db()
        print(f"   User verified after OTP: {unverified_user.is_verified}")
        
        if '/dashboard/' in location:
            print("   ✓ Correctly redirected to dashboard")
        else:
            print("   ✗ Not redirected to dashboard")
            
        # Test following the redirect
        print(f"\n3. Testing dashboard access...")
        dashboard_response = client.get(location)
        print(f"   Dashboard access status: {dashboard_response.status_code}")
        
        if dashboard_response.status_code == 200:
            print("   ✓ Dashboard loaded successfully")
        elif dashboard_response.status_code == 302:
            final_location = dashboard_response.get('Location', 'No location')
            print(f"   Dashboard redirected to: {final_location}")
            
            # Follow final redirect
            final_response = client.get(final_location)
            print(f"   Final page status: {final_response.status_code}")
            if final_response.status_code == 200:
                print("   ✓ Final dashboard page loaded")
        else:
            print(f"   ✗ Dashboard error: {dashboard_response.status_code}")
    else:
        print(f"   ✗ Verification failed with status: {verify_response.status_code}")

def test_merchant_dashboard():
    """Test merchant dashboard specifically"""
    print("\n=== Testing Merchant Dashboard ===")
    
    # Find a verified user with merchant account
    merchant_user = CustomUser.objects.filter(
        is_verified=True,
        merchant_account__isnull=False
    ).first()
    
    if not merchant_user:
        print("No merchant users found")
        return
    
    print(f"Testing with merchant user: {merchant_user.email}")
    
    client = Client()
    client.force_login(merchant_user)
    
    # Test merchant dashboard access
    response = client.get('/dashboard/merchant/')
    print(f"Merchant dashboard status: {response.status_code}")
    
    if response.status_code == 200:
        print("✓ Merchant dashboard loaded successfully")
    elif response.status_code == 500:
        print("✗ Server error in merchant dashboard")
    else:
        print(f"Unexpected status: {response.status_code}")
        if response.status_code == 302:
            location = response.get('Location', 'No location')
            print(f"Redirected to: {location}")

if __name__ == '__main__':
    test_otp_verification()
    test_merchant_dashboard()
