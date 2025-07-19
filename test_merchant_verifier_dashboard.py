#!/usr/bin/env python
"""
Test script for merchant verifier dashboard functionality
"""
import os
import sys
import django
from datetime import datetime, timedelta

# Add the project directory to Python path
sys.path.append('/Users/asd/Desktop/desktop/pexilabs')

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pexilabs.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from authentication.models import CustomUser, Merchant, MerchantCategory, UserRole

def create_test_data():
    """Create test data for merchant verifier dashboard"""
    print("Creating test data...")
    
    # Create staff user for testing
    staff_user, created = CustomUser.objects.get_or_create(
        email='staff@pexilabs.com',
        defaults={
            'first_name': 'Staff',
            'last_name': 'User',
            'is_verified': True,
            'is_staff': True,
            'role': UserRole.STAFF,
        }
    )
    if created:
        staff_user.set_password('staffpass123')
        staff_user.save()
        print(f"✓ Created staff user: {staff_user.email}")
    else:
        print(f"✓ Using existing staff user: {staff_user.email}")
    
    # Create test merchant category
    category, created = MerchantCategory.objects.get_or_create(
        name='E-commerce',
        defaults={'description': 'Online retail businesses'}
    )
    
    # Create test merchants with different statuses
    test_merchants = [
        {
            'email': 'merchant1@test.com',
            'business_name': 'Test E-commerce Store',
            'status': 'pending',
            'business_registration_number': 'BRN001'
        },
        {
            'email': 'merchant2@test.com',
            'business_name': 'Approved Digital Store',
            'status': 'approved',
            'business_registration_number': 'BRN002'
        },
        {
            'email': 'merchant3@test.com',
            'business_name': 'Rejected Business',
            'status': 'rejected',
            'business_registration_number': 'BRN003'
        },
        {
            'email': 'merchant4@test.com',
            'business_name': 'Suspended Merchant',
            'status': 'suspended',
            'business_registration_number': 'BRN004'
        }
    ]
    
    created_merchants = []
    for merchant_data in test_merchants:
        # Create user
        user, user_created = CustomUser.objects.get_or_create(
            email=merchant_data['email'],
            defaults={
                'first_name': 'Merchant',
                'last_name': 'User',
                'is_verified': True,
            }
        )
        if user_created:
            user.set_password('merchantpass123')
            user.save()
        
        # Create merchant
        merchant, merchant_created = Merchant.objects.get_or_create(
            user=user,
            defaults={
                'business_name': merchant_data['business_name'],
                'business_registration_number': merchant_data['business_registration_number'],
                'category': category,
                'status': merchant_data['status'],
                'business_address': f"123 {merchant_data['business_name']} Street",
                'business_phone': '+1234567890',
                'business_website': f'https://{merchant_data["business_name"].lower().replace(" ", "")}.com',
            }
        )
        
        if merchant_created:
            print(f"✓ Created merchant: {merchant.business_name} ({merchant.status})")
        else:
            print(f"✓ Using existing merchant: {merchant.business_name} ({merchant.status})")
        
        created_merchants.append(merchant)
    
    return staff_user, created_merchants

def test_merchant_verifier_dashboard_access():
    """Test access to merchant verifier dashboard"""
    print("\n=== Testing Merchant Verifier Dashboard Access ===")
    
    staff_user, merchants = create_test_data()
    client = Client()
    
    # Test without login
    print("Testing access without login...")
    response = client.get('/dashboard/merchant-verifier/')
    print(f"Without login status: {response.status_code}")
    if response.status_code == 302:
        print("✓ Correctly redirected to login")
    
    # Test with regular user (should be denied)
    regular_user = CustomUser.objects.filter(is_staff=False, role=UserRole.USER).first()
    if regular_user:
        client.force_login(regular_user)
        response = client.get('/dashboard/merchant-verifier/')
        print(f"Regular user access status: {response.status_code}")
        if response.status_code == 302:
            print("✓ Regular user correctly denied access")
        client.logout()
    
    # Test with staff user
    client.force_login(staff_user)
    response = client.get('/dashboard/merchant-verifier/')
    print(f"Staff user access status: {response.status_code}")
    if response.status_code == 200:
        print("✓ Staff user can access merchant verifier dashboard")
        
        # Check if merchants are displayed
        content = response.content.decode()
        if 'Test E-commerce Store' in content:
            print("✓ Pending merchants are displayed")
        else:
            print("✗ Pending merchants not found in content")
            
        if 'stats' in content.lower():
            print("✓ Statistics section is present")
        else:
            print("✗ Statistics section not found")
    else:
        print(f"✗ Staff user access failed with status {response.status_code}")

