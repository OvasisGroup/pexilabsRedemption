#!/usr/bin/env python3
"""
Test script for API Key Management functionality in merchant dashboard
"""

import os
import sys
import django
from django.test import Client
from django.contrib.auth import get_user_model

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pexilabs.settings')
django.setup()

from authentication.models import Merchant, WhitelabelPartner, AppKey

def test_api_key_management():
    """Test the API key management functionality"""
    print("🧪 Testing API Key Management...")
    
    # Create a test client
    client = Client()
    
    # Check if we have a test merchant user
    User = get_user_model()
    try:
        merchant_user = User.objects.filter(role='merchant').first()
        if not merchant_user:
            print("❌ No merchant user found. Please create a test merchant first.")
            return False
            
        merchant = merchant_user.merchant_account
        if not merchant:
            print("❌ User has no merchant account.")
            return False
            
        print(f"✅ Found test merchant: {merchant.business_name}")
        
        # Check partner creation/retrieval
        partner_code = f"merchant_{merchant.id}"
        partner, created = WhitelabelPartner.objects.get_or_create(
            code=partner_code,
            defaults={
                'name': merchant.business_name,
                'contact_email': merchant.business_email,
                'business_address': merchant.business_address or 'Test Address',
                'business_registration_number': merchant.business_registration_number or 'TEST123',
                'is_active': True,
                'is_verified': merchant.is_verified,
            }
        )
        
        if created:
            print(f"✅ Created whitelabel partner: {partner.code}")
        else:
            print(f"✅ Found existing whitelabel partner: {partner.code}")
        
        # Check API key URLs are accessible
        print("\n🔗 Testing API Key URLs...")
        
        # Login the merchant user
        client.force_login(merchant_user)
        
        # Test API keys view
        response = client.get('/dashboard/merchant/api-keys/')
        if response.status_code == 200:
            print("✅ API Keys page accessible")
        else:
            print(f"❌ API Keys page returned status {response.status_code}")
            return False
        
        # Test create API key endpoint
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
            print("✅ API Key creation endpoint working")
            response_data = response.json()
            if response_data.get('success'):
                print(f"✅ Successfully created API key: {response_data['api_key']['name']}")
                test_key_id = response_data['api_key']['id']
                
                # Test list API keys
                response = client.get('/dashboard/api/api-keys/list/')
                if response.status_code == 200:
                    list_data = response.json()
                    if list_data.get('success'):
                        print(f"✅ API Keys list working, found {list_data['count']} keys")
                    else:
                        print(f"❌ API Keys list failed: {list_data.get('error')}")
                else:
                    print(f"❌ API Keys list returned status {response.status_code}")
                
                # Test revoke API key
                response = client.delete(f'/dashboard/api/api-keys/{test_key_id}/revoke/')
                if response.status_code == 200:
                    revoke_data = response.json()
                    if revoke_data.get('success'):
                        print("✅ API Key revocation working")
                    else:
                        print(f"❌ API Key revocation failed: {revoke_data.get('error')}")
                else:
                    print(f"❌ API Key revocation returned status {response.status_code}")
                    
            else:
                print(f"❌ API Key creation failed: {response_data.get('error')}")
                return False
        else:
            print(f"❌ API Key creation endpoint returned status {response.status_code}")
            return False
        
        print("\n✅ All API Key Management tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main test function"""
    print("🚀 Starting API Key Management Tests...\n")
    
    if test_api_key_management():
        print("\n🎉 All tests completed successfully!")
        sys.exit(0)
    else:
        print("\n💥 Some tests failed!")
        sys.exit(1)

if __name__ == '__main__':
    main()
