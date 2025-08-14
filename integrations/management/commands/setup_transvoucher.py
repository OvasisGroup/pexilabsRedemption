#!/usr/bin/env python3
"""
TransVoucher Integration Setup Command

This management command sets up the TransVoucher integration with the configuration
from environment variables and creates the necessary database records.

Usage:
    python manage.py setup_transvoucher
    python manage.py setup_transvoucher --test-connection
    python manage.py setup_transvoucher --merchant-id <merchant_id> --api-secret <secret>
"""

import os
import sys
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from integrations.models import (
    Integration,
    MerchantIntegration,
    IntegrationStatus,
    IntegrationType,
    AuthenticationType
)
from integrations.transvoucher.service import TransVoucherService, validate_transvoucher_credentials
from authentication.models import Merchant


class Command(BaseCommand):
    help = 'Setup TransVoucher integration with environment configuration'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--test-connection',
            action='store_true',
            help='Test connection to TransVoucher API after setup'
        )
        parser.add_argument(
            '--merchant-id',
            type=str,
            help='Specific merchant ID to setup TransVoucher integration for'
        )
        parser.add_argument(
            '--api-secret',
            type=str,
            help='API secret for the merchant (required if --merchant-id is provided)'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force update existing integration configuration'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Enable verbose output'
        )
    
    def handle(self, *args, **options):
        self.verbose = options.get('verbose', False)
        
        try:
            # Validate environment configuration
            self.stdout.write(self.style.HTTP_INFO('🔧 Setting up TransVoucher integration...'))
            
            if not self._validate_environment():
                raise CommandError('Environment validation failed')
            
            # Setup global integration
            integration = self._setup_global_integration(force=options.get('force', False))
            
            # Setup merchant-specific integration if requested
            if options.get('merchant_id'):
                if not options.get('api_secret'):
                    raise CommandError('--api-secret is required when --merchant-id is provided')
                
                merchant_integration = self._setup_merchant_integration(
                    merchant_id=options['merchant_id'],
                    api_secret=options['api_secret'],
                    force=options.get('force', False)
                )
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✅ Merchant integration setup completed for merchant {options["merchant_id"]}'
                    )
                )
            
            # Test connection if requested
            if options.get('test_connection'):
                self._test_connection(integration)
            
            self.stdout.write(
                self.style.SUCCESS('🎉 TransVoucher integration setup completed successfully!')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Setup failed: {str(e)}')
            )
            raise CommandError(f'TransVoucher setup failed: {str(e)}')
    
    def _validate_environment(self) -> bool:
        """Validate required environment variables"""
        self.stdout.write('📋 Validating environment configuration...')
        
        required_settings = [
            'TRANSVOUCHER_API_KEY',
            'TRANSVOUCHER_API_BASE_URL'
        ]
        
        missing_settings = []
        for setting in required_settings:
            if not getattr(settings, setting, None):
                missing_settings.append(setting)
        
        if missing_settings:
            self.stdout.write(
                self.style.ERROR(
                    f'❌ Missing required settings: {", ".join(missing_settings)}'
                )
            )
            self.stdout.write('Please add the following to your .env file:')
            for setting in missing_settings:
                if setting == 'TRANSVOUCHER_API_KEY':
                    self.stdout.write(f'{setting}=tv-your-api-key-here')
                elif setting == 'TRANSVOUCHER_API_BASE_URL':
                    self.stdout.write(f'{setting}=https://api.transvoucher.com')
            return False
        
        # Validate API key format
        api_key = getattr(settings, 'TRANSVOUCHER_API_KEY')
        api_secret = getattr(settings, 'TRANSVOUCHER_API_SECRET')
        validation = validate_transvoucher_credentials(api_key, api_secret)
        
        if not validation['valid']:
            self.stdout.write(
                self.style.ERROR(f'❌ Invalid API key: {validation["message"]}')
            )
            return False
        
        # Show current configuration
        if self.verbose:
            self.stdout.write('Current configuration:')
            self.stdout.write(f'  API Key: {api_key[:10]}...')
            self.stdout.write(f'  Base URL: {getattr(settings, "TRANSVOUCHER_API_BASE_URL")}')
            self.stdout.write(f'  Sandbox Mode: {getattr(settings, "TRANSVOUCHER_SANDBOX_MODE", True)}')
        
        self.stdout.write(self.style.SUCCESS('✅ Environment validation passed'))
        return True
    
    def _setup_global_integration(self, force: bool = False) -> Integration:
        """Setup global TransVoucher integration"""
        self.stdout.write('🌐 Setting up global TransVoucher integration...')
        
        try:
            integration = Integration.objects.get(code='transvoucher')
            
            if not force:
                self.stdout.write(
                    self.style.WARNING(
                        '⚠️  TransVoucher integration already exists. Use --force to update.'
                    )
                )
                return integration
            else:
                self.stdout.write('🔄 Updating existing integration...')
        
        except Integration.DoesNotExist:
            self.stdout.write('📝 Creating new integration...')
            integration = None
        
        # Get configuration from settings
        api_key = getattr(settings, 'TRANSVOUCHER_API_KEY')
        api_secret = getattr(settings, 'TRANSVOUCHER_API_SECRET')
        base_url = getattr(settings, 'TRANSVOUCHER_API_BASE_URL')
        is_sandbox = getattr(settings, 'TRANSVOUCHER_SANDBOX_MODE', True)
        
        # Validate credentials
        validation = validate_transvoucher_credentials(api_key, api_secret)
        if not validation['valid']:
            raise CommandError(f'Invalid TransVoucher credentials: {validation["message"]}')
        
        integration_data = {
            'name': 'TransVoucher Payment Gateway',
            'provider_name': 'TransVoucher',
            'description': 'TransVoucher payment processing and voucher services',
            'integration_type': IntegrationType.PAYMENT_GATEWAY,
            'base_url': base_url,
            'is_sandbox': is_sandbox,
            'version': 'v1.0',
            'authentication_type': AuthenticationType.API_KEY,
            'supports_webhooks': True,
            'supports_bulk_operations': False,
            'supports_real_time': True,
            'rate_limit_per_minute': 60,
            'rate_limit_per_hour': 1000,
            'rate_limit_per_day': 10000,
            'status': IntegrationStatus.ACTIVE,
            'is_global': True,
            'provider_website': 'https://transvoucher.com/',
            'provider_documentation': 'https://transvoucher.com/api-documentation',
            'last_health_check': timezone.now(),
            'is_healthy': True
        }
        
        with transaction.atomic():
            if integration:
                # Update existing integration
                for key, value in integration_data.items():
                    setattr(integration, key, value)
                integration.save()
                action = 'updated'
            else:
                # Create new integration
                integration = Integration.objects.create(
                    code='transvoucher',
                    **integration_data
                )
                action = 'created'
        
        self.stdout.write(
            self.style.SUCCESS(f'✅ Global integration {action} successfully')
        )
        
        if self.verbose:
            self.stdout.write(f'  Integration ID: {integration.id}')
            self.stdout.write(f'  Status: {integration.status}')
            self.stdout.write(f'  Sandbox Mode: {integration.is_sandbox}')
        
        return integration
    
    def _setup_merchant_integration(
        self,
        merchant_id: str,
        api_secret: str,
        force: bool = False
    ) -> MerchantIntegration:
        """Setup merchant-specific TransVoucher integration"""
        self.stdout.write(f'🏪 Setting up merchant integration for {merchant_id}...')
        
        try:
            merchant = Merchant.objects.get(id=merchant_id)
        except Merchant.DoesNotExist:
            raise CommandError(f'Merchant with ID {merchant_id} not found')
        
        try:
            integration = Integration.objects.get(code='transvoucher')
        except Integration.DoesNotExist:
            raise CommandError('Global TransVoucher integration not found. Run setup first.')
        
        # Setup merchant integration using the service
        service = TransVoucherService(merchant=merchant)
        
        configuration = {
            'webhook_url': '',  # Can be configured later
            'return_url': '',   # Can be configured later
            'failure_url': '',  # Can be configured later
            'setup_date': timezone.now().isoformat(),
            'setup_method': 'management_command'
        }
        
        merchant_integration = service.setup_merchant_integration(
            merchant=merchant,
            api_secret=api_secret,
            configuration=configuration
        )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'✅ Merchant integration setup for {merchant.business_name or merchant.user.username}'
            )
        )
        
        if self.verbose:
            self.stdout.write(f'  Merchant Integration ID: {merchant_integration.id}')
            self.stdout.write(f'  Status: {merchant_integration.status}')
            self.stdout.write(f'  Enabled: {merchant_integration.is_enabled}')
        
        return merchant_integration
    
    def _test_connection(self, integration: Integration):
        """Test connection to TransVoucher API"""
        self.stdout.write('🔍 Testing connection to TransVoucher API...')
        
        try:
            service = TransVoucherService()
            result = service.test_connection()
            
            if result['success']:
                self.stdout.write(
                    self.style.SUCCESS('✅ Connection test passed')
                )
                if self.verbose and 'response' in result:
                    self.stdout.write(f'  Response: {result["response"]}')
            else:
                self.stdout.write(
                    self.style.ERROR(f'❌ Connection test failed: {result["message"]}')
                )
                if 'status_code' in result:
                    self.stdout.write(f'  Status Code: {result["status_code"]}')
                if 'error_code' in result:
                    self.stdout.write(f'  Error Code: {result["error_code"]}')
        
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Connection test error: {str(e)}')
            )
    
    def _show_summary(self):
        """Show setup summary"""
        self.stdout.write('\n📊 Setup Summary:')
        
        try:
            integration = Integration.objects.get(code='transvoucher')
            self.stdout.write(f'  Global Integration: ✅ {integration.status}')
            
            merchant_count = MerchantIntegration.objects.filter(
                integration=integration,
                is_enabled=True
            ).count()
            
            self.stdout.write(f'  Enabled Merchants: {merchant_count}')
            
        except Integration.DoesNotExist:
            self.stdout.write('  Global Integration: ❌ Not found')
        
        self.stdout.write('\n🔗 Next Steps:')
        self.stdout.write('  1. Configure merchant-specific integrations with API secrets')
        self.stdout.write('  2. Set up webhook URLs for payment notifications')
        self.stdout.write('  3. Test payment flows in sandbox mode')
        self.stdout.write('  4. Switch to production when ready')