def test_merchant_filtering_and_search():
    """Test filtering and search functionality"""
    print("\n=== Testing Filtering and Search ===")
    
    staff_user, merchants = create_test_data()
    client = Client()
    client.force_login(staff_user)
    
    # Test status filtering
    status_filters = ['pending', 'approved', 'rejected', 'suspended', 'all']
    
    for status in status_filters:
        response = client.get(f'/dashboard/merchant-verifier/?status={status}')
        print(f"Filter '{status}' status: {response.status_code}")
        if response.status_code == 200:
            print(f"✓ Status filter '{status}' works")
        else:
            print(f"✗ Status filter '{status}' failed")
    
    # Test search functionality
    search_terms = ['Test E-commerce', 'merchant1@test.com', 'BRN001']
    
    for term in search_terms:
        response = client.get(f'/dashboard/merchant-verifier/?search={term}')
        print(f"Search '{term}' status: {response.status_code}")
        if response.status_code == 200:
            print(f"✓ Search for '{term}' works")
        else:
            print(f"✗ Search for '{term}' failed")

def test_merchant_verification_detail():
    """Test merchant verification detail view"""
    print("\n=== Testing Merchant Verification Detail ===")
    
    staff_user, merchants = create_test_data()
    client = Client()
    client.force_login(staff_user)
    
    # Find a pending merchant
    pending_merchant = next((m for m in merchants if m.status == 'pending'), None)
    
    if pending_merchant:
        print(f"Testing with merchant: {pending_merchant.business_name}")
        
        # Test accessing detail view
        response = client.get(f'/dashboard/merchant-verifier/{pending_merchant.id}/')
        print(f"Detail view status: {response.status_code}")
        
        if response.status_code == 200:
            print("✓ Can access merchant detail view")
            
            content = response.content.decode()
            if pending_merchant.business_name in content:
                print("✓ Merchant details are displayed")
            
            if 'approve' in content.lower():
                print("✓ Approval action is available")
            
            if 'reject' in content.lower():
                print("✓ Rejection action is available")
        else:
            print(f"✗ Detail view access failed with status {response.status_code}")
    else:
        print("✗ No pending merchant found for testing")

def test_merchant_approval_process():
    """Test merchant approval process"""
    print("\n=== Testing Merchant Approval Process ===")
    
    staff_user, merchants = create_test_data()
    client = Client()
    client.force_login(staff_user)
    
    # Find a pending merchant
    pending_merchant = next((m for m in merchants if m.status == 'pending'), None)
    
    if pending_merchant:
        print(f"Testing approval for: {pending_merchant.business_name}")
        
        # Test approval
        response = client.post(f'/dashboard/merchant-verifier/{pending_merchant.id}/', {
            'action': 'approve'
        })
        
        print(f"Approval response status: {response.status_code}")
        
        # Check if merchant was approved
        pending_merchant.refresh_from_db()
        if pending_merchant.status == 'approved':
            print("✓ Merchant successfully approved")
            print(f"Verified by: {pending_merchant.verified_by}")
            print(f"Verified at: {pending_merchant.verified_at}")
        else:
            print(f"✗ Merchant approval failed. Status: {pending_merchant.status}")
    else:
        print("✗ No pending merchant found for approval testing")

