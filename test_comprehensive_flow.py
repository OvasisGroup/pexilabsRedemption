#!/usr/bin/env python
"""
Comprehensive test of registration and OTP verification URLs
"""
import os
import django
import sys

# Set up Django
sys.path.append('/Users/asd/Desktop/desktop/pexilabs')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pexilabs.settings')
django.setup()

from django.urls import reverse
from django.test import Client
from authentication.models import CustomUser, Country, PreferredCurrency, MerchantCategory
import uuid

def test_url_patterns():
    """Test that URL patterns work with UUIDs"""
    print("=== Testing URL Patterns ===")
    
    # Test with fake UUID
    test_uuid = uuid.uuid4()
    
    try:
        verify_url = reverse('auth:verify_otp', kwargs={'user_id': test_uuid})
        print(f"✅ verify_otp URL: {verify_url}")
    except Exception as e:
        print(f"❌ verify_otp URL failed: {e}")
        return False
    
    try:
        resend_url = reverse('auth:resend_otp', kwargs={'user_id': test_uuid})
        print(f"✅ resend_otp URL: {resend_url}")
    except Exception as e:
        print(f"❌ resend_otp URL failed: {e}")
        return False
    
    return True

def test_registration_and_redirect():
    """Test complete registration flow"""
    print("\n=== Testing Registration Flow ===")
    
    # Clean up test user
    test_email = "comprehensive_test@example.com"
    CustomUser.objects.filter(email=test_email).delete()
    
    # Get reference data
    try:
        country = Country.objects.first()
        currency = PreferredCurrency.objects.first()
        category = MerchantCategory.objects.first()
        
        if not all([country, currency, category]):
            print("❌ Missing reference data")
            return False
            
        print(f"Using: {country.name}, {currency.name}, {category.name}")
        
    except Exception as e:
        print(f"❌ Error getting reference data: {e}")
        return False
    
    # Registration data
    data = {
        'first_name': 'Comprehensive',
        'last_name': 'Test',
        'email': test_email,
        'password': 'comprehensive123',
        'confirm_password': 'comprehensive123',
        'phone': '+1555123456',
        'country': str(country.id),
        'currency': str(currency.id),
        'business_name': 'Comprehensive Test Business',
        'merchant_category': str(category.id),
    }
    
    # Submit registration
    client = Client()
    try:
        response = client.post('/auth/register/', data)
        print(f"Registration response status: {response.status_code}")
        
        if response.status_code == 302:
            redirect_location = response.get('Location', '')
            print(f"Redirect location: {redirect_location}")
            
            # Check if user was created
            if CustomUser.objects.filter(email=test_email).exists():
                user = CustomUser.objects.get(email=test_email)
                print(f"✅ User created: {user}")
                
                # Verify redirect URL contains user ID
                if str(user.id) in redirect_location:
                    print("✅ Correct redirect URL with UUID")
                else:
                    print(f"❌ Incorrect redirect URL. Expected UUID {user.id} in {redirect_location}")
                    return False
                
                # Test accessing the verification page
                verify_url = f"/auth/verify/{user.id}/"
                verify_response = client.get(verify_url)
                print(f"Verification page status: {verify_response.status_code}")
                
                if verify_response.status_code == 200:
                    print("✅ Verification page loads successfully")
                    return True
                else:
                    print(f"❌ Verification page failed: {verify_response.status_code}")
                    return False
            else:
                print("❌ User was not created")
                return False
        else:
            print(f"❌ Expected redirect (302) but got {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Registration failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("Starting comprehensive URL and registration tests...\n")
    
    success = True
    
    # Test URL patterns
    if not test_url_patterns():
        success = False
    
    # Test registration flow
    if not test_registration_and_redirect():
        success = False
    
    if success:
        print("\n🎉 All tests passed! Registration -> OTP verification flow is working correctly!")
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)

if __name__ == '__main__':
    main()
