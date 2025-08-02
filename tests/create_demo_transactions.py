#!/usr/bin/env python
"""
Create demo transaction data to test the merchant transaction system
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pexilabs.settings')
django.setup()

from django.contrib.auth import get_user_model
from authentication.models import Merchant, PreferredCurrency, MerchantCategory
from transactions.models import Transaction, PaymentLink, TransactionStatus, PaymentMethod, TransactionType
from decimal import Decimal
from datetime import datetime, timedelta
from django.utils import timezone
import uuid

User = get_user_model()

def create_demo_data():
    """Create demo transaction data for testing"""
    
    print("📦 Creating Demo Transaction Data")
    print("=" * 40)
    
    # Step 1: Ensure we have a merchant account
    try:
        # Try to find existing admin user
        admin_user = User.objects.filter(is_superuser=True).first()
        if not admin_user:
            print("Creating admin user...")
            admin_user = User.objects.create_superuser(
                email='admin@pexilabs.com',
                password='admin123',
                first_name='Admin',
                last_name='User'
            )
        
        print(f"✅ Admin user: {admin_user.email}")
        
        # Check if admin has merchant account
        if not hasattr(admin_user, 'merchant_account') or not admin_user.merchant_account:
            # Create merchant category if doesn't exist
            category, created = MerchantCategory.objects.get_or_create(
                name='Technology',
                defaults={'description': 'Technology and software services'}
            )
            
            # Create merchant account
            merchant = Merchant.objects.create(
                user=admin_user,
                business_name='PexiLabs Demo Corp',
                business_email='demo@pexilabs.com',
                business_phone='+1234567890',
                category=category,
                status='approved'
            )
            print(f"✅ Created merchant: {merchant.business_name}")
        else:
            merchant = admin_user.merchant_account
            print(f"✅ Using existing merchant: {merchant.business_name}")
        
    except Exception as e:
        print(f"❌ Error setting up merchant: {e}")
        return False
    
    # Step 2: Ensure USD currency exists
    try:
        usd_currency, created = PreferredCurrency.objects.get_or_create(
            code='USD',
            defaults={
                'name': 'US Dollar',
                'symbol': '$',
                'is_active': True
            }
        )
        print(f"✅ USD currency ready: {usd_currency.name}")
    except Exception as e:
        print(f"❌ Error setting up currency: {e}")
        return False
    
    # Step 3: Create demo transactions
    try:
        print("\n📋 Creating demo transactions...")
        
        # Clear existing demo transactions
        Transaction.objects.filter(description__icontains='Demo').delete()
        
        transactions_data = [
            {
                'amount': Decimal('100.00'),
                'customer_email': 'customer1@example.com',
                'description': 'Demo Payment Transaction #1',
                'status': TransactionStatus.COMPLETED,
                'payment_method': PaymentMethod.CARD
            },
            {
                'amount': Decimal('250.50'),
                'customer_email': 'customer2@example.com',
                'description': 'Demo Payment Transaction #2',
                'status': TransactionStatus.PENDING,
                'payment_method': PaymentMethod.BANK_TRANSFER
            },
            {
                'amount': Decimal('75.00'),
                'customer_email': 'customer3@example.com',
                'description': 'Demo Payment Transaction #3',
                'status': TransactionStatus.COMPLETED,
                'payment_method': PaymentMethod.MOBILE_MONEY
            },
            {
                'amount': Decimal('500.00'),
                'customer_email': 'customer4@example.com',
                'description': 'Demo Payment Transaction #4',
                'status': TransactionStatus.FAILED,
                'payment_method': PaymentMethod.CARD,
                'failure_reason': 'Insufficient funds'
            }
        ]
        
        created_transactions = []
        for data in transactions_data:
            reference = f"DEMO_{uuid.uuid4().hex[:8].upper()}"
            
            transaction = Transaction.objects.create(
                merchant=merchant,
                reference=reference,
                transaction_type=TransactionType.PAYMENT,
                payment_method=data['payment_method'],
                amount=data['amount'],
                currency=usd_currency,
                customer_email=data['customer_email'],
                description=data['description'],
                status=data['status'],
                net_amount=data['amount'],
                failure_reason=data.get('failure_reason', ''),
                created_at=timezone.now() - timedelta(days=len(created_transactions))
            )
            
            # Set processed/completed dates for completed transactions
            if data['status'] == TransactionStatus.COMPLETED:
                transaction.processed_at = transaction.created_at + timedelta(minutes=5)
                transaction.completed_at = transaction.created_at + timedelta(minutes=10)
                transaction.save()
            
            created_transactions.append(transaction)
            print(f"   ✅ {transaction.reference}: {data['description']}")
        
        print(f"\n✅ Created {len(created_transactions)} demo transactions")
        
    except Exception as e:
        print(f"❌ Error creating transactions: {e}")
        return False
    
    # Step 4: Create demo payment links
    try:
        print("\n🔗 Creating demo payment links...")
        
        # Clear existing demo payment links
        PaymentLink.objects.filter(title__icontains='Demo').delete()
        
        payment_links_data = [
            {
                'title': 'Demo Product Purchase',
                'description': 'Payment for demo product',
                'amount': Decimal('99.99'),
                'is_active': True
            },
            {
                'title': 'Demo Service Payment',
                'description': 'Payment for consulting services',
                'amount': Decimal('299.00'),
                'is_active': True,
                'expires_at': timezone.now() + timedelta(days=30)
            }
        ]
        
        created_links = []
        for data in payment_links_data:
            slug = f"demo-{uuid.uuid4().hex[:8]}"
            
            payment_link = PaymentLink.objects.create(
                merchant=merchant,
                title=data['title'],
                description=data['description'],
                amount=data['amount'],
                currency=usd_currency,
                slug=slug,
                is_active=data['is_active'],
                expires_at=data.get('expires_at'),
                created_at=timezone.now() - timedelta(days=len(created_links))
            )
            
            created_links.append(payment_link)
            print(f"   ✅ {payment_link.title}: /pay/{slug}/")
        
        print(f"\n✅ Created {len(created_links)} demo payment links")
        
    except Exception as e:
        print(f"❌ Error creating payment links: {e}")
        return False
    
    # Step 5: Summary
    print("\n📊 DEMO DATA SUMMARY:")
    print(f"   • Merchant: {merchant.business_name}")
    print(f"   • Total Transactions: {Transaction.objects.filter(merchant=merchant).count()}")
    print(f"   • Completed Transactions: {Transaction.objects.filter(merchant=merchant, status=TransactionStatus.COMPLETED).count()}")
    print(f"   • Total Payment Links: {PaymentLink.objects.filter(merchant=merchant).count()}")
    print(f"   • Total Volume: ${Transaction.objects.filter(merchant=merchant, status=TransactionStatus.COMPLETED).aggregate(total=django.db.models.Sum('amount'))['total'] or 0}")
    
    print("\n🎉 Demo data created successfully!")
    print("\nTo test the system:")
    print("1. Login with admin@pexilabs.com / admin123")
    print("2. Visit the merchant dashboard")
    print("3. Go to the transactions page")
    print("4. Create new transactions and payment links")
    
    return True

if __name__ == '__main__':
    try:
        import django.db.models
        success = create_demo_data()
        if success:
            print("\n✅ Demo data setup completed!")
        else:
            print("\n❌ Demo data setup failed!")
            sys.exit(1)
    except Exception as e:
        print(f"\n💥 Setup failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
