"""
Management command to set up and test all payment integrations
"""

from django.core.management.base import BaseCommand
from django.conf import settings
from integrations.services import UBABankService, CyberSourceService, CorefyService
from integrations.models import (
    Integration, 
    IntegrationProvider, 
    IntegrationStatus, 
    IntegrationType,
    AuthenticationType
)
from authentication.models import Merchant
import logging
import json

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Set up and test all payment integrations (UBA, CyberSource, Corefy)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--test-connections',
            action='store_true',
            help='Test connections to all integration APIs',
        )
        parser.add_argument(
            '--update-status',
            action='store_true',
            help='Update integration status based on health checks',
        )
        parser.add_argument(
            '--show-config',
            action='store_true',
            help='Show current integration configurations',
        )
        parser.add_argument(
            '--create-sample-integrations',
            action='store_true',
            help='Create sample integrations with provider configurations',
        )
        parser.add_argument(
            '--setup-providers',
            action='store_true',
            help='Set up provider configurations for existing integrations',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('🚀 Payment Integrations Setup and Test')
        )
        self.stdout.write('=' * 60)

        # Get test merchant
        merchant = Merchant.objects.first()
        if not merchant:
            self.stdout.write(
                self.style.ERROR('❌ No merchants found. Please create a merchant first.')
            )
            return

        self.stdout.write(f'📊 Using test merchant: {merchant.business_name}')

        # Initialize all services
        services = {
            'UBA Bank': UBABankService(merchant=merchant),
            'CyberSource': CyberSourceService(merchant=merchant),
            'Corefy': CorefyService(merchant=merchant)
        }

        # Show configurations if requested
        if options['show_config']:
            self.show_configurations(services)

        # Test connections if requested
        if options['test_connections']:
            self.test_connections(services)

        # Update status if requested
        if options['update_status']:
            self.update_integration_status(services)

        # Create sample integrations if requested
        if options['create_sample_integrations']:
            self.create_sample_integrations()

        # Set up provider configurations if requested
        if options['setup_providers']:
            self.setup_provider_configurations()

        # Show summary
        self.show_integration_summary()

    def show_configurations(self, services):
        """Show current integration configurations"""
        self.stdout.write('\n📋 Integration Configurations:')
        self.stdout.write('-' * 40)

        for name, service in services.items():
            self.stdout.write(f'\n🔧 {name}:')
            self.stdout.write(f'   Base URL: {service.base_url}')
            self.stdout.write(f'   Status: {service.integration.status}')
            self.stdout.write(f'   Sandbox Mode: {service.integration.is_sandbox}')
            self.stdout.write(f'   Supports Webhooks: {service.integration.supports_webhooks}')
            
            if hasattr(service, 'merchant_id'):
                self.stdout.write(f'   Merchant ID: {service.merchant_id}')
            if hasattr(service, 'api_key') and service.api_key:
                masked_key = service.api_key[:8] + '...' + service.api_key[-4:] if len(service.api_key) > 12 else '***'
                self.stdout.write(f'   API Key: {masked_key}')

    def test_connections(self, services):
        """Test connections to all integration APIs"""
        self.stdout.write('\n🔍 Testing Integration Connections:')
        self.stdout.write('-' * 40)

        for name, service in services.items():
            self.stdout.write(f'\n🌐 Testing {name}...')
            
            try:
                # Call test_connection method if available
                if hasattr(service, 'test_connection'):
                    result = service.test_connection()
                    if result.get('success', False):
                        self.stdout.write(
                            self.style.SUCCESS(f'   ✅ Connection successful')
                        )
                        if 'message' in result:
                            self.stdout.write(f'   📝 {result["message"]}')
                    else:
                        self.stdout.write(
                            self.style.ERROR(f'   ❌ Connection failed: {result.get("error", "Unknown error")}')
                        )
                else:
                    self.stdout.write(
                        self.style.WARNING(f'   ⚠️  No test_connection method available')
                    )
                    
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'   ❌ Connection test error: {str(e)}')
                )

    def update_integration_status(self, services):
        """Update integration status based on health checks"""
        self.stdout.write('\n🔄 Updating Integration Status:')
        self.stdout.write('-' * 40)

        for name, service in services.items():
            try:
                integration = service.integration
                
                # Perform health check if method exists
                if hasattr(service, 'test_connection'):
                    result = service.test_connection()
                    is_healthy = result.get('success', False)
                    
                    integration.is_healthy = is_healthy
                    integration.status = IntegrationStatus.ACTIVE if is_healthy else IntegrationStatus.ERROR
                    integration.health_error_message = result.get('error', '') if not is_healthy else ''
                    integration.save()
                    
                    status_icon = '✅' if is_healthy else '❌'
                    status_text = 'ACTIVE' if is_healthy else 'ERROR'
                    self.stdout.write(f'   {status_icon} {name}: {status_text}')
                else:
                    self.stdout.write(f'   ⚠️  {name}: No health check available')
                    
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'   ❌ {name}: Update failed - {str(e)}')
                )

    def create_sample_integrations(self):
        """Create sample integrations with provider configurations"""
        self.stdout.write('\n🏗️  Creating Sample Integrations:')
        self.stdout.write('-' * 40)
        
        sample_integrations = [
            {
                'name': 'UBA Kenya Pay',
                'code': 'uba_kenya_pay',
                'provider_name': 'United Bank for Africa',
                'integration_type': IntegrationType.UBA_BANK,
                'description': 'UBA Kenya payment gateway integration',
                'base_url': 'https://api.uba.co.ke',
                'authentication_type': AuthenticationType.API_KEY,
                'supports_webhooks': True,
                'provider_config': {
                    'supported_operations': [
                        'payment_page', 'account_inquiry', 'fund_transfer',
                        'balance_inquiry', 'transaction_history', 'bill_payment'
                    ],
                    'endpoints': {
                        'payment_page': '/api/v1/payment/create',
                        'account_inquiry': '/api/v1/account/inquiry',
                        'fund_transfer': '/api/v1/transfer',
                        'balance_inquiry': '/api/v1/balance',
                        'transaction_history': '/api/v1/transactions',
                        'bill_payment': '/api/v1/bills/pay'
                    },
                    'fee_structure': {
                        'fund_transfer': {'fixed': '50.00', 'percentage': '0.5'},
                        'bill_payment': {'fixed': '25.00', 'percentage': '0.0'},
                        'account_inquiry': {'fixed': '10.00', 'percentage': '0.0'}
                    },
                    'limits': {
                        'min_transfer': '100.00',
                        'max_transfer': '1000000.00',
                        'daily_limit': '5000000.00'
                    },
                    'webhook_config': {
                        'events': ['payment.completed', 'payment.failed', 'transfer.completed'],
                        'signature_method': 'hmac_sha256'
                    }
                }
            },
            {
                'name': 'CyberSource Payment Gateway',
                'code': 'cybersource_gateway',
                'provider_name': 'Visa CyberSource',
                'integration_type': IntegrationType.CYBERSOURCE,
                'description': 'CyberSource payment processing platform',
                'base_url': 'https://apitest.cybersource.com',
                'authentication_type': AuthenticationType.JWT,
                'supports_webhooks': True,
                'provider_config': {
                    'supported_operations': [
                        'payment', 'capture', 'refund', 'void',
                        'customer_create', 'token_create'
                    ],
                    'endpoints': {
                        'payment': '/pts/v2/payments',
                        'capture': '/pts/v2/captures',
                        'refund': '/pts/v2/refunds',
                        'void': '/pts/v2/voids',
                        'customer': '/tms/v2/customers',
                        'token': '/tms/v2/tokens'
                    },
                    'fee_structure': {
                        'payment': {'fixed': '0.00', 'percentage': '2.9'},
                        'refund': {'fixed': '0.00', 'percentage': '0.0'}
                    },
                    'limits': {
                        'min_amount': '1.00',
                        'max_amount': '999999.99'
                    },
                    'webhook_config': {
                        'events': ['payment.authorized', 'payment.captured', 'payment.declined'],
                        'signature_method': 'rsa_sha256'
                    }
                }
            },
            {
                'name': 'Corefy Payment Platform',
                'code': 'corefy_platform',
                'provider_name': 'Corefy',
                'integration_type': IntegrationType.COREFY,
                'description': 'Corefy unified payment platform',
                'base_url': 'https://api.corefy.com',
                'authentication_type': AuthenticationType.BEARER_TOKEN,
                'supports_webhooks': True,
                'provider_config': {
                    'supported_operations': [
                        'payment_intent', 'confirm_payment', 'refund',
                        'customer_create', 'payment_method_create'
                    ],
                    'endpoints': {
                        'payment_intent': '/v1/payment-intents',
                        'confirm_payment': '/v1/payment-intents/{id}/confirm',
                        'refund': '/v1/refunds',
                        'customer': '/v1/customers',
                        'payment_method': '/v1/payment-methods'
                    },
                    'fee_structure': {
                        'payment': {'fixed': '0.00', 'percentage': '2.5'},
                        'refund': {'fixed': '0.00', 'percentage': '0.0'}
                    },
                    'limits': {
                        'min_amount': '0.50',
                        'max_amount': '500000.00'
                    },
                    'webhook_config': {
                        'events': ['payment.succeeded', 'payment.failed', 'refund.succeeded'],
                        'signature_method': 'hmac_sha256'
                    }
                }
            }
        ]
        
        for integration_data in sample_integrations:
            provider_config = integration_data.pop('provider_config')
            
            # Create or update integration
            integration, created = Integration.objects.get_or_create(
                code=integration_data['code'],
                defaults={
                    **integration_data,
                    'status': IntegrationStatus.ACTIVE,
                    'is_global': True,
                    'is_sandbox': True
                }
            )
            
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'   ✅ Created integration: {integration.name}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'   ⚠️  Integration already exists: {integration.name}')
                )
            
            # Create or update provider configuration
            provider, provider_created = IntegrationProvider.objects.get_or_create(
                integration=integration,
                defaults={
                    'supported_operations': provider_config['supported_operations'],
                    'endpoints': provider_config['endpoints'],
                    'fee_structure': provider_config['fee_structure'],
                    'limits': provider_config['limits'],
                    'webhook_config': provider_config['webhook_config'],
                    'sandbox_config': {
                        'test_mode': True,
                        'debug_logging': True
                    },
                    'production_config': {
                        'test_mode': False,
                        'debug_logging': False
                    }
                }
            )
            
            if provider_created:
                self.stdout.write(
                    self.style.SUCCESS(f'   ✅ Created provider config for: {integration.name}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'   ⚠️  Provider config already exists for: {integration.name}')
                )
    
    def setup_provider_configurations(self):
        """Set up provider configurations for existing integrations"""
        self.stdout.write('\n⚙️  Setting up Provider Configurations:')
        self.stdout.write('-' * 40)
        
        # Get all integrations without provider configurations
        integrations_without_config = Integration.objects.filter(
            provider_config__isnull=True
        )
        
        if not integrations_without_config.exists():
            self.stdout.write(
                self.style.SUCCESS('   ✅ All integrations already have provider configurations')
            )
            return
        
        for integration in integrations_without_config:
            # Create basic provider configuration based on integration type
            basic_config = self.get_basic_provider_config(integration.integration_type)
            
            provider = IntegrationProvider.objects.create(
                integration=integration,
                **basic_config
            )
            
            self.stdout.write(
                self.style.SUCCESS(f'   ✅ Created basic config for: {integration.name}')
            )
    
    def get_basic_provider_config(self, integration_type):
        """Get basic provider configuration based on integration type"""
        base_config = {
            'supported_operations': [],
            'endpoints': {},
            'fee_structure': {},
            'limits': {},
            'webhook_config': {},
            'sandbox_config': {'test_mode': True},
            'production_config': {'test_mode': False}
        }
        
        if integration_type == IntegrationType.BANK or integration_type == IntegrationType.UBA_BANK:
            base_config.update({
                'supported_operations': ['account_inquiry', 'balance_inquiry', 'fund_transfer'],
                'endpoints': {
                    'account_inquiry': '/api/v1/account/inquiry',
                    'balance_inquiry': '/api/v1/balance',
                    'fund_transfer': '/api/v1/transfer'
                },
                'fee_structure': {
                    'fund_transfer': {'fixed': '0.00', 'percentage': '0.5'}
                },
                'limits': {
                    'min_transfer': '1.00',
                    'max_transfer': '1000000.00'
                }
            })
        elif integration_type == IntegrationType.PAYMENT_GATEWAY or integration_type == IntegrationType.CYBERSOURCE:
            base_config.update({
                'supported_operations': ['payment', 'refund', 'capture'],
                'endpoints': {
                    'payment': '/api/v1/payments',
                    'refund': '/api/v1/refunds',
                    'capture': '/api/v1/captures'
                },
                'fee_structure': {
                    'payment': {'fixed': '0.00', 'percentage': '2.9'}
                },
                'limits': {
                    'min_amount': '1.00',
                    'max_amount': '999999.99'
                }
            })
        
        return base_config

    def show_integration_summary(self):
        """Show summary of all integrations"""
        self.stdout.write('\n📊 Integration Summary:')
        self.stdout.write('-' * 40)

        integrations = Integration.objects.filter(
            code__in=['uba_kenya', 'cybersource', 'corefy']
        )

        for integration in integrations:
            status_icon = '✅' if integration.is_healthy else '❌'
            self.stdout.write(
                f'{status_icon} {integration.provider_name} - {integration.name}'
            )
            self.stdout.write(f'   Status: {integration.get_status_display()}')
            self.stdout.write(f'   Healthy: {integration.is_healthy}')
            if integration.health_error_message:
                self.stdout.write(f'   Error: {integration.health_error_message}')

        self.stdout.write('\n🎉 Integration setup and testing complete!')
        self.stdout.write(
            '\n💡 Usage examples:'
        )
        self.stdout.write('   python manage.py setup_integrations --show-config')
        self.stdout.write('   python manage.py setup_integrations --test-connections')
        self.stdout.write('   python manage.py setup_integrations --update-status')