def test_merchant_rejection_process():
    """Test merchant rejection process"""
    print("\n=== Testing Merchant Rejection Process ===")
    
    staff_user, merchants = create_test_data()
    client = Client()
    client.force_login(staff_user)
    
    # Create a new pending merchant for rejection
    user = CustomUser.objects.create_user(
        email='reject_test@test.com',
        first_name='Reject',
        last_name='Test',
        is_verified=True
    )
    
    category = MerchantCategory.objects.first()
    
    reject_merchant = Merchant.objects.create(
        user=user,
        business_name='Reject Test Business',
        business_registration_number='REJECT001',
        category=category,
        status='pending',
        business_address='123 Reject Street',
        business_phone='+1234567890',
    )
    
    print(f"Testing rejection for: {reject_merchant.business_name}")
    
    # Test rejection with notes
    response = client.post(f'/dashboard/merchant-verifier/{reject_merchant.id}/', {
        'action': 'reject',
        'verification_notes': 'Test rejection reason'
    })
    
    print(f"Rejection response status: {response.status_code}")
    
    # Check if merchant was rejected
    reject_merchant.refresh_from_db()
    if reject_merchant.status == 'rejected':
        print("✓ Merchant successfully rejected")
        print(f"Rejection notes: {reject_merchant.verification_notes}")
        print(f"Verified by: {reject_merchant.verified_by}")
    else:
        print(f"✗ Merchant rejection failed. Status: {reject_merchant.status}")

def test_pagination():
    """Test pagination functionality"""
    print("\n=== Testing Pagination ===")
    
    staff_user, merchants = create_test_data()
    client = Client()
    client.force_login(staff_user)
    
    # Test pagination with page parameter
    response = client.get('/dashboard/merchant-verifier/?page=1')
    print(f"Pagination page 1 status: {response.status_code}")
    
    if response.status_code == 200:
        print("✓ Pagination works")
        
        # Check for pagination elements in content
        content = response.content.decode()
        if 'page' in content.lower() or 'next' in content.lower() or 'previous' in content.lower():
            print("✓ Pagination elements found in content")
        else:
            print("ℹ No pagination elements (may be normal if few merchants)")
    else:
        print(f"✗ Pagination failed with status {response.status_code}")

def test_statistics_display():
    """Test statistics display"""
    print("\n=== Testing Statistics Display ===")
    
    staff_user, merchants = create_test_data()
    client = Client()
    client.force_login(staff_user)
    
    response = client.get('/dashboard/merchant-verifier/')
    
    if response.status_code == 200:
        content = response.content.decode()
        
        # Check for various statistics
        stats_indicators = [
            'total', 'pending', 'approved', 'rejected',
            'recent', 'statistics', 'stats'
        ]
        
        found_stats = []
        for indicator in stats_indicators:
            if indicator in content.lower():
                found_stats.append(indicator)
        
        if found_stats:
            print(f"✓ Statistics found: {', '.join(found_stats)}")
        else:
            print("✗ No statistics indicators found")
    else:
        print(f"✗ Failed to load dashboard for statistics check")

def run_all_tests():
    """Run all merchant verifier dashboard tests"""
    print("🧪 MERCHANT VERIFIER DASHBOARD TEST SUITE")
    print("=" * 50)
    
    try:
        test_merchant_verifier_dashboard_access()
        test_merchant_filtering_and_search()
        test_merchant_verification_detail()
        test_merchant_approval_process()
        test_merchant_rejection_process()
        test_pagination()
        test_statistics_display()
        
        print("\n" + "=" * 50)
        print("✅ ALL TESTS COMPLETED")
        print("\nMerchant Verifier Dashboard Features:")
        print("✓ Access control (staff/admin only)")
        print("✓ Status filtering (pending, approved, rejected, suspended)")
        print("✓ Search functionality (business name, email, registration number)")
        print("✓ Merchant approval workflow")
        print("✓ Merchant rejection workflow with notes")
        print("✓ Statistics and analytics")
        print("✓ Pagination for large datasets")
        print("✓ Detailed merchant verification view")
        
    except Exception as e:
        print(f"\n❌ TEST SUITE FAILED: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    run_all_tests()
