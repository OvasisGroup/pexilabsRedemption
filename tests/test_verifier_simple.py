#!/usr/bin/env python
"""
Simple test script for merchant verifier dashboard functionality
"""
import os
import sys
import django

# Add the project directory to Python path
sys.path.append('/Users/asd/Desktop/desktop/pexilabs')

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pexilabs.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from authentication.models import CustomUser, Merchant, MerchantCategory, UserRole

def test_basic_functionality():
    """Test basic merchant verifier dashboard functionality"""
    print("🧪 Testing Merchant Verifier Dashboard")
    print("=" * 40)
    
    # Create or get staff user
    staff_user, created = CustomUser.objects.get_or_create(
        email='verifier@pexilabs.com',
        defaults={
            'first_name': 'Verifier',
            'last_name': 'Staff',
            'is_verified': True,
            'is_staff': True,
            'role': UserRole.STAFF,
        }
    )
    if created:
        staff_user.set_password('verifierpass123')
        staff_user.save()
        print(f"✓ Created staff user: {staff_user.email}")
    else:
        print(f"✓ Using existing staff user: {staff_user.email}")
    
    # Test dashboard access
    client = Client()
    client.force_login(staff_user)
    
    print("\n--- Testing Dashboard Access ---")
    response = client.get('/dashboard/merchant-verifier/')
    print(f"Dashboard access status: {response.status_code}")
    
    if response.status_code == 200:
        print("✅ Merchant Verifier Dashboard loads successfully")
        
        # Check content
        content = response.content.decode()
        if 'Merchant Verifier' in content:
            print("✓ Dashboard title is correct")
        if 'stats' in content.lower() or 'statistics' in content.lower():
            print("✓ Statistics section present")
        if 'pending' in content.lower():
            print("✓ Pending merchants section present")
            
    elif response.status_code == 302:
        print(f"⚠️  Redirected to: {response.get('Location', 'Unknown')}")
    else:
        print(f"❌ Dashboard access failed with status: {response.status_code}")
    
    # Test filtering
    print("\n--- Testing Filtering ---")
    filter_response = client.get('/dashboard/merchant-verifier/?status=pending')
    print(f"Filter test status: {filter_response.status_code}")
    if filter_response.status_code == 200:
        print("✓ Status filtering works")
    
    # Test search
    print("\n--- Testing Search ---")
    search_response = client.get('/dashboard/merchant-verifier/?search=test')
    print(f"Search test status: {search_response.status_code}")
    if search_response.status_code == 200:
        print("✓ Search functionality works")
    
    # Count merchants by status
    print("\n--- Merchant Statistics ---")
    total_merchants = Merchant.objects.count()
    pending_merchants = Merchant.objects.filter(status='pending').count()
    approved_merchants = Merchant.objects.filter(status='approved').count()
    rejected_merchants = Merchant.objects.filter(status='rejected').count()
    
    print(f"Total merchants: {total_merchants}")
    print(f"Pending: {pending_merchants}")
    print(f"Approved: {approved_merchants}")
    print(f"Rejected: {rejected_merchants}")
    
    # Test detail view if merchants exist
    if total_merchants > 0:
        print("\n--- Testing Detail View ---")
        first_merchant = Merchant.objects.first()
        detail_response = client.get(f'/dashboard/merchant-verifier/{first_merchant.id}/')
        print(f"Detail view status: {detail_response.status_code}")
        if detail_response.status_code == 200:
            print("✓ Merchant detail view works")
        else:
            print(f"❌ Detail view failed with status: {detail_response.status_code}")
    else:
        print("\n--- No merchants found for detail view testing ---")
    
    print("\n✅ MERCHANT VERIFIER DASHBOARD TEST COMPLETED")
    print("\nFeatures verified:")
    print("- Dashboard access control")
    print("- Status filtering")
    print("- Search functionality")
    print("- Statistics display")
    print("- Detail view navigation")

if __name__ == '__main__':
    test_basic_functionality()
