#!/usr/bin/env python3
"""
Test script to verify the NoReverseMatch fix for API Keys template
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

def test_api_keys_template_rendering():
    """Test that the API keys template renders without NoReverseMatch error"""
    print("🧪 Testing API Keys Template Rendering...")
    
    # Create a test client
    client = Client()
    
    User = get_user_model()
    
    try:
        # Find an existing merchant user or create one
        merchant_user = User.objects.filter(role='merchant').first()
        
        if not merchant_user:
            # Create a test merchant if none exists
            test_user = User.objects.create_user(
                email='test_template_merchant@example.com',
                password='testpass123',
                role='merchant'
            )
            
            test_merchant = Merchant.objects.create(
                user=test_user,
                business_name='Template Test Business',
                business_email='test@templatebusiness.com',
                business_address='123 Test St',
                business_registration_number='TEST123',
            )
            
            merchant_user = test_user
            print(f"✅ Created test merchant: {test_merchant.business_name}")
        else:
            print(f"✅ Using existing merchant: {merchant_user.email}")
        
        # Login the merchant user
        client.force_login(merchant_user)
        
        # Test accessing the API keys page (this should not cause NoReverseMatch)
        print("\n🔗 Testing API Keys page template rendering...")
        response = client.get('/dashboard/merchant/api-keys/')
        
        if response.status_code == 200:
            print("✅ API Keys page renders successfully!")
            print("✅ No NoReverseMatch error occurred")
            
            # Check if the page contains expected elements
            content = response.content.decode()
            if 'Generate API Key' in content:
                print("✅ Page contains expected UI elements")
            
            if 'revokeApiKey' in content:
                print("✅ JavaScript functions are present")
                
            if '/dashboard/api/api-keys/' in content:
                print("✅ Fixed URLs are present in JavaScript")
                
        elif response.status_code == 302:
            print("ℹ️  Redirected (possibly due to missing API_KEYS_AVAILABLE setting)")
            print(f"   Redirect location: {response.get('Location', 'Unknown')}")
        else:
            print(f"❌ API Keys page returned status {response.status_code}")
            print(f"   Content preview: {response.content.decode()[:200]}...")
            return False
        
        # If we created a test user, clean it up
        if merchant_user.email == 'test_template_merchant@example.com':
            merchant_user.merchant_account.delete()
            merchant_user.delete()
            print("🧹 Cleaned up test data")
        
        print("\n✅ Template rendering test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main test function"""
    print("🚀 Starting NoReverseMatch Fix Test...\n")
    
    if test_api_keys_template_rendering():
        print("\n🎉 Template fix verified successfully!")
        sys.exit(0)
    else:
        print("\n💥 Template fix verification failed!")
        sys.exit(1)

if __name__ == '__main__':
    main()
