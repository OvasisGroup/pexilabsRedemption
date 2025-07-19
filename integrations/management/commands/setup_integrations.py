"""
Management command to set up and test all payment integrations
"""

from django.core.management.base import BaseCommand
from django.conf import settings
from integrations.services import UBABankService, CyberSourceService, CorefyService
from integrations.models import Integration, IntegrationStatus
from authentication.models import Merchant
import logging

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
