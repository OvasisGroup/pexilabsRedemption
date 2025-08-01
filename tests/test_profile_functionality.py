#!/usr/bin/env python3
"""
Test script to verify the Profile Page functionality
"""

import os
import sys
import django
from django.test import Client
from django.contrib.auth import get_user_model

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pexilabs.settings')
django.setup()

from authentication.models import Merchant

def test_profile_page_functionality():
    """Test that the profile page renders and API endpoints work"""
    print("🧪 Testing Profile Page Functionality...")
    
    # Create a test client
    client = Client()
    
    User = get_user_model()
    
    try:
        # Find an existing merchant user or create one
        merchant_user = User.objects.filter(role='merchant').first()
        
        if not merchant_user:
            # Create a test merchant if none exists
            test_user = User.objects.create_user(
                email='test_profile_merchant@example.com',
                password='testpass123',
                role='merchant',
                first_name='John',
                last_name='Doe',
                phone_number='+1234567890'
            )
            
            test_merchant = Merchant.objects.create(
                user=test_user,
                business_name='Profile Test Business',
                business_email='business@profiletest.com',
                business_phone='+1987654321',
                business_address='123 Business St, Test City',
                business_registration_number='PROFILE123',
            )
            
            merchant_user = test_user
            created_test_user = True
            print(f"✅ Created test merchant: {test_merchant.business_name}")
        else:
            created_test_user = False
            print(f"✅ Using existing merchant: {merchant_user.email}")
        
        # Login the merchant user
        client.force_login(merchant_user)
        
        # Test accessing the profile page
        print("\n👤 Testing Profile page access...")
        response = client.get('/dashboard/merchant/profile/')
        
        if response.status_code == 200:
            print("✅ Profile page renders successfully!")
            
            # Check if the page contains expected elements
            content = response.content.decode()
            if 'Profile Settings' in content:
                print("✅ Page contains profile header")
            
            if 'Personal Information' in content:
                print("✅ Personal information section present")
                
            if 'Business Information' in content:
                print("✅ Business information section present")
                
            if 'Security Settings' in content:
                print("✅ Security settings section present")
                
        elif response.status_code == 302:
            print("ℹ️  Redirected (possibly authentication issue)")
            print(f"   Redirect location: {response.get('Location', 'Unknown')}")
        else:
            print(f"❌ Profile page returned status {response.status_code}")
            print(f"   Content preview: {response.content.decode()[:200]}...")
            return False
        
        # Test updating personal information
        print("\n📝 Testing personal information update...")
        personal_data = {
            'first_name': 'John Updated',
            'last_name': 'Doe Updated',
            'phone_number': '+1111111111'
        }
        
        response = client.post('/dashboard/api/profile/personal/', data=personal_data)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print("✅ Personal information update successful")
            else:
                print(f"❌ Personal information update failed: {result.get('error')}")
        else:
            print(f"❌ Personal information update returned status {response.status_code}")
        
        # Test updating business information
        print("\n🏢 Testing business information update...")
        business_data = {
            'business_name': 'Updated Business Name',
            'business_email': 'updated@business.com',
            'business_phone': '+2222222222',
            'business_address': '456 Updated Business Ave',
            'business_registration_number': 'UPDATED123'
        }
        
        response = client.post('/dashboard/api/profile/business/', data=business_data)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print("✅ Business information update successful")
            else:
                print(f"❌ Business information update failed: {result.get('error')}")
        else:
            print(f"❌ Business information update returned status {response.status_code}")
        
        # Test password change (with intentionally wrong current password)
        print("\n🔒 Testing password change validation...")
        password_data = {
            'current_password': 'wrongpassword',
            'new_password': 'newpassword123',
            'confirm_password': 'newpassword123'
        }
        
        response = client.post('/dashboard/api/profile/password/', data=password_data)
        
        if response.status_code == 400:
            result = response.json()
            if 'incorrect' in result.get('error', '').lower():
                print("✅ Password validation working (rejected wrong current password)")
            else:
                print(f"❌ Unexpected password error: {result.get('error')}")
        else:
            print(f"❌ Password change returned unexpected status {response.status_code}")
        
        # Cleanup if we created a test user
        if created_test_user:
            merchant_user.merchant_account.delete()
            merchant_user.delete()
            print("🧹 Cleaned up test data")
        
        print("\n✅ Profile functionality test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main test function"""
    print("🚀 Starting Profile Page Test...\n")
    
    if test_profile_page_functionality():
        print("\n🎉 Profile functionality verified successfully!")
        sys.exit(0)
    else:
        print("\n💥 Profile functionality verification failed!")
        sys.exit(1)

if __name__ == '__main__':
    main()
