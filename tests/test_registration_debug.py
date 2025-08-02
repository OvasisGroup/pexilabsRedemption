#!/usr/bin/env python
"""
Test script to debug registration issues
"""
import os
import django
import sys

# Add the project root to the Python path
sys.path.insert(0, '/Users/asd/Desktop/desktop/pexilabs')

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pexilabs.settings')
django.setup()

from django.test import Client
from django.urls import reverse
from authentication.models import CustomUser, Country, PreferredCurrency, MerchantCategory

def test_registration():
    """Test the registration process step by step"""
    
    # Create a test client
    client = Client()
    
    print("=== Testing Registration Process ===")
    
    # Step 1: Create required reference data
    print("\n1. Creating reference data...")
    
    # Create a country if it doesn't exist
    country, created = Country.objects.get_or_create(
        name="United States",
        defaults={
            'code': 'US',
            'phone_code': '+1'
        }
    )
    if created:
        print(f"   Created country: {country}")
    else:
        print(f"   Using existing country: {country}")
    
    # Create a currency if it doesn't exist
    currency, created = PreferredCurrency.objects.get_or_create(
        name="US Dollar",
        defaults={
            'code': 'USD',
            'symbol': '$',
            'is_active': True
        }
    )
    if created:
        print(f"   Created currency: {currency}")
    else:
        print(f"   Using existing currency: {currency}")
    
    # Create a merchant category if it doesn't exist
    category, created = MerchantCategory.objects.get_or_create(
        name="Technology",
        defaults={
            'code': 'TECH',
            'description': 'Technology and software companies',
            'is_active': True
        }
    )
    if created:
        print(f"   Created merchant category: {category}")
    else:
        print(f"   Using existing merchant category: {category}")
    
    # Step 2: Test GET request to registration page
    print("\n2. Testing GET request to registration page...")
    try:
        response = client.get(reverse('auth:register_page'))
        print(f"   Status code: {response.status_code}")
        if response.status_code == 200:
            print("   ✓ Registration page loads successfully")
        else:
            print(f"   ✗ Registration page failed to load: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ✗ Error loading registration page: {e}")
        return False
    
    # Step 3: Test POST request with valid data
    print("\n3. Testing POST request with valid data...")
    
    # Clean up any existing test user
    test_email = "test@example.com"
    CustomUser.objects.filter(email=test_email).delete()
    
    registration_data = {
        'first_name': 'Test',
        'last_name': 'User',
        'email': test_email,
        'password': 'testpassword123',
        'confirm_password': 'testpassword123',
        'phone': '+1234567890',
        'country': str(country.id),
        'currency': str(currency.id),
        'business_name': 'Test Business',
        'merchant_category': str(category.id),
    }
    
    try:
        response = client.post(reverse('auth:register_page'), data=registration_data)
        print(f"   Status code: {response.status_code}")
        
        # Check if user was created
        try:
            user = CustomUser.objects.get(email=test_email)
            print(f"   ✓ User created successfully: {user}")
            
            # Check if merchant was created
            if hasattr(user, 'merchant_account'):
                print(f"   ✓ Merchant account created: {user.merchant_account}")
            else:
                print("   ℹ No merchant account created (this is okay)")
            
            # Check if OTP was created
            from authentication.models import EmailOTP
            otp_count = EmailOTP.objects.filter(user=user).count()
            print(f"   OTP records created: {otp_count}")
            
            if otp_count > 0:
                latest_otp = EmailOTP.objects.filter(user=user).latest('created_at')
                print(f"   ✓ Latest OTP: {latest_otp.otp_code} (expires: {latest_otp.expires_at})")
            
            # Check the redirect
            if response.status_code == 302:
                print(f"   Redirect location: {response.get('Location', 'Not specified')}")
                print("   ✓ Registration appears successful")
                return True
            else:
                print(f"   ✗ Expected redirect (302) but got {response.status_code}")
                return False
                
        except CustomUser.DoesNotExist:
            print("   ✗ User was not created")
            return False
            
    except Exception as e:
        print(f"   ✗ Error during registration: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

def test_required_models():
    """Test if all required models and data exist"""
    print("\n=== Testing Required Models ===")
    
    # Check if basic models are accessible
    try:
        user_count = CustomUser.objects.count()
        print(f"CustomUser model: ✓ ({user_count} users)")
    except Exception as e:
        print(f"CustomUser model: ✗ Error: {e}")
        return False
    
    try:
        country_count = Country.objects.count()
        print(f"Country model: ✓ ({country_count} countries)")
    except Exception as e:
        print(f"Country model: ✗ Error: {e}")
        return False
    
    try:
        currency_count = PreferredCurrency.objects.count()
        print(f"PreferredCurrency model: ✓ ({currency_count} currencies)")
    except Exception as e:
        print(f"PreferredCurrency model: ✗ Error: {e}")
        return False
    
    try:
        category_count = MerchantCategory.objects.count()
        print(f"MerchantCategory model: ✓ ({category_count} categories)")
    except Exception as e:
        print(f"MerchantCategory model: ✗ Error: {e}")
        return False
    
    try:
        from authentication.models import EmailOTP
        otp_count = EmailOTP.objects.count()
        print(f"EmailOTP model: ✓ ({otp_count} OTP records)")
    except Exception as e:
        print(f"EmailOTP model: ✗ Error: {e}")
        return False
    
    return True

if __name__ == '__main__':
    print("Starting registration debug test...")
    
    # Test required models first
    if not test_required_models():
        print("\n✗ Required models test failed. Cannot continue.")
        sys.exit(1)
    
    # Test registration process
    if test_registration():
        print("\n✓ Registration test completed successfully!")
    else:
        print("\n✗ Registration test failed!")
        sys.exit(1)
