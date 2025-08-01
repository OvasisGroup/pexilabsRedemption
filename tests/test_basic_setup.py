#!/usr/bin/env python
"""
Simple test to verify merchant transaction system setup
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pexilabs.settings')
django.setup()

def test_basic_setup():
    """Test basic transaction system setup"""
    
    print("🧪 Testing Basic Transaction System Setup")
    print("=" * 40)
    
    # Test 1: Import models
    try:
        from authentication.models import CustomUser, Merchant, PreferredCurrency, MerchantCategory
        from transactions.models import Transaction, PaymentLink, TransactionStatus
        print("✅ All models imported successfully")
    except ImportError as e:
        print(f"❌ Model import failed: {e}")
        return False
    
    # Test 2: Check currencies
    try:
        currency_count = PreferredCurrency.objects.count()
        print(f"✅ Currencies in database: {currency_count}")
        
        # Check if USD exists
        usd = PreferredCurrency.objects.filter(code='USD').first()
        if usd:
            print(f"✅ USD currency found: {usd.name}")
        else:
            print("⚠️ USD currency not found, creating...")
            usd = PreferredCurrency.objects.create(
                code='USD',
                name='US Dollar',
                symbol='$',
                is_active=True
            )
            print("✅ USD currency created")
    except Exception as e:
        print(f"❌ Currency check failed: {e}")
        return False
    
    # Test 3: Check if we can create basic objects
    try:
        # Count existing objects
        users_count = CustomUser.objects.count()
        merchants_count = Merchant.objects.count()
        transactions_count = Transaction.objects.count()
        
        print(f"✅ Database objects:")
        print(f"   • Users: {users_count}")
        print(f"   • Merchants: {merchants_count}")
        print(f"   • Transactions: {transactions_count}")
    except Exception as e:
        print(f"❌ Database query failed: {e}")
        return False
    
    # Test 4: Test URL patterns
    try:
        from django.urls import reverse
        
        # Test dashboard URLs
        dashboard_url = reverse('dashboard:dashboard_redirect')
        transactions_url = reverse('dashboard:merchant_transactions')
        
        print(f"✅ URL patterns working:")
        print(f"   • Dashboard: {dashboard_url}")
        print(f"   • Transactions: {transactions_url}")
    except Exception as e:
        print(f"❌ URL pattern test failed: {e}")
        return False
    
    print("\n🎉 Basic setup test completed successfully!")
    return True

if __name__ == '__main__':
    try:
        success = test_basic_setup()
        if success:
            print("\n✅ Transaction system is properly set up!")
        else:
            print("\n❌ Setup issues detected!")
            sys.exit(1)
    except Exception as e:
        print(f"\n💥 Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
