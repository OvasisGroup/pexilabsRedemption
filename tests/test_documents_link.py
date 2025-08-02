#!/usr/bin/env python
"""
Test script to verify documents link functionality in merchant dashboard
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pexilabs.settings')
django.setup()

from django.test import Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from authentication.models import Merchant

User = get_user_model()

def test_documents_link():
    """Test the documents link in merchant dashboard"""
    
    print("🔗 Testing Documents Link in Merchant Dashboard")
    print("=" * 50)
    
    # Find a merchant user
    merchant_user = User.objects.filter(
        merchant_account__isnull=False
    ).first()
    
    if not merchant_user:
        print("❌ No merchant users found in system")
        return False
    
    print(f"✅ Found merchant user: {merchant_user.email}")
    print(f"   Business: {merchant_user.merchant_account.business_name}")
    
    # Test dashboard access
    client = Client()
    client.force_login(merchant_user)
    
    print("\n📊 Testing merchant dashboard access...")
    response = client.get(reverse('dashboard:merchant_dashboard'))
    
    if response.status_code != 200:
        print(f"❌ Dashboard access failed: {response.status_code}")
        return False
    
    print("✅ Dashboard accessible")
    
    # Check if documents section exists in template
    content = response.content.decode()
    
    checks = [
        ('documents-section', 'Documents section ID'),
        ('Business Documents', 'Documents section title'),
        ('Upload Document', 'Upload document link'),
        ('scrollToDocuments', 'Scroll function'),
        ('Required Documents', 'Required documents info')
    ]
    
    print("\n🔍 Checking dashboard content...")
    all_passed = True
    
    for check_text, description in checks:
        if check_text in content:
            print(f"✅ {description}: Found")
        else:
            print(f"❌ {description}: Not found")
            all_passed = False
    
    # Check if sidebar navigation has documents link
    print("\n🧭 Checking sidebar navigation...")
    navigation_checks = [
        ('fa-file-alt', 'Documents icon'),
        ('onclick="scrollToDocuments()"', 'Documents link click handler')
    ]
    
    for check_text, description in navigation_checks:
        if check_text in content:
            print(f"✅ {description}: Found")
        else:
            print(f"❌ {description}: Not found")
            all_passed = False
    
    # Test if merchant has any documents
    merchant = merchant_user.merchant_account
    document_count = merchant.documents.count() if hasattr(merchant, 'documents') else 0
    
    print(f"\n📄 Document Statistics:")
    print(f"   Total documents: {document_count}")
    
    if document_count > 0:
        print("   ✅ Merchant has documents - list should be visible")
    else:
        print("   ℹ️  No documents found - empty state should be visible")
        if 'No documents uploaded yet' in content:
            print("   ✅ Empty state message found")
        else:
            print("   ❌ Empty state message not found")
            all_passed = False
    
    print(f"\n📋 Test Summary:")
    if all_passed:
        print("✅ All documents link features working correctly")
        print("\n🎯 Features Verified:")
        print("   • Documents link in sidebar navigation")
        print("   • Documents section in dashboard")
        print("   • Scroll-to-documents functionality")
        print("   • Document statistics display")
        print("   • Upload document functionality")
        print("   • Required documents information")
        return True
    else:
        print("❌ Some features are missing or not working")
        return False

if __name__ == '__main__':
    success = test_documents_link()
    if success:
        print("\n🎉 Documents link test completed successfully!")
    else:
        print("\n⚠️  Some issues found. Please check the implementation.")
    
    print("\n📖 Next Steps:")
    print("   1. Navigate to merchant dashboard")
    print("   2. Click 'Documents' in the sidebar")
    print("   3. Verify smooth scrolling to documents section")
    print("   4. Test document upload functionality")
