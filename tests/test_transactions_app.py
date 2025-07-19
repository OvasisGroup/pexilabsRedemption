#!/usr/bin/env python
"""
Test script for the Transactions App
This script demonstrates the full functionality of the transactions app.
"""

import os
import sys
import django
from decimal import Decimal
from datetime import datetime, timedelta

# Add the project directory to the path
sys.path.append('/Users/asd/Desktop/desktop/pexilabs')

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pexilabs.settings')
django.setup()

from django.utils import timezone
from authentication.models import CustomUser, Merchant, PreferredCurrency, Country
from transactions.models import (
    PaymentGateway, Transaction, PaymentLink, TransactionEvent, Webhook,
    PaymentMethod, TransactionType, TransactionStatus
)


def create_test_data():
    """Create test data for transactions"""
    print("🏗️  Creating test data...")
    
    # Create a country and currency
    country, _ = Country.objects.get_or_create(
        name="United States",
        defaults={'code': 'US', 'phone_code': '+1'}
    )
    
    currency, _ = PreferredCurrency.objects.get_or_create(
        name="US Dollar",
        defaults={'code': 'USD', 'symbol': '$', 'is_active': True}
    )
    
    # Create test merchant user
    merchant_user, created = CustomUser.objects.get_or_create(
        email="merchant@example.com",
        defaults={
            'first_name': 'John',
            'last_name': 'Merchant',
            'is_verified': True,
            'country': country,
            'preferred_currency': currency
        }
    )
    if created:
        merchant_user.set_password('testpass123')
        merchant_user.save()
    
    # Create merchant account
    merchant, _ = Merchant.objects.get_or_create(
        user=merchant_user,
        defaults={
            'business_name': 'Test Merchant Co.',
            'business_address': '123 Business St, City, State',
            'business_phone': '+1-555-0123',
            'business_email': 'merchant@example.com',
            'status': 'approved',
            'is_verified': True
        }
    )
    
    # Create test customer
    customer, created = CustomUser.objects.get_or_create(
        email="customer@example.com",
        defaults={
            'first_name': 'Jane',
            'last_name': 'Customer',
            'is_verified': True,
            'country': country,
            'preferred_currency': currency
        }
    )
    if created:
        customer.set_password('testpass123')
        customer.save()
    
    print(f"✅ Created merchant: {merchant.business_name}")
    print(f"✅ Created customer: {customer.get_full_name()}")
    
    return merchant, customer, currency


def create_payment_gateway():
    """Create a test payment gateway"""
    print("\n💳 Creating payment gateway...")
    
    gateway, created = PaymentGateway.objects.get_or_create(
        code="stripe_test",
        defaults={
            'name': 'Stripe (Test)',
            'description': 'Stripe payment gateway for testing',
            'api_endpoint': 'https://api.stripe.com/v1',
            'webhook_endpoint': 'https://webhook.example.com/stripe',
            'merchant_id': 'acct_test123',
            'supports_payments': True,
            'supports_refunds': True,
            'supports_payouts': False,
            'supports_webhooks': True,
            'supported_payment_methods': 'card,bank_transfer,wallet',
            'supported_currencies': 'USD,EUR,GBP',
            'min_amount': Decimal('0.50'),
            'max_amount': Decimal('10000.00'),
            'transaction_fee_percentage': Decimal('0.0290'),
            'transaction_fee_fixed': Decimal('0.30'),
            'is_active': True,
            'is_sandbox': True,
            'priority': 1
        }
    )
    
    if created:
        print(f"✅ Created payment gateway: {gateway.name}")
    else:
        print(f"✅ Using existing payment gateway: {gateway.name}")
    
    return gateway


def test_transactions(merchant, customer, currency, gateway):
    """Test transaction creation and management"""
    print("\n💰 Testing transactions...")
    
    # Test 1: Create a payment transaction
    payment = Transaction.objects.create(
        merchant=merchant,
        customer=customer,
        transaction_type=TransactionType.PAYMENT,
        payment_method=PaymentMethod.CARD,
        gateway=gateway,
        currency=currency,
        amount=Decimal('100.00'),
        description='Test payment for product purchase',
        metadata={'product_id': 'prod_123', 'order_id': 'order_456'},
        payment_details={'card_last4': '4242', 'card_brand': 'visa'},
        ip_address='192.168.1.100',
        user_agent='Mozilla/5.0 (Test Browser)'
    )
    
    print(f"✅ Created payment transaction: {payment.reference}")
    print(f"   Amount: {payment.amount} {payment.currency.code}")
    print(f"   Status: {payment.get_status_display()}")
    print(f"   Fee: {payment.fee_amount}")
    print(f"   Net: {payment.net_amount}")
    
    # Test 2: Process the payment
    payment.mark_as_processing()
    print(f"✅ Transaction marked as processing")
    
    # Create transaction event
    TransactionEvent.objects.create(
        transaction=payment,
        event_type='status_change',
        old_status='pending',
        new_status='processing',
        description='Payment processing started',
        source='gateway',
        metadata={'gateway_response': 'Processing initiated'}
    )
    
    # Test 3: Complete the payment
    payment.mark_as_completed()
    print(f"✅ Transaction completed")
    
    # Test 4: Test refund capability
    if payment.can_refund():
        print(f"✅ Transaction can be refunded")
        print(f"   Remaining refundable amount: {payment.get_remaining_refundable_amount()}")
        
        # Create a partial refund
        refund = payment.create_refund(
            amount=Decimal('25.00'),
            reason='Customer requested partial refund',
            created_by=merchant.user
        )
        
        refund.mark_as_completed()
        print(f"✅ Created refund: {refund.reference}")
        print(f"   Refund amount: {refund.amount}")
        print(f"   Remaining refundable: {payment.get_remaining_refundable_amount()}")
    
    return payment


