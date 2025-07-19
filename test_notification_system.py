#!/usr/bin/env python
"""
Test script for the notification system
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

from django.contrib.auth import get_user_model
from authentication.models import Merchant, Notification, NotificationType, NotificationPriority

def test_notification_system():
    """Test the notification system functionality"""
    User = get_user_model()
    
    print("🔧 Testing Notification System...")
    
    # Get a user with merchant account
    try:
        merchant = Merchant.objects.first()
        if not merchant:
            print("❌ No merchant found. Please create a merchant account first.")
            return
        
        user = merchant.user
        print(f"✅ Found merchant: {merchant.business_name} (User: {user.email})")
        
        # Test 1: Check if notification creation works
        print("\n📧 Test 1: Creating notifications...")
        
        # Create a test notification manually
        notification = Notification.objects.create(
            user=user,
            title="Test Notification",
            message="This is a test notification to verify the system works",
            type=NotificationType.INFO,
            priority=NotificationPriority.NORMAL,
            action_url="/dashboard/profile/",
            action_text="Update Profile"
        )
        print(f"✅ Created notification: {notification.title}")
        
        # Test 2: Check completeness reminder creation
        print("\n🔍 Test 2: Testing completeness reminder...")
        
        # Create a completeness reminder
        reminder = Notification.create_info_completeness_reminder(merchant)
        if reminder:
            print(f"✅ Created completeness reminder: {reminder.title}")
        else:
            print("ℹ️  No completeness reminder needed (info already complete)")
        
        # Test 3: Check notification counts
        print(f"\n📊 Test 3: Notification counts...")
        total_notifications = user.notifications.count()
        unread_notifications = user.notifications.filter(is_read=False).count()
        
        print(f"✅ Total notifications: {total_notifications}")
        print(f"✅ Unread notifications: {unread_notifications}")
        
        # Test 4: Test notification methods
        print(f"\n⚙️  Test 4: Testing notification methods...")
        
        if notification:
            print(f"   - Is read: {notification.is_read}")
            notification.mark_as_read()
            print(f"   - After mark_as_read: {notification.is_read}")
            
            print(f"   - Is dismissed: {notification.is_dismissed}")
            notification.dismiss()
            print(f"   - After dismiss: {notification.is_dismissed}")
        
        # Test 5: Display merchant completeness info
        print(f"\n🏢 Test 5: Merchant completeness check...")
        is_complete = merchant.is_information_complete()
        missing_info = merchant.get_missing_information()
        
        print(f"✅ Information complete: {is_complete}")
        if missing_info:
            print(f"❌ Missing information: {', '.join(missing_info)}")
        else:
            print("✅ All required information is present")
        
        print(f"\n🎉 Notification system test completed successfully!")
        
    except Exception as e:
        print(f"❌ Error during testing: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_notification_system()
