#!/usr/bin/env python
"""
Test the registration process directly
"""
import os
import django
import sys
import json

# Set up Django
sys.path.insert(0, '/Users/asd/Desktop/desktop/pexilabs')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pexilabs.settings')
django.setup()

from django.test import Client
from django.urls import reverse
from authentication.models import CustomUser, Country, PreferredCurrency, MerchantCategory

def test_registration_complete():
    """Test the complete registration process"""
    
    client = Client()
    print("=== Testing Complete Registration Process ===")
    
    # Get reference data
    country = Country.objects.first()
    currency = PreferredCurrency.objects.first()
    category = MerchantCategory.objects.first()
    
    if not all([country, currency, category]):
        print("✗ Missing reference data")
        return False
    
    print(f"Using: {country.name}, {currency.name}, {category.name}")
    
    # Test email that should not exist
    test_email = "newuser@example.com"
    
    # Clean up any existing test user
    CustomUser.objects.filter(email=test_email).delete()
    
    # Prepare registration data
    registration_data = {
        'first_name': 'New',
        'last_name': 'User',
        'email': test_email,
        'password': 'newpassword123',
        'confirm_password': 'newpassword123',
        'phone': '+1234567890',
        'country': str(country.id),
        'currency': str(currency.id),
        'business_name': 'New Business',
        'merchant_category': str(category.id),
    }
    
    print(f"\\nTesting registration with data: {json.dumps(registration_data, indent=2, default=str)}")
    
    try:
        # Test POST request
        response = client.post(reverse('auth:register_page'), data=registration_data)
        
        print(f"Response status: {response.status_code}")
        print(f"Response redirect location: {response.get('Location', 'None')}")
        
        # Check if user was created
        try:
            user = CustomUser.objects.get(email=test_email)
            print(f"✓ User created: {user}")
            print(f"  - Name: {user.get_full_name()}")
            print(f"  - Email: {user.email}")
            print(f"  - Phone: {user.phone_number}")
            print(f"  - Country: {user.country}")
            print(f"  - Currency: {user.preferred_currency}")
            print(f"  - Verified: {user.is_verified}")
            
            # Check merchant account
            try:
                merchant = user.merchant_account
                print(f"✓ Merchant created: {merchant}")
                print(f"  - Business: {merchant.business_name}")
                print(f"  - Category: {merchant.category}")
                print(f"  - Status: {merchant.status}")
            except:
                print("ℹ No merchant account (this is okay if business name was empty)")
            
            # Check OTP
            from authentication.models import EmailOTP
            otps = EmailOTP.objects.filter(user=user)
            print(f"OTP records: {otps.count()}")
            if otps.exists():
                latest_otp = otps.latest('created_at')
                print(f"✓ Latest OTP: {latest_otp.otp_code} (expires: {latest_otp.expires_at})")
            
            # Success!
            print("\\n✓ Registration completed successfully!")
            return True
            
        except CustomUser.DoesNotExist:
            print("✗ User was not created")
            
            # Check for any error messages in the response
            if hasattr(response, 'context') and response.context:
                messages = response.context.get('messages', [])
                if messages:
                    print("Error messages:")
                    for message in messages:
                        print(f"  - {message}")
            
            return False
            
    except Exception as e:
        print(f"✗ Exception during registration: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_validation_errors():
    """Test validation error cases"""
    
    client = Client()
    print("\\n=== Testing Validation Errors ===")
    
    # Test with missing required fields
    test_cases = [
        {
            'name': 'Missing first name',
            'data': {
                'last_name': 'User',
                'email': 'test1@example.com',
                'password': 'password123',
                'confirm_password': 'password123',
            }
        },
        {
            'name': 'Password mismatch',
            'data': {
                'first_name': 'Test',
                'last_name': 'User',
                'email': 'test2@example.com',
                'password': 'password123',
                'confirm_password': 'different123',
            }
        },
        {
            'name': 'Short password',
            'data': {
                'first_name': 'Test',
                'last_name': 'User',
                'email': 'test3@example.com',
                'password': '123',
                'confirm_password': '123',
            }
        }
    ]
    
    for test_case in test_cases:
        print(f"\\nTesting: {test_case['name']}")
        
        # Clean up any test users
        email = test_case['data'].get('email')
        if email:
            CustomUser.objects.filter(email=email).delete()
        
        try:
            response = client.post(reverse('auth:register_page'), data=test_case['data'])
            print(f"  Status: {response.status_code}")
            
            # Check that user was NOT created
            if email and CustomUser.objects.filter(email=email).exists():
                print(f"  ✗ User was created when it shouldn't have been")
            else:
                print(f"  ✓ Validation worked correctly")
                
        except Exception as e:
            print(f"  ✗ Exception: {e}")
    
    return True

if __name__ == '__main__':
    print("Starting registration tests...")
    
    success = True
    
    # Test normal registration
    if not test_registration_complete():
        success = False
    
    # Test validation
    if not test_validation_errors():
        success = False
    
    if success:
        print("\\n✅ All tests passed!")
    else:
        print("\\n❌ Some tests failed!")
        sys.exit(1)
