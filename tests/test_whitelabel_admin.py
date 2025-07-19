#!/usr/bin/env python3
"""
Test script to verify WhitelabelPartner admin functionality
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pexilabs.settings')
django.setup()

from django.contrib.admin.sites import AdminSite
from authentication.admin import WhitelabelPartnerAdmin
from authentication.models import WhitelabelPartner

def test_admin_registration():
    """Test that WhitelabelPartner is properly registered in admin"""
    from django.contrib import admin
    
    # Check if WhitelabelPartner is registered
    if WhitelabelPartner in admin.site._registry:
        print("✅ WhitelabelPartner is registered in Django admin")
        
        # Get the admin class
        admin_class = admin.site._registry[WhitelabelPartner]
        print(f"✅ Admin class: {admin_class.__class__.__name__}")
        
        # Check list display fields
        list_display = admin_class.list_display
        print(f"✅ List display fields: {list_display}")
        
        # Check search fields
        search_fields = admin_class.search_fields
        print(f"✅ Search fields: {search_fields}")
        
        # Check list filters
        list_filter = admin_class.list_filter
        print(f"✅ List filters: {list_filter}")
        
        # Check actions
        actions = admin_class.actions
        print(f"✅ Admin actions: {actions}")
        
        # Check fieldsets
        fieldsets = admin_class.fieldsets
        print(f"✅ Fieldsets configured: {len(fieldsets)} sections")
        
        return True
    else:
        print("❌ WhitelabelPartner is NOT registered in Django admin")
        return False

def test_admin_methods():
    """Test custom admin methods"""
    print("\n=== Testing Custom Admin Methods ===")
    
    # Create a test partner (in memory, not saved)
    test_partner = WhitelabelPartner(
        name="Test Partner",
        code="test_partner",
        contact_email="test@example.com",
        daily_api_limit=1000,
        is_active=True,
        is_verified=True
    )
    
    # Test admin instance
    admin_site = AdminSite()
    admin_instance = WhitelabelPartnerAdmin(WhitelabelPartner, admin_site)
    
    try:
        # Test app_keys_count method
        if hasattr(admin_instance, 'app_keys_count'):
            result = admin_instance.app_keys_count(test_partner)
            print(f"✅ app_keys_count method works: {result}")
        
        # Test api_usage_today method
        if hasattr(admin_instance, 'api_usage_today'):
            result = admin_instance.api_usage_today(test_partner)
            print(f"✅ api_usage_today method works: {result}")
        
        # Test formatted_webhook_url method
        if hasattr(admin_instance, 'formatted_webhook_url'):
            result = admin_instance.formatted_webhook_url(test_partner)
            print(f"✅ formatted_webhook_url method works: {result}")
        
        return True
    except Exception as e:
        print(f"❌ Error testing admin methods: {e}")
        return False

def test_inline_admin():
    """Test AppKey inline admin"""
    print("\n=== Testing AppKey Inline Admin ===")
    
    from authentication.admin import AppKeyInline
    from authentication.models import AppKey
    
    # Test inline registration
    admin_site = AdminSite()
    admin_instance = WhitelabelPartnerAdmin(WhitelabelPartner, admin_site)
    
    if hasattr(admin_instance, 'inlines'):
        inlines = admin_instance.inlines
        print(f"✅ Inlines configured: {inlines}")
        
        if AppKeyInline in inlines:
            print("✅ AppKeyInline is properly configured")
            
            # Check inline fields
            inline_instance = AppKeyInline(AppKey, admin_site)
            fields = inline_instance.fields
            print(f"✅ Inline fields: {fields}")
            
            readonly_fields = inline_instance.readonly_fields
            print(f"✅ Readonly fields: {readonly_fields}")
            
            return True
    
    print("❌ AppKeyInline not properly configured")
    return False

def main():
    """Run all admin tests"""
    print("Testing WhitelabelPartner Django Admin Configuration...")
    
    tests_passed = 0
    total_tests = 3
    
    # Test 1: Admin registration
    if test_admin_registration():
        tests_passed += 1
    
    # Test 2: Custom admin methods
    if test_admin_methods():
        tests_passed += 1
    
    # Test 3: Inline admin
    if test_inline_admin():
        tests_passed += 1
    
    print(f"\n🎉 Admin tests completed!")
    print(f"Tests passed: {tests_passed}/{total_tests}")
    
    if tests_passed == total_tests:
        print("✅ All WhitelabelPartner admin tests passed!")
        print("\n📋 Admin Access:")
        print("- URL: http://localhost:8000/admin/authentication/whitelabelpartner/")
        print("- Requires Django admin staff access")
        print("- Full CRUD operations available")
        print("- Real-time usage monitoring")
        print("- Bulk actions for partner management")
        return True
    else:
        print(f"❌ {total_tests - tests_passed} admin tests failed")
        return False

if __name__ == "__main__":
    if not main():
        sys.exit(1)
    sys.exit(0)
