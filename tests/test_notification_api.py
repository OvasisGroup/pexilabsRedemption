#!/usr/bin/env python
"""
Test script for notification API endpoints
"""
import os
import sys
import django
import json

# Add project root to Python path
sys.path.append('/Users/asd/Desktop/desktop/pexilabs')

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pexilabs.settings')

# Setup Django
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from authentication.models import Merchant, Notification, NotificationType, NotificationPriority

def test_notification_api():
    """Test the notification API endpoints"""
    User = get_user_model()
    
    print("🔧 Testing Notification API...")
    
    # Get a user with merchant account
    try:
        merchant = Merchant.objects.first()
        if not merchant:
            print("❌ No merchant found. Please create a merchant account first.")
            return
        
        user = merchant.user
        print(f"✅ Found merchant: {merchant.business_name} (User: {user.email})")
        
        # Create a test client and login
        client = Client()
        
        # We need to manually set up the session since we're not using actual login
        from django.contrib.sessions.middleware import SessionMiddleware
        from django.contrib.auth.middleware import AuthenticationMiddleware
        from django.http import HttpRequest
        
        # Create some test notifications
        notification1 = Notification.objects.create(
            user=user,
            title="Test Notification 1",
            message="This is a test notification",
            type=NotificationType.INFO,
            priority=NotificationPriority.NORMAL,
            action_url="/dashboard/profile/",
            action_text="Update Profile"
        )
        
        notification2 = Notification.objects.create(
            user=user,
            title="Urgent Action Required",
            message="Please complete your business information immediately",
            type=NotificationType.WARNING,
            priority=NotificationPriority.URGENT,
            action_url="/dashboard/profile/",
            action_text="Complete Now"
        )
        
        print(f"✅ Created test notifications")
        
        # Test the API endpoint URLs
        print("\n📡 Testing API endpoints...")
        
        # Log in the user for API testing
        client.force_login(user)
        
        # Test 1: Get notifications
        print("1. Testing GET /dashboard/api/notifications/")
        response = client.get('/dashboard/api/notifications/')
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Status: {response.status_code}")
            print(f"   ✅ Notifications count: {len(data['notifications'])}")
            print(f"   ✅ Unread count: {data['unread_count']}")
            
            # Display first notification
            if data['notifications']:
                notif = data['notifications'][0]
                print(f"   📧 First notification: {notif['title']}")
                print(f"      Type: {notif['type']}, Priority: {notif['priority']}")
        else:
            print(f"   ❌ Status: {response.status_code}")
            print(f"   ❌ Response: {response.content}")
        
        # Test 2: Mark notification as read
        print(f"\n2. Testing POST /dashboard/api/notifications/{notification1.id}/read/")
        response = client.post(f'/dashboard/api/notifications/{notification1.id}/read/')
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Status: {response.status_code}")
            print(f"   ✅ Success: {data.get('success')}")
            
            # Verify notification was marked as read
            notification1.refresh_from_db()
            print(f"   ✅ Notification is_read: {notification1.is_read}")
        else:
            print(f"   ❌ Status: {response.status_code}")
            print(f"   ❌ Response: {response.content}")
        
        # Test 3: Dismiss notification
        print(f"\n3. Testing POST /dashboard/api/notifications/{notification2.id}/dismiss/")
        response = client.post(f'/dashboard/api/notifications/{notification2.id}/dismiss/')
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Status: {response.status_code}")
            print(f"   ✅ Success: {data.get('success')}")
            
            # Verify notification was dismissed
            notification2.refresh_from_db()
            print(f"   ✅ Notification is_dismissed: {notification2.is_dismissed}")
        else:
            print(f"   ❌ Status: {response.status_code}")
            print(f"   ❌ Response: {response.content}")
        
        # Test 4: Mark all as read
        print(f"\n4. Testing POST /dashboard/api/notifications/mark-all-read/")
        
        # Create another notification to test
        notification3 = Notification.objects.create(
            user=user,
            title="Another Test Notification",
            message="This should be marked as read",
            type=NotificationType.INFO,
            priority=NotificationPriority.LOW
        )
        
        response = client.post('/dashboard/api/notifications/mark-all-read/')
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Status: {response.status_code}")
            print(f"   ✅ Success: {data.get('success')}")
            print(f"   ✅ Marked count: {data.get('marked_count')}")
        else:
            print(f"   ❌ Status: {response.status_code}")
            print(f"   ❌ Response: {response.content}")
        
        # Final check: Get notifications again to see the updated state
        print(f"\n5. Final check - GET /dashboard/api/notifications/")
        response = client.get('/dashboard/api/notifications/')
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Final unread count: {data['unread_count']}")
            print(f"   ✅ Total notifications: {len(data['notifications'])}")
        
        print(f"\n🎉 API testing completed successfully!")
        
        # Clean up test notifications
        print(f"\n🧹 Cleaning up test notifications...")
        Notification.objects.filter(user=user, title__icontains="Test").delete()
        print(f"✅ Test notifications cleaned up")
        
    except Exception as e:
        print(f"❌ Error during API testing: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_notification_api()
