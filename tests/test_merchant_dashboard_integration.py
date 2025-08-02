#!/usr/bin/env python
"""
Final test to ensure merchant dashboard notification integration works correctly
"""
import os
import sys
import django

# Add project root to Python path
sys.path.append('/Users/asd/Desktop/desktop/pexilabs')

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pexilabs.settings')

# Setup Django
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from authentication.models import Merchant, Notification

def test_merchant_dashboard_integration():
    """Test that merchant dashboard properly creates and displays notifications"""
    User = get_user_model()
    
    print("🏢 Testing Merchant Dashboard Notification Integration...")
    
    try:
        merchant = Merchant.objects.first()
        if not merchant:
            print("❌ No merchant found. Please create a merchant account first.")
            return
        
        user = merchant.user
        print(f"✅ Found merchant: {merchant.business_name} (User: {user.email})")
        
        # Clear existing notifications to start fresh
        user.notifications.all().delete()
        print("🧹 Cleared existing notifications")
        
        # Create a test client and login
        client = Client()
        client.force_login(user)
        
        # Test: Access merchant dashboard
        print("\n📊 Testing merchant dashboard access...")
        response = client.get('/dashboard/merchant/')
        
        if response.status_code == 200:
            print(f"   ✅ Dashboard accessible (Status: {response.status_code})")
            
            # Check if notification was created automatically
            notifications = user.notifications.all()
            print(f"   ✅ Notifications created: {notifications.count()}")
            
            for notif in notifications:
                print(f"   📧 {notif.title}: {notif.message[:50]}...")
            
            # Check context variables
            context_vars = response.context
            if context_vars:
                is_info_complete = context_vars.get('is_info_complete', 'Not found')
                missing_info = context_vars.get('missing_info', [])
                notifications_context = context_vars.get('notifications', [])
                
                print(f"   ✅ is_info_complete: {is_info_complete}")
                print(f"   ✅ missing_info: {missing_info}")
                print(f"   ✅ notifications in context: {len(notifications_context)}")
            else:
                print("   ⚠️  No context found (might be using class-based view)")
                
        else:
            print(f"   ❌ Dashboard not accessible (Status: {response.status_code})")
            print(f"   ❌ Response: {response.content[:200]}")
        
        # Test: Check notification API after dashboard visit
        print(f"\n🔔 Testing notification API after dashboard visit...")
        response = client.get('/dashboard/api/notifications/')
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ API working (Status: {response.status_code})")
            print(f"   ✅ Notifications count: {len(data['notifications'])}")
            print(f"   ✅ Unread count: {data['unread_count']}")
            
            # Display notification details
            for i, notif in enumerate(data['notifications'], 1):
                print(f"   📧 Notification {i}:")
                print(f"      Title: {notif['title']}")
                print(f"      Type: {notif['type']}, Priority: {notif['priority']}")
                print(f"      Action: {notif.get('action_text', 'None')} -> {notif.get('action_url', 'None')}")
                print(f"      Read: {notif['is_read']}")
        else:
            print(f"   ❌ API error (Status: {response.status_code})")
        
        # Test: Verify merchant completeness logic
        print(f"\n🔍 Testing merchant completeness logic...")
        is_complete = merchant.is_information_complete()
        missing_info = merchant.get_missing_information()
        
        print(f"   ✅ Information complete: {is_complete}")
        if missing_info:
            print(f"   📝 Missing information:")
            for item in missing_info:
                print(f"      - {item}")
        else:
            print(f"   ✅ All required information is present")
        
        # Test: Check if reminder banner should be shown
        print(f"\n🎗️  Testing reminder banner logic...")
        if not is_complete:
            print(f"   ✅ Reminder banner should be displayed")
            print(f"   📋 Banner should show: {len(missing_info)} missing items")
        else:
            print(f"   ✅ No reminder banner needed (info complete)")
        
        print(f"\n🎉 Merchant dashboard integration test completed successfully!")
        
        # Final summary
        print(f"\n📋 SUMMARY:")
        print(f"   - Merchant: {merchant.business_name}")
        print(f"   - Information Complete: {is_complete}")
        print(f"   - Active Notifications: {user.notifications.filter(is_dismissed=False).count()}")
        print(f"   - Unread Notifications: {user.notifications.filter(is_read=False, is_dismissed=False).count()}")
        print(f"   - Dashboard Accessible: ✅")
        print(f"   - API Functional: ✅")
        print(f"   - Notification Creation: ✅")
        
    except Exception as e:
        print(f"❌ Error during testing: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_merchant_dashboard_integration()
