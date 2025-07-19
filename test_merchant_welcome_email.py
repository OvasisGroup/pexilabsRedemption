#!/usr/bin/env python3
"""
Test script for merchant welcome email functionality

This script tests the email sending functionality when merchant accounts
are auto-created after user verification.
"""

import os
import sys
import django
import uuid

# Add the project directory to the Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pexilabs.settings')
django.setup()

from authentication.models import CustomUser, Merchant, MerchantCategory, Country, PreferredCurrency
from authentication.signals import send_merchant_welcome_email
from django.db import transaction
from django.utils import timezone


class EmailTester:
    """Test suite for merchant welcome email functionality"""
    
    def __init__(self):
        self.test_base_email = 'test.email.merchant'
        self.test_domain = 'example.com'
        self.cleanup_test_data()
        self.setup_reference_data()
    
    def get_unique_email(self, prefix="test"):
        """Generate a unique email address"""
        return f"{prefix}.{uuid.uuid4().hex[:8]}@{self.test_domain}"
    
    def cleanup_test_data(self):
        """Clean up any existing test data"""
        print("🧹 Cleaning up existing test data...")
        
        # Delete test users and their merchant accounts
        test_users = CustomUser.objects.filter(email__startswith=self.test_base_email)
        merchant_count = 0
        
        for user in test_users:
            if hasattr(user, 'merchant_account'):
                merchant_count += 1
        
        deleted_users = test_users.count()
        test_users.delete()
        
        print(f"   ✓ Deleted {deleted_users} test users")
        print(f"   ✓ Deleted {merchant_count} associated merchant accounts")
    
    def setup_reference_data(self):
        """Ensure reference data exists"""
        print("📋 Setting up reference data...")
        
        # Create default country if not exists
        country, created = Country.objects.get_or_create(
            code='US',
            defaults={
                'name': 'United States',
                'phone_code': '+1'
            }
        )
        if created:
            print("   ✓ Created default country (US)")
        
        # Create default currency if not exists
        currency, created = PreferredCurrency.objects.get_or_create(
            code='USD',
            defaults={
                'name': 'US Dollar',
                'symbol': '$'
            }
        )
        if created:
            print("   ✓ Created default currency (USD)")
        
        # Create default merchant category if not exists
        category, created = MerchantCategory.objects.get_or_create(
            code='general',
            defaults={
                'name': 'General Business',
                'description': 'Default category for new merchants'
            }
        )
        if created:
            print("   ✓ Created default merchant category (General)")
        
        self.default_country = country
        self.default_currency = currency
        self.default_category = category
    
    def test_email_template_rendering(self):
        """Test email template rendering without sending"""
        print("\n" + "="*60)
        print("🧪 TEST: Email Template Rendering")
        print("="*60)
        
        try:
            from django.template.loader import render_to_string
            
            # Create a test merchant for template context
            test_email = self.get_unique_email("template")
            user = CustomUser.objects.create_user(
                email=test_email,
                password='testpass123',
                first_name='Test',
                last_name='EmailUser',
                phone_number='+1234567890',
                country=self.default_country,
                preferred_currency=self.default_currency,
                is_verified=True
            )
            
            merchant = Merchant.objects.create(
                user=user,
                business_name=f"{user.get_full_name()}'s Business",
                business_email=user.email,
                business_phone=user.phone_number or '',
                business_address='123 Test Street, Test City, TC 12345',
                category=self.default_category,
                description=f"Test merchant account for {user.get_full_name()}",
                status='pending',
                is_verified=False,
            )
            
            print(f"✓ Created test merchant: {merchant.business_name}")
            
            # Email context data
            context = {
                'user_name': user.get_full_name(),
                'user_first_name': user.first_name,
                'business_name': merchant.business_name,
                'merchant_id': str(merchant.id),
                'business_email': merchant.business_email,
                'business_phone': merchant.business_phone,
                'category': merchant.category.name if merchant.category else 'General Business',
                'status': merchant.get_status_display(),
                'created_at': merchant.created_at.strftime('%B %d, %Y at %I:%M %p'),
                'platform_name': 'PexiLabs',
                'support_email': 'support@pexilabs.com',
                'dashboard_url': 'https://pexilabs.com/dashboard',
                'docs_url': 'https://docs.pexilabs.com',
            }
            
            # Test HTML template rendering
            try:
                html_message = render_to_string('emails/merchant_welcome.html', context)
                print("✓ HTML email template rendered successfully")
                print(f"   📊 HTML content length: {len(html_message)} characters")
            except Exception as e:
                print(f"❌ HTML template rendering failed: {e}")
                return False
            
            # Test plain text template rendering
            try:
                plain_message = render_to_string('emails/merchant_welcome.txt', context)
                print("✓ Plain text email template rendered successfully")
                print(f"   📊 Plain text content length: {len(plain_message)} characters")
            except Exception as e:
                print(f"❌ Plain text template rendering failed: {e}")
                return False
            
            # Show sample content
            print("\n📧 Sample Email Content:")
            print("Subject: Welcome to PexiLabs - Your Merchant Account is Ready!")
            print(f"To: {merchant.business_email}")
            print("Content Preview (first 200 chars):")
            print("---")
            print(plain_message[:200] + "..." if len(plain_message) > 200 else plain_message)
            print("---")
            
            return True
            
        except Exception as e:
            print(f"❌ Template rendering test failed: {e}")
            return False
    
    def test_signal_with_email(self):
        """Test the complete signal flow including email sending"""
        print("\n" + "="*60)
        print("🧪 TEST: Signal with Email Sending")
        print("="*60)
        
        try:
            # Create unverified user
            test_email = self.get_unique_email("signal")
            user = CustomUser.objects.create_user(
                email=test_email,
                password='testpass123',
                first_name='Signal',
                last_name='EmailTest',
                phone_number='+1234567890',
                country=self.default_country,
                preferred_currency=self.default_currency,
                is_verified=False
            )
            
            print(f"✓ Created unverified user: {user.email}")
            
            # Verify no merchant account exists yet
            if hasattr(user, 'merchant_account'):
                print("❌ Merchant account already exists (unexpected)")
                return False
            
            print("✓ Confirmed no merchant account exists yet")
            
            # Verify the user - this should trigger the signal and send email
            print("🔄 Verifying user (this will trigger signal and send email)...")
            user.is_verified = True
            user.save()
            
            print("✓ User verification status changed to True")
            
            # Check that merchant account was created
            user.refresh_from_db()
            
            if hasattr(user, 'merchant_account'):
                merchant = user.merchant_account
                print("✅ SUCCESS: Merchant account auto-created by signal!")
                print(f"   📊 Merchant ID: {merchant.id}")
                print(f"   🏢 Business Name: {merchant.business_name}")
                print(f"   📧 Business Email: {merchant.business_email}")
                
                print("\n📧 Email should have been sent to:", merchant.business_email)
                print("   Check your email server logs or configured email backend")
                print("   for delivery confirmation.")
                
                return True
            else:
                print("❌ FAILED: No merchant account was created")
                return False
                
        except Exception as e:
            print(f"❌ Signal test failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_manual_email_sending(self):
        """Test manual email sending function"""
        print("\n" + "="*60)
        print("🧪 TEST: Manual Email Sending")
        print("="*60)
        
        try:
            # Create a merchant for testing
            test_email = self.get_unique_email("manual")
            user = CustomUser.objects.create_user(
                email=test_email,
                password='testpass123',
                first_name='Manual',
                last_name='EmailTest',
                phone_number='+1234567890',
                country=self.default_country,
                preferred_currency=self.default_currency,
                is_verified=True
            )
            
            merchant = Merchant.objects.create(
                user=user,
                business_name=f"{user.get_full_name()}'s Test Business",
                business_email=user.email,
                business_phone=user.phone_number or '',
                business_address='123 Manual Test Street, Test City, TC 12345',
                category=self.default_category,
                description=f"Manual test merchant account for {user.get_full_name()}",
                status='pending',
                is_verified=False,
            )
            
            print(f"✓ Created test merchant: {merchant.business_name}")
            
            # Test manual email sending
            print("📧 Sending welcome email manually...")
            send_merchant_welcome_email(merchant)
            
            print("✅ SUCCESS: Manual email sending completed!")
            print(f"   📧 Email sent to: {merchant.business_email}")
            print("   Check your email server logs for delivery confirmation.")
            
            return True
            
        except Exception as e:
            print(f"❌ Manual email test failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def run_all_tests(self):
        """Run all email functionality tests"""
        print("🎯 MERCHANT WELCOME EMAIL TEST SUITE")
        print("=" * 60)
        print("Testing email functionality for merchant account creation...")
        
        tests = [
            ("Email Template Rendering", self.test_email_template_rendering),
            ("Signal with Email Sending", self.test_signal_with_email),
            ("Manual Email Sending", self.test_manual_email_sending),
        ]
        
        results = []
        
        for test_name, test_func in tests:
            try:
                result = test_func()
                results.append((test_name, result))
            except Exception as e:
                print(f"❌ {test_name} failed with error: {e}")
                results.append((test_name, False))
        
        # Summary
        print("\n" + "="*60)
        print("🎯 EMAIL TEST SUMMARY")
        print("="*60)
        
        passed = sum(1 for _, result in results if result)
        total = len(results)
        
        for test_name, result in results:
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"{status} - {test_name}")
        
        print(f"\n📊 Overall Result: {passed}/{total} tests passed")
        
        if passed == total:
            print("\n🎉 ALL EMAIL TESTS PASSED!")
            print("✅ Merchant welcome email functionality is working correctly!")
        else:
            print(f"\n⚠️  {total - passed} test(s) failed.")
            print("❌ Please review the email implementation.")
        
        print("\n💡 Email Configuration Notes:")
        print("   - Ensure Django email settings are configured in settings.py")
        print("   - Check EMAIL_HOST, EMAIL_PORT, EMAIL_HOST_USER settings")
        print("   - For testing, you can use Django's console email backend")
        print("   - In production, use a real SMTP server or email service")
        
        # Cleanup
        print(f"\n🧹 Cleaning up test data...")
        self.cleanup_test_data()
        print("✓ Cleanup complete")
        
        return passed == total


if __name__ == '__main__':
    tester = EmailTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)