def test_payment_links(merchant, currency):
    """Test payment link creation"""
    print("\n🔗 Testing payment links...")
    
    # Create a payment link
    payment_link = PaymentLink.objects.create(
        merchant=merchant,
        title='Product Purchase',
        description='Purchase our amazing product',
        currency=currency,
        amount=Decimal('49.99'),
        is_amount_flexible=False,
        expires_at=timezone.now() + timedelta(days=30),
        max_uses=100,
        require_name=True,
        require_email=True,
        require_phone=False,
        allowed_payment_methods='card,bank_transfer',
        success_url='https://example.com/success',
        cancel_url='https://example.com/cancel',
        metadata={'product_id': 'prod_789'}
    )
    
    print(f"✅ Created payment link: {payment_link.title}")
    print(f"   Slug: {payment_link.slug}")
    print(f"   Amount: {payment_link.amount} {payment_link.currency.code}")
    print(f"   URL: {payment_link.get_absolute_url()}")
    print(f"   Usable: {payment_link.is_usable()}")
    
    # Display usage information
    if payment_link.max_uses:
        usage_display = f"{payment_link.current_uses}/{payment_link.max_uses}"
    else:
        usage_display = f"{payment_link.current_uses}/∞"
    print(f"   Usage: {usage_display}")
    
    return payment_link


def test_webhook_tracking(transaction):
    """Test webhook creation and tracking"""
    print("\n🔔 Testing webhook tracking...")
    
    # Create a webhook
    webhook = Webhook.objects.create(
        transaction=transaction,
        url='https://merchant.example.com/webhooks/payment',
        event_type='payment.completed',
        payload={
            'event': 'payment.completed',
            'transaction_id': str(transaction.id),
            'amount': str(transaction.amount),
            'currency': transaction.currency.code,
            'timestamp': timezone.now().isoformat()
        },
        headers={'Content-Type': 'application/json', 'X-Webhook-Signature': 'test_signature'}
    )
    
    print(f"✅ Created webhook: {webhook.event_type}")
    print(f"   URL: {webhook.url}")
    print(f"   Attempts: {webhook.attempts}")
    print(f"   Delivered: {webhook.is_delivered}")
    
    # Simulate successful delivery
    webhook.status_code = 200
    webhook.response_body = '{"status": "received"}'
    webhook.response_time_ms = 150
    webhook.mark_as_delivered()
    
    print(f"✅ Webhook delivered successfully")
    
    return webhook


def test_statistics(merchant):
    """Test transaction statistics"""
    print("\n📊 Testing transaction statistics...")
    
    # Get merchant stats
    stats = Transaction.get_merchant_stats(merchant)
    
    print(f"✅ Transaction Statistics for {merchant.business_name}:")
    print(f"   Total transactions: {stats['total_transactions']}")
    print(f"   Completed transactions: {stats['completed_transactions']}")
    print(f"   Failed transactions: {stats['failed_transactions']}")
    print(f"   Success rate: {stats['success_rate']}%")
    print(f"   Total volume: ${stats['total_volume']}")
    print(f"   Total fees: ${stats['total_fees']}")
    print(f"   Net volume: ${stats['net_volume']}")
    
    return stats


def run_comprehensive_test():
    """Run comprehensive test of the transactions app"""
    print("🚀 Starting Transactions App Test")
    print("=" * 50)
    
    try:
        # Step 1: Create test data
        merchant, customer, currency = create_test_data()
        
        # Step 2: Create payment gateway
        gateway = create_payment_gateway()
        
        # Step 3: Test transactions
        transaction = test_transactions(merchant, customer, currency, gateway)
        
        # Step 4: Test payment links
        payment_link = test_payment_links(merchant, currency)
        
        # Step 5: Test webhook tracking
        webhook = test_webhook_tracking(transaction)
        
        # Step 6: Test statistics
        stats = test_statistics(merchant)
        
        print("\n" + "=" * 50)
        print("🎉 All tests completed successfully!")
        print("\n📋 Summary:")
        print(f"   - Payment Gateway: {gateway.name}")
        print(f"   - Transaction: {transaction.reference} ({transaction.get_status_display()})")
        print(f"   - Payment Link: {payment_link.slug}")
        print(f"   - Webhook: {webhook.event_type} (delivered: {webhook.is_delivered})")
        print(f"   - Total Volume: ${stats['total_volume']}")
        
        print("\n✅ Transactions app is fully functional!")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_comprehensive_test()
    sys.exit(0 if success else 1)
