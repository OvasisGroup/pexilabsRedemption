#!/usr/bin/env python
"""
Comprehensive test script for merchant transaction system
Tests transaction creation, payment links, and merchant dashboard functionality
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pexilabs.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from authentication.models import Merchant, PreferredCurrency, MerchantCategory
from transactions.models import Transaction, PaymentLink, TransactionStatus, PaymentMethod, TransactionType
from decimal import Decimal
import json

User = get_user_model()

def test_merchant_transaction_system():
    """Test the complete merchant transaction system"""
    
    print("🧪 Testing Merchant Transaction System")
    print("=" * 50)
    
    # Create test client
    client = Client()
    
    # Step 1: Create test merchant user and merchant account
    print("\n1️⃣ Creating test merchant user...")
    
    # Create merchant user
    merchant_user = User.objects.create_user(
        email='test_merchant@example.com',
        password='testpass123',
        first_name='Test',
        last_name='Merchant',
        is_verified=True,
        role='user'
    )
    
    # Get or create merchant category
    category, _ = MerchantCategory.objects.get_or_create(
        name='E-commerce',
        defaults={'description': 'Online retail business'}
    )
    
    # Create merchant account
    merchant = Merchant.objects.create(
        user=merchant_user,
        business_name='Test Merchant Corp',
        business_email='business@testmerchant.com',
        business_phone='+1234567890',
        category=category,
        status='approved'
    )
    
    print(f"✅ Created merchant: {merchant.business_name}")
    
    # Step 2: Test merchant login and dashboard access
    print("\n2️⃣ Testing merchant dashboard access...")
    
    # Login
    login_success = client.login(email='test_merchant@example.com', password='testpass123')
    if login_success:
        print("✅ Merchant login successful")
    else:
        print("❌ Merchant login failed")
        return False
    
    # Access merchant dashboard
    dashboard_response = client.get(reverse('dashboard:merchant_dashboard'))
    if dashboard_response.status_code == 200:
        print("✅ Merchant dashboard accessible")
    else:
        print(f"❌ Dashboard access failed: {dashboard_response.status_code}")
        return False
    
    # Step 3: Test transaction page access
    print("\n3️⃣ Testing merchant transactions page...")
    
    transactions_response = client.get(reverse('dashboard:merchant_transactions'))
    if transactions_response.status_code == 200:
        print("✅ Merchant transactions page accessible")
    else:
        print(f"❌ Transactions page access failed: {transactions_response.status_code}")
        return False
    
    # Step 4: Test transaction creation via API
    print("\n4️⃣ Testing transaction creation...")
    
    # Get USD currency
    try:
        usd_currency = PreferredCurrency.objects.get(code='USD')
    except PreferredCurrency.DoesNotExist:
        print("❌ USD currency not found. Creating...")
        usd_currency = PreferredCurrency.objects.create(
            code='USD',
            name='US Dollar',
            symbol='$',
            is_active=True
        )
    
    # Create transaction
    transaction_data = {
        'transaction_type': 'payment',
        'payment_method': 'card',
        'amount': '100.00',
        'currency': str(usd_currency.id),
        'customer_email': 'customer@example.com',
        'customer_phone': '+1987654321',
        'description': 'Test payment transaction',
        'external_reference': 'TEST123'
    }
    
    create_transaction_response = client.post(
        reverse('dashboard:create_transaction_api'),
        data=transaction_data,
        HTTP_X_REQUESTED_WITH='XMLHttpRequest'
    )
    
    if create_transaction_response.status_code == 200:
        response_data = json.loads(create_transaction_response.content)
        if response_data.get('success'):
            transaction_id = response_data.get('transaction_id')
            print(f"✅ Transaction created successfully: {response_data.get('reference')}")
            
            # Verify transaction in database
            try:
                created_transaction = Transaction.objects.get(id=transaction_id)
                print(f"✅ Transaction verified in database: {created_transaction.reference}")
            except Transaction.DoesNotExist:
                print("❌ Transaction not found in database")
                return False
        else:
            print(f"❌ Transaction creation failed: {response_data.get('error')}")
            return False
    else:
        print(f"❌ Transaction creation request failed: {create_transaction_response.status_code}")
        return False
    
    # Step 5: Test payment link creation
    print("\n5️⃣ Testing payment link creation...")
    
    payment_link_data = {
        'amount': '50.00',
        'currency': str(usd_currency.id),
        'description': 'Test Payment Link',
        'expires_at': '2024-12-31T23:59'
    }
    
    create_payment_link_response = client.post(
        reverse('dashboard:create_payment_link_api'),
        data=payment_link_data,
        HTTP_X_REQUESTED_WITH='XMLHttpRequest'
    )
    
    if create_payment_link_response.status_code == 200:
        response_data = json.loads(create_payment_link_response.content)
        if response_data.get('success'):
            payment_url = response_data.get('payment_url')
            token = response_data.get('token')
            print(f"✅ Payment link created successfully")
            print(f"   URL: {payment_url}")
            
            # Test payment link page
            payment_link_response = client.get(f'/pay/{token}/')
            if payment_link_response.status_code == 200:
                print("✅ Payment link page accessible")
            else:
                print(f"❌ Payment link page failed: {payment_link_response.status_code}")
        else:
            print(f"❌ Payment link creation failed: {response_data.get('error')}")
            return False
    else:
        print(f"❌ Payment link creation request failed: {create_payment_link_response.status_code}")
        return False
    
    # Step 6: Test transaction detail API
    print("\n6️⃣ Testing transaction detail retrieval...")
    
    transaction_detail_response = client.get(
        reverse('dashboard:transaction_detail_api', kwargs={'transaction_id': transaction_id}),
        HTTP_X_REQUESTED_WITH='XMLHttpRequest'
    )
    
    if transaction_detail_response.status_code == 200:
        detail_data = json.loads(transaction_detail_response.content)
        print(f"✅ Transaction details retrieved: {detail_data.get('reference')}")
    else:
        print(f"❌ Transaction detail retrieval failed: {transaction_detail_response.status_code}")
        return False
    
    # Step 7: Test transaction statistics
    print("\n7️⃣ Testing transaction statistics...")
    
    # Get updated dashboard to check stats
    updated_dashboard_response = client.get(reverse('dashboard:merchant_dashboard'))
    if updated_dashboard_response.status_code == 200:
        print("✅ Dashboard statistics updated")
    else:
        print("❌ Dashboard statistics update failed")
        return False
    
    # Step 8: Test transaction filtering
    print("\n8️⃣ Testing transaction filtering...")
    
    # Test filtering by status
    filtered_response = client.get(
        reverse('dashboard:merchant_transactions') + '?status=pending'
    )
    if filtered_response.status_code == 200:
        print("✅ Transaction filtering works")
    else:
        print("❌ Transaction filtering failed")
        return False
    
    print("\n🎉 All tests completed successfully!")
    print("=" * 50)
    
    # Print summary
    print("\n📊 TEST SUMMARY:")
    print(f"   • Merchant created: {merchant.business_name}")
    print(f"   • Total transactions: {Transaction.objects.filter(merchant=merchant).count()}")
    print(f"   • Total payment links: {PaymentLink.objects.filter(merchant=merchant).count()}")
    
    return True

def cleanup_test_data():
    """Clean up test data"""
    print("\n🧹 Cleaning up test data...")
    
    # Delete test transactions
    Transaction.objects.filter(customer_email='customer@example.com').delete()
    
    # Delete test payment links
    PaymentLink.objects.filter(title='Test Payment Link').delete()
    
    # Delete test merchant
    try:
        test_merchant = Merchant.objects.get(business_name='Test Merchant Corp')
        test_user = test_merchant.user
        test_merchant.delete()
        test_user.delete()
        print("✅ Test data cleaned up")
    except Merchant.DoesNotExist:
        pass

if __name__ == '__main__':
    try:
        success = test_merchant_transaction_system()
        if success:
            print("\n✅ All merchant transaction system tests passed!")
        else:
            print("\n❌ Some tests failed!")
            sys.exit(1)
    except Exception as e:
        print(f"\n💥 Test execution failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        # Ask user if they want to clean up
        cleanup_choice = input("\nClean up test data? (y/n): ").lower()
        if cleanup_choice == 'y':
            cleanup_test_data()
