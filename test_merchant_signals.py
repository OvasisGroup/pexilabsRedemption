#!/usr/bin/env python3
"""
Test script for auto merchant account creation signals

This script tests the Django signals that automatically create merchant accounts
when users become verified.
"""

import os
import sys
import django

# Add the project directory to the Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pexilabs.settings')
django.setup()

from authentication.models import CustomUser, Merchant, MerchantCategory, Country, PreferredCurrency
from django.db import transaction
from django.utils import timezone


class MerchantSignalTester:
    """Test suite for merchant account auto-creation signals"""
    
    def __init__(self):
        self.test_emails = [
            'test.signal.user1@example.com',
            'test.signal.user2@example.com', 
            'test.signal.user3@example.com'
        ]
        self.cleanup_test_data()
        self.setup_reference_data()
    
    def cleanup_test_data(self):
        """Clean up any existing test data"""
        print("🧹 Cleaning up existing test data...")
        
        # Delete test users and their merchant accounts
        test_users = CustomUser.objects.filter(email__in=self.test_emails)
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
    
    def test_auto_merchant_creation_on_verification(self):
        """Test that merchant accounts are auto-created when users are verified"""
        print("\n" + "="*60)
        print("🧪 TEST: Auto Merchant Creation on User Verification")
        print("="*60)
        
        try:
            # Create unverified user
            user = CustomUser.objects.create_user(
                email=self.test_emails[0],
                password='testpass123',
                first_name='Test',
                last_name='User',
                phone_number='+1234567890',
                country=self.default_country,
                preferred_currency=self.default_currency,
                is_verified=False  # Start unverified
            )
            
            print(f"✓ Created unverified user: {user.email}")
            
            # Verify no merchant account exists yet
            self.assert_no_merchant_account(user)
            print("✓ Confirmed no merchant account exists for unverified user")
            
            # Now verify the user - this should trigger the signal
            user.is_verified = True
            user.save()
            
            print("✓ User verification status changed to True")
            
            # Check that merchant account was auto-created
            user.refresh_from_db()
            
            if hasattr(user, 'merchant_account'):
                merchant = user.merchant_account
                print(f"✅ SUCCESS: Merchant account auto-created!")
                print(f"   📊 Merchant ID: {merchant.id}")
                print(f"   🏢 Business Name: {merchant.business_name}")
                print(f"   📧 Business Email: {merchant.business_email}")
                print(f"   📱 Business Phone: {merchant.business_phone}")
                print(f"   📂 Category: {merchant.category.name if merchant.category else 'None'}")
                print(f"   🔍 Status: {merchant.status}")
                print(f"   ✅ Is Verified: {merchant.is_verified}")
                
                # Verify merchant details
                assert merchant.business_name == f"{user.get_full_name()}'s Business"
                assert merchant.business_email == user.email
                assert merchant.status == 'pending'
                assert merchant.is_verified == False  # Merchant verification is separate
                
                return True
            else:
                print("❌ FAILED: No merchant account was created")
                return False
                
        except Exception as e:
            print(f"❌ TEST FAILED: {e}")
            return False
    
    def test_no_duplicate_merchant_creation(self):
        """Test that duplicate merchant accounts are not created"""
        print("\n" + "="*60)
        print("🧪 TEST: No Duplicate Merchant Creation")
        print("="*60)
        
        try:
            # Create verified user (should auto-create merchant)
            user = CustomUser.objects.create_user(
                email=self.test_emails[1],
                password='testpass123',
                first_name='Test',
                last_name='User2',
                phone_number='+1234567891',
                country=self.default_country,
                preferred_currency=self.default_currency,
                is_verified=True  # Create as verified
            )
            
            print(f"✓ Created verified user: {user.email}")
            
            # Check merchant was created
            user.refresh_from_db()
            if not hasattr(user, 'merchant_account'):
                print("❌ FAILED: No merchant account was created for verified user")
                return False
            
            original_merchant_id = user.merchant_account.id
            print(f"✓ Merchant account created with ID: {original_merchant_id}")
            
            # Try to verify again (should not create duplicate)
            user.is_verified = False
            user.save()
            user.is_verified = True
            user.save()
            
            print("✓ User verification toggled (False → True)")
            
            # Check that no new merchant was created
            user.refresh_from_db()
            if hasattr(user, 'merchant_account'):
                current_merchant_id = user.merchant_account.id
                if current_merchant_id == original_merchant_id:
                    print("✅ SUCCESS: No duplicate merchant account created")
                    return True
                else:
                    print(f"❌ FAILED: Duplicate merchant created (old: {original_merchant_id}, new: {current_merchant_id})")
                    return False
            else:
                print("❌ FAILED: Merchant account was deleted")
                return False
                
        except Exception as e:
            print(f"❌ TEST FAILED: {e}")
            return False
    
    def test_no_merchant_for_unverified_user(self):
        """Test that unverified users don't get merchant accounts"""
        print("\n" + "="*60)
        print("🧪 TEST: No Merchant for Unverified User")
        print("="*60)
        
        try:
            # Create unverified user
            user = CustomUser.objects.create_user(
                email=self.test_emails[2],
                password='testpass123',
                first_name='Test',
                last_name='User3',
                phone_number='+1234567892',
                country=self.default_country,
                preferred_currency=self.default_currency,
                is_verified=False  # Keep unverified
            )
            
            print(f"✓ Created unverified user: {user.email}")
            
            # Update some other fields (but not verification)
            user.first_name = 'Updated'
            user.save()
            
            print("✓ Updated user fields (not verification)")
            
            # Verify no merchant account exists
            user.refresh_from_db()
            if hasattr(user, 'merchant_account'):
                print("❌ FAILED: Merchant account was created for unverified user")
                return False
            else:
                print("✅ SUCCESS: No merchant account created for unverified user")
                return True
                
        except Exception as e:
            print(f"❌ TEST FAILED: {e}")
            return False
    
    def assert_no_merchant_account(self, user):
        """Assert that user has no merchant account"""
        if hasattr(user, 'merchant_account'):
            raise AssertionError(f"User {user.email} should not have a merchant account")
    
    def run_all_tests(self):
        """Run all signal tests"""
        print("🎯 MERCHANT AUTO-CREATION SIGNALS TEST SUITE")
        print("=" * 60)
        print("Testing Django signals for automatic merchant account creation")
        print("when users become verified...")
        
        tests = [
            ("Auto Merchant Creation on Verification", self.test_auto_merchant_creation_on_verification),
            ("No Duplicate Merchant Creation", self.test_no_duplicate_merchant_creation),
            ("No Merchant for Unverified User", self.test_no_merchant_for_unverified_user),
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
        print("🎯 TEST SUMMARY")
        print("="*60)
        
        passed = sum(1 for _, result in results if result)
        total = len(results)
        
        for test_name, result in results:
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"{status} - {test_name}")
        
        print(f"\n📊 Overall Result: {passed}/{total} tests passed")
        
        if passed == total:
            print("\n🎉 ALL TESTS PASSED!")
            print("✅ Merchant auto-creation signals are working correctly!")
        else:
            print(f"\n⚠️  {total - passed} test(s) failed.")
            print("❌ Please review the signal implementation.")
        
        # Cleanup
        print(f"\n🧹 Cleaning up test data...")
        self.cleanup_test_data()
        print("✓ Cleanup complete")
        
        return passed == total


if __name__ == '__main__':
    tester = MerchantSignalTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)
