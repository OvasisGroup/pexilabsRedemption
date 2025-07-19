"""
Django management command to demonstrate and test merchant auto-creation signals

Usage:
    python manage.py demo_merchant_signals --help
    python manage.py demo_merchant_signals --create-test-user
    python manage.py demo_merchant_signals --verify-user user@example.com
    python manage.py demo_merchant_signals --list-merchants
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from authentication.models import CustomUser, Merchant, MerchantCategory, Country, PreferredCurrency
from django.utils import timezone
import uuid


class Command(BaseCommand):
    help = 'Demonstrate and test merchant auto-creation signals'

    def add_arguments(self, parser):
        parser.add_argument(
            '--create-test-user',
            action='store_true',
            help='Create a test user to demonstrate the signal functionality',
        )
        parser.add_argument(
            '--verify-user',
            type=str,
            help='Verify a user by email (will trigger merchant account creation)',
        )
        parser.add_argument(
            '--list-merchants',
            action='store_true',
            help='List all merchant accounts and their associated users',
        )
        parser.add_argument(
            '--cleanup-test-data',
            action='store_true',
            help='Clean up test data created by this command',
        )
        parser.add_argument(
            '--test-email',
            type=str,
            help='Test welcome email sending for a merchant account by merchant ID',
        )

    def handle(self, *args, **options):
        if options['create_test_user']:
            self.create_test_user()
        elif options['verify_user']:
            self.verify_user(options['verify_user'])
        elif options['list_merchants']:
            self.list_merchants()
        elif options['test_email']:
            self.test_email_sending(options['test_email'])
        elif options['cleanup_test_data']:
            self.cleanup_test_data()
        else:
            self.stdout.write(
                self.style.WARNING(
                    'Please specify an action. Use --help for available options.'
                )
            )

    def test_email_sending(self, merchant_id):
        """Test welcome email sending for a specific merchant"""
        self.stdout.write(f"📧 Testing email sending for merchant: {merchant_id}")
        
        try:
            merchant = Merchant.objects.get(id=merchant_id)
            
            self.stdout.write(f"✅ Found merchant: {merchant.business_name}")
            self.stdout.write(f"   👤 User: {merchant.user.get_full_name()} ({merchant.user.email})")
            self.stdout.write(f"   📧 Business Email: {merchant.business_email}")
            
            # Import the email function
            from authentication.signals import send_merchant_welcome_email
            
            # Send the email
            self.stdout.write("\n📤 Sending welcome email...")
            send_merchant_welcome_email(merchant)
            
            self.stdout.write(self.style.SUCCESS("✅ Welcome email sent successfully!"))
            self.stdout.write(f"   📧 Email sent to: {merchant.business_email}")
            self.stdout.write("\n💡 Check your email server logs or inbox for delivery confirmation.")
            
        except Merchant.DoesNotExist:
            raise CommandError(f'Merchant with ID "{merchant_id}" does not exist.')
        except Exception as e:
            raise CommandError(f'Failed to send email: {e}')

    def create_test_user(self):
        """Create a test user to demonstrate signal functionality"""
        self.stdout.write("🧪 Creating test user for signal demonstration...")
        
        # Generate unique email
        test_email = f'signal.test.{uuid.uuid4().hex[:8]}@example.com'
        
        try:
            # Ensure reference data exists
            country, _ = Country.objects.get_or_create(
                code='US',
                defaults={'name': 'United States', 'phone_code': '+1'}
            )
            
            currency, _ = PreferredCurrency.objects.get_or_create(
                code='USD',
                defaults={'name': 'US Dollar', 'symbol': '$'}
            )
            
            category, _ = MerchantCategory.objects.get_or_create(
                code='general',
                defaults={'name': 'General Business'}
            )
            
            # Create unverified user
            user = CustomUser.objects.create_user(
                email=test_email,
                password='testpass123',
                first_name='Signal',
                last_name='Test',
                phone_number='+1555000123',
                country=country,
                preferred_currency=currency,
                is_verified=False  # Start unverified
            )
            
            self.stdout.write(
                self.style.SUCCESS(f'✅ Created test user: {user.email}')
            )
            self.stdout.write(f"   📧 Email: {user.email}")
            self.stdout.write(f"   👤 Name: {user.get_full_name()}")
            self.stdout.write(f"   ✅ Verified: {user.is_verified}")
            
            # Check if merchant account exists (should be None)
            if hasattr(user, 'merchant_account'):
                self.stdout.write(
                    self.style.WARNING("⚠️  Merchant account already exists (unexpected)")
                )
            else:
                self.stdout.write("✅ No merchant account yet (as expected)")
            
            self.stdout.write("\n💡 Next steps:")
            self.stdout.write(f"   1. Verify the user: python manage.py demo_merchant_signals --verify-user {user.email}")
            self.stdout.write("   2. List merchants: python manage.py demo_merchant_signals --list-merchants")
            
        except Exception as e:
            raise CommandError(f'Failed to create test user: {e}')

    def verify_user(self, email):
        """Verify a user by email (triggers merchant account creation)"""
        self.stdout.write(f"🔐 Verifying user: {email}")
        
        try:
            user = CustomUser.objects.get(email=email)
            
            self.stdout.write(f"✅ Found user: {user.get_full_name()}")
            self.stdout.write(f"   📧 Email: {user.email}")
            self.stdout.write(f"   ✅ Current verification status: {user.is_verified}")
            
            # Check current merchant status
            if hasattr(user, 'merchant_account'):
                self.stdout.write(f"   🏢 Merchant account: EXISTS (ID: {user.merchant_account.id})")
            else:
                self.stdout.write("   🏢 Merchant account: NONE")
            
            if user.is_verified:
                self.stdout.write(
                    self.style.WARNING("⚠️  User is already verified. No change will occur.")
                )
                return
            
            # Verify the user (this triggers the signal)
            self.stdout.write("\n🔄 Setting user verification to True...")
            user.is_verified = True
            user.save()
            
            # Refresh and check results
            user.refresh_from_db()
            
            self.stdout.write(self.style.SUCCESS("✅ User verification completed!"))
            self.stdout.write(f"   ✅ Verification status: {user.is_verified}")
            
            # Check if merchant account was created
            if hasattr(user, 'merchant_account'):
                merchant = user.merchant_account
                self.stdout.write(self.style.SUCCESS("🎉 Merchant account auto-created by signal!"))
                self.stdout.write(f"   📊 Merchant ID: {merchant.id}")
                self.stdout.write(f"   🏢 Business Name: {merchant.business_name}")
                self.stdout.write(f"   📧 Business Email: {merchant.business_email}")
                self.stdout.write(f"   📱 Business Phone: {merchant.business_phone}")
                self.stdout.write(f"   📂 Category: {merchant.category.name if merchant.category else 'None'}")
                self.stdout.write(f"   🔍 Status: {merchant.status}")
                self.stdout.write(f"   ✅ Is Verified: {merchant.is_verified}")
                self.stdout.write(f"   📅 Created: {merchant.created_at}")
            else:
                self.stdout.write(
                    self.style.ERROR("❌ No merchant account was created (signal may not be working)")
                )
            
        except CustomUser.DoesNotExist:
            raise CommandError(f'User with email "{email}" does not exist.')
        except Exception as e:
            raise CommandError(f'Failed to verify user: {e}')

    def list_merchants(self):
        """List all merchant accounts and their users"""
        self.stdout.write("📋 Listing all merchant accounts...")
        
        merchants = Merchant.objects.select_related('user', 'category').order_by('-created_at')
        
        if not merchants:
            self.stdout.write(self.style.WARNING("No merchant accounts found."))
            return
        
        self.stdout.write(f"\n📊 Found {merchants.count()} merchant account(s):\n")
        
        for i, merchant in enumerate(merchants, 1):
            self.stdout.write(f"🏢 Merchant #{i}")
            self.stdout.write(f"   📊 ID: {merchant.id}")
            self.stdout.write(f"   🏢 Business Name: {merchant.business_name}")
            self.stdout.write(f"   👤 User: {merchant.user.get_full_name()} ({merchant.user.email})")
            self.stdout.write(f"   📧 Business Email: {merchant.business_email}")
            self.stdout.write(f"   📱 Business Phone: {merchant.business_phone}")
            self.stdout.write(f"   📂 Category: {merchant.category.name if merchant.category else 'None'}")
            self.stdout.write(f"   🔍 Status: {merchant.status}")
            self.stdout.write(f"   ✅ User Verified: {merchant.user.is_verified}")
            self.stdout.write(f"   ✅ Merchant Verified: {merchant.is_verified}")
            self.stdout.write(f"   📅 Created: {merchant.created_at}")
            self.stdout.write("")

    def cleanup_test_data(self):
        """Clean up test data created by this command"""
        self.stdout.write("🧹 Cleaning up test data...")
        
        # Find test users (those with emails containing 'signal.test')
        test_users = CustomUser.objects.filter(email__contains='signal.test')
        
        if not test_users:
            self.stdout.write(self.style.WARNING("No test data found to clean up."))
            return
        
        merchant_count = 0
        user_emails = []
        
        for user in test_users:
            user_emails.append(user.email)
            if hasattr(user, 'merchant_account'):
                merchant_count += 1
        
        user_count = test_users.count()
        
        # Confirm deletion
        self.stdout.write(f"Found {user_count} test user(s) and {merchant_count} associated merchant account(s):")
        for email in user_emails:
            self.stdout.write(f"   - {email}")
        
        confirm = input("\nAre you sure you want to delete this test data? [y/N]: ")
        
        if confirm.lower() in ['y', 'yes']:
            test_users.delete()
            self.stdout.write(
                self.style.SUCCESS(f"✅ Deleted {user_count} test users and {merchant_count} merchant accounts")
            )
        else:
            self.stdout.write("❌ Cleanup cancelled")
