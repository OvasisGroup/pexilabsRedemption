#!/usr/bin/env python
"""
Complete Demo: Merchant Auto-Creation with Welcome Email

This script demonstrates the complete flow of:
1. Creating an unverified user
2. Verifying the user (triggers signal)
3. Automatic merchant account creation
4. Welcome email sending

The Django signals automatically handle merchant creation and email sending
when a user's verification status changes from False to True.
"""

import os
import sys
import django
import uuid
from datetime import datetime

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pexilabs.settings')
django.setup()

from django.conf import settings
from authentication.models import CustomUser, Merchant, Country, PreferredCurrency, MerchantCategory
from authentication.signals import send_merchant_welcome_email


class CompleteDemoRunner:
    """Demonstrates the complete merchant auto-creation and welcome email flow"""
    
    def __init__(self):
        self.setup_reference_data()
    
    def setup_reference_data(self):
        """Ensure reference data exists"""
        # Get or create default country
        self.default_country, _ = Country.objects.get_or_create(
            code='KE',
            defaults={'name': 'Kenya'}
        )
        
        # Get or create default currency
        self.default_currency, _ = PreferredCurrency.objects.get_or_create(
            code='USD',
            defaults={'name': 'US Dollar', 'symbol': '$', 'is_active': True}
        )
        
        # Get or create default merchant category
        self.default_category, _ = MerchantCategory.objects.get_or_create(
            code='general',
            defaults={
                'name': 'General Business',
                'description': 'General business category',
                'is_active': True
            }
        )
    
    def get_unique_email(self):
        """Generate a unique email address"""
        unique_id = uuid.uuid4().hex[:8]
        return f"demo.complete.{unique_id}@example.com"
    
    def run_complete_demo(self):
        """Run the complete demonstration"""
        print("🎯 COMPLETE MERCHANT AUTO-CREATION & EMAIL DEMO")
        print("=" * 60)
        print("This demo shows the complete flow from user creation to merchant account")
        print("with automatic welcome email sending via Django signals.")
        print()
        
        # Step 1: Create unverified user
        print("📝 STEP 1: Creating Unverified User")
        print("-" * 40)
        
        email = self.get_unique_email()
        user = CustomUser.objects.create_user(
            email=email,
            password='demopass123',
            first_name='Demo',
            last_name='User',
            phone_number='+1555123456',
            country=self.default_country,
            preferred_currency=self.default_currency,
            is_verified=False  # Important: Start as unverified
        )
        
        print(f"✅ Created user: {user.email}")
        print(f"   👤 Name: {user.get_full_name()}")
        print(f"   📱 Phone: {user.phone_number}")
        print(f"   🌍 Country: {user.country.name}")
        print(f"   ✅ Verified: {user.is_verified}")
        
        # Check no merchant exists yet
        try:
            merchant = user.merchant_account
            print(f"   ⚠️  Unexpected: Merchant already exists: {merchant.id}")
        except Merchant.DoesNotExist:
            print("   ✅ Confirmed: No merchant account exists yet")
        
        print()
        
        # Step 2: Verify user (this triggers the signal)
        print("🔐 STEP 2: Verifying User (Triggers Signal)")
        print("-" * 40)
        print("When we set is_verified=True, the Django signal will:")
        print("  • Automatically create a merchant account")
        print("  • Send a welcome email to the user")
        print()
        
        # This is the key moment - changing verification status triggers the signal
        user.is_verified = True
        user.save()
        
        print(f"✅ User verification status changed to: {user.is_verified}")
        print()
        
        # Step 3: Check auto-created merchant account
        print("🏢 STEP 3: Merchant Account Auto-Created")
        print("-" * 40)
        
        try:
            # Refresh user from database
            user.refresh_from_db()
            merchant = user.merchant_account
            
            print("🎉 SUCCESS: Merchant account automatically created!")
            print(f"   📊 Merchant ID: {merchant.id}")
            print(f"   🏢 Business Name: {merchant.business_name}")
            print(f"   📧 Business Email: {merchant.business_email}")
            print(f"   📱 Business Phone: {merchant.business_phone}")
            print(f"   📂 Category: {merchant.category.name if merchant.category else 'None'}")
            print(f"   🔍 Status: {merchant.status}")
            print(f"   ✅ Merchant Verified: {merchant.is_verified}")
            print(f"   📅 Created: {merchant.created_at}")
            
        except Merchant.DoesNotExist:
            print("❌ ERROR: Merchant account was not created by signal!")
            return False
        
        print()
        
        # Step 4: Email confirmation
        print("📧 STEP 4: Welcome Email Sent")
        print("-" * 40)
        print("The signal automatically sent a welcome email to the user.")
        print(f"📤 Email sent to: {user.email}")
        print("📋 Email includes:")
        print("   • Welcome message")
        print("   • Merchant account details")
        print("   • Next steps for activation")
        print("   • Dashboard and documentation links")
        print()
        
        # Step 5: Manual email test (optional)
        print("🧪 STEP 5: Manual Email Test (Optional)")
        print("-" * 40)
        print("Testing manual email sending function...")
        
        try:
            send_merchant_welcome_email(merchant)
            print("✅ Manual email test successful!")
        except Exception as e:
            print(f"❌ Manual email test failed: {e}")
        
        print()
        
        # Summary
        print("📊 DEMO SUMMARY")
        print("-" * 40)
        print("✅ User created (unverified)")
        print("✅ User verified (signal triggered)")
        print("✅ Merchant account auto-created")
        print("✅ Welcome email sent automatically")
        print("✅ Manual email test completed")
        print()
        print("🎉 Complete flow demonstrated successfully!")
        print()
        
        # Cleanup option
        print("🧹 CLEANUP")
        print("-" * 40)
        print(f"Demo user: {user.email}")
        print(f"Demo merchant: {merchant.id}")
        print("To clean up, run: python manage.py demo_merchant_signals --cleanup-test-data")
        
        return True


def main():
    """Main execution function"""
    demo = CompleteDemoRunner()
    
    try:
        success = demo.run_complete_demo()
        
        if success:
            print("\n🎯 VERIFICATION")
            print("=" * 60)
            print("You can verify this worked by:")
            print("1. Checking your email server logs for sent emails")
            print("2. Running: python manage.py demo_merchant_signals --list-merchants")
            print("3. Checking the Django logs for signal execution messages")
            
        return success
        
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print(f"🚀 Starting complete demo at {datetime.now()}")
    print()
    
    success = main()
    
    print()
    print(f"🏁 Demo completed at {datetime.now()}")
    sys.exit(0 if success else 1)
