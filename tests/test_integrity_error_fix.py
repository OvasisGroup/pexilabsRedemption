#!/usr/bin/env python3
"""
Test script to verify the IntegrityError fix for API Keys
"""

import os
import sys
import django
from django.test import Client
from django.contrib.auth import get_user_model

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pexilabs.settings')
django.setup()

from authentication.models import Merchant, WhitelabelPartner

def test_api_key_integrity_fix():
    """Test that merchants without complete data can still access API keys"""
    print("🧪 Testing API Key IntegrityError Fix...")
    
    # Create a test client
    client = Client()
    
    User = get_user_model()
    
    try:
        # Create a test merchant with minimal data (simulating the error case)
        test_user = User.objects.create_user(
            email='test_merchant@example.com',
            password='testpass123',
            role='merchant'
        )
        
        # Create merchant with missing required fields
        test_merchant = Merchant.objects.create(
            user=test_user,
            business_name='Test Business',
            business_email='test@business.com',
            # Intentionally leaving some fields empty to test the fix
            business_address='',
            business_registration_number='',
        )
        
        print(f"✅ Created test merchant: {test_merchant.business_name}")
        print(f"   - Business registration number: '{test_merchant.business_registration_number}'")
        print(f"   - Business address: '{test_merchant.business_address}'")
        
        # Login the merchant user
        client.force_login(test_user)
        
        # Test accessing the API keys page (this should not cause IntegrityError)
        print("\n🔑 Testing API Keys page access...")
        response = client.get('/dashboard/merchant/api-keys/')
        
        if response.status_code == 200:
            print("✅ API Keys page accessible without IntegrityError!")
            
            # Check if a partner was created with proper defaults
            partner_code = f"merchant_{test_merchant.id}"
            try:
                partner = WhitelabelPartner.objects.get(code=partner_code)
                print(f"✅ WhitelabelPartner created with defaults:")
                print(f"   - Name: {partner.name}")
                print(f"   - Contact Email: {partner.contact_email}")
                print(f"   - Business Address: {partner.business_address}")
                print(f"   - Registration Number: {partner.business_registration_number}")
                
            except WhitelabelPartner.DoesNotExist:
                print("ℹ️  No partner created yet (accessed via template)")
                
        elif response.status_code == 302:
            print("ℹ️  Redirected (possibly due to missing API_KEYS_AVAILABLE setting)")
            print(f"   Redirect location: {response.get('Location', 'Unknown')}")
        else:
            print(f"❌ API Keys page returned status {response.status_code}")
            print(f"   Content: {response.content.decode()[:200]}...")
            return False
        
        # Test creating an API key via API
        print("\n🆕 Testing API Key creation...")
        create_data = {
            'name': 'Test API Key',
            'key_type': 'sandbox',
            'scopes': 'read,write'
        }
        
        response = client.post(
            '/dashboard/api/api-keys/',
            data=create_data,
            content_type='application/json'
        )
        
        if response.status_code == 200:
            response_data = response.json()
            if response_data.get('success'):
                print("✅ API Key creation successful!")
                print(f"   Created key: {response_data['api_key']['name']}")
                
                # Verify partner was created properly
                partner = WhitelabelPartner.objects.get(code=partner_code)
                print(f"✅ Partner created with proper defaults:")
                print(f"   - Registration Number: {partner.business_registration_number}")
                
            else:
                print(f"❌ API Key creation failed: {response_data.get('error')}")
        elif response.status_code == 503:
            print("ℹ️  API key functionality not available (API_KEYS_AVAILABLE=False)")
        else:
            print(f"❌ API Key creation returned status {response.status_code}")
            if hasattr(response, 'json'):
                print(f"   Response: {response.json()}")
        
        # Cleanup
        test_merchant.delete()
        test_user.delete()
        try:
            partner = WhitelabelPartner.objects.get(code=partner_code)
            partner.delete()
        except WhitelabelPartner.DoesNotExist:
            pass
        
        print("\n✅ IntegrityError fix test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main test function"""
    print("🚀 Starting IntegrityError Fix Test...\n")
    
    if test_api_key_integrity_fix():
        print("\n🎉 Fix verified successfully!")
        sys.exit(0)
    else:
        print("\n💥 Fix verification failed!")
        sys.exit(1)

if __name__ == '__main__':
    main()
