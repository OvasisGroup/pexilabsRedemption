"""
Enhanced integration monitoring and health check system
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import models
from datetime import timedelta
from integrations.models import Integration, IntegrationAPICall, IntegrationStatus
from integrations.services import UBABankService, CyberSourceService, CorefyService
from authentication.models import Merchant
import json


class Command(BaseCommand):
    help = 'Monitor integration health and generate status reports'

    def add_arguments(self, parser):
        parser.add_argument(
            '--full-report',
            action='store_true',
            help='Generate full integration status report',
        )
        parser.add_argument(
            '--api-stats',
            action='store_true',
            help='Show API call statistics',
        )
        parser.add_argument(
            '--health-check',
            action='store_true',
            help='Perform health checks for all integrations',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('📊 Integration Monitoring & Status Report')
        )
        self.stdout.write('=' * 60)

        if options['full_report']:
            self.generate_full_report()
            
        if options['api_stats']:
            self.show_api_statistics()
            
        if options['health_check']:
            self.perform_health_checks()
            
        if not any([options['full_report'], options['api_stats'], options['health_check']]):
            self.show_quick_status()

    def generate_full_report(self):
        """Generate a comprehensive integration status report"""
        self.stdout.write('\n📋 Full Integration Status Report')
        self.stdout.write('-' * 40)

        integrations = Integration.objects.filter(
            code__in=['uba_kenya', 'cybersource', 'corefy']
        )

        for integration in integrations:
            self.stdout.write(f'\n🔧 {integration.provider_name}')
            self.stdout.write(f'   Name: {integration.name}')
            self.stdout.write(f'   Code: {integration.code}')
            self.stdout.write(f'   Status: {integration.get_status_display()}')
            self.stdout.write(f'   Type: {integration.get_integration_type_display()}')
            self.stdout.write(f'   Base URL: {integration.base_url}')
            self.stdout.write(f'   Sandbox Mode: {integration.is_sandbox}')
            self.stdout.write(f'   Healthy: {"✅" if integration.is_healthy else "❌"}')
            
            # Rate limiting info
            if integration.rate_limit_per_minute:
                self.stdout.write(f'   Rate Limit: {integration.rate_limit_per_minute}/min')
            
            # Last health check
            if integration.last_health_check:
                self.stdout.write(f'   Last Check: {integration.last_health_check}')
            
            # Error message if any
            if integration.health_error_message:
                self.stdout.write(f'   Error: {integration.health_error_message}')
            
            # Capabilities
            capabilities = []
            if integration.supports_webhooks:
                capabilities.append('Webhooks')
            if integration.supports_bulk_operations:
                capabilities.append('Bulk Ops')
            if integration.supports_real_time:
                capabilities.append('Real-time')
            
            if capabilities:
                self.stdout.write(f'   Capabilities: {", ".join(capabilities)}')

    def show_api_statistics(self):
        """Show API call statistics for all integrations"""
        self.stdout.write('\n📈 API Call Statistics (Last 24 Hours)')
        self.stdout.write('-' * 40)

        # Get API calls from last 24 hours
        since = timezone.now() - timedelta(hours=24)
        api_calls = IntegrationAPICall.objects.filter(
            created_at__gte=since
        )

        if not api_calls.exists():
            self.stdout.write('   No API calls in the last 24 hours')
            return

        # Group by integration
        integrations = ['uba_kenya', 'cybersource', 'corefy']
        
        for integration_code in integrations:
            integration_calls = api_calls.filter(
                integration__code=integration_code
            )
            
            if integration_calls.exists():
                total_calls = integration_calls.count()
                successful_calls = integration_calls.filter(
                    status_code__gte=200,
                    status_code__lt=300
                ).count()
                
                success_rate = (successful_calls / total_calls * 100) if total_calls > 0 else 0
                
                self.stdout.write(f'\n🔌 {integration_code.replace("_", " ").title()}:')
                self.stdout.write(f'   Total Calls: {total_calls}')
                self.stdout.write(f'   Successful: {successful_calls}')
                self.stdout.write(f'   Success Rate: {success_rate:.1f}%')
                
                # Average response time
                avg_response_time = integration_calls.aggregate(
                    avg_time=models.Avg('response_time')
                )['avg_time']
                
                if avg_response_time:
                    self.stdout.write(f'   Avg Response Time: {avg_response_time:.2f}ms')

    def perform_health_checks(self):
        """Perform health checks for all integrations"""
        self.stdout.write('\n🏥 Performing Health Checks')
        self.stdout.write('-' * 40)

        # Get a test merchant
        merchant = Merchant.objects.first()
        if not merchant:
            self.stdout.write(
                self.style.ERROR('❌ No merchants found for testing')
            )
            return

        services = {
            'UBA Bank': UBABankService(merchant=merchant),
            'CyberSource': CyberSourceService(merchant=merchant),
            'Corefy': CorefyService(merchant=merchant)
        }

        health_results = {}

        for name, service in services.items():
            self.stdout.write(f'\n🔍 Testing {name}...')
            
            try:
                if hasattr(service, 'test_connection'):
                    result = service.test_connection()
                    is_healthy = result.get('success', False)
                    error_message = result.get('error', '')
                    
                    # Update integration health status
                    integration = service.integration
                    integration.is_healthy = is_healthy
                    integration.last_health_check = timezone.now()
                    integration.health_error_message = error_message if not is_healthy else ''
                    integration.status = IntegrationStatus.ACTIVE if is_healthy else IntegrationStatus.ERROR
                    integration.save()
                    
                    health_results[name] = is_healthy
                    
                    if is_healthy:
                        self.stdout.write(
                            self.style.SUCCESS(f'   ✅ {name} is healthy')
                        )
                    else:
                        self.stdout.write(
                            self.style.ERROR(f'   ❌ {name} is unhealthy: {error_message}')
                        )
                else:
                    self.stdout.write(
                        self.style.WARNING(f'   ⚠️  {name} has no health check method')
                    )
                    health_results[name] = None
                    
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'   ❌ {name} health check failed: {str(e)}')
                )
                health_results[name] = False

        # Summary
        self.stdout.write('\n📊 Health Check Summary:')
        healthy_count = sum(1 for status in health_results.values() if status is True)
        total_count = len([status for status in health_results.values() if status is not None])
        
        self.stdout.write(f'   Healthy Services: {healthy_count}/{total_count}')
        
        if healthy_count == total_count:
            self.stdout.write(
                self.style.SUCCESS('   🎉 All services are healthy!')
            )
        else:
            self.stdout.write(
                self.style.WARNING('   ⚠️  Some services need attention')
            )

    def show_quick_status(self):
        """Show a quick status overview"""
        self.stdout.write('\n⚡ Quick Status Overview')
        self.stdout.write('-' * 30)

        integrations = Integration.objects.filter(
            code__in=['uba_kenya', 'cybersource', 'corefy']
        )

        for integration in integrations:
            status_icon = '✅' if integration.is_healthy else '❌'
            self.stdout.write(
                f'{status_icon} {integration.provider_name}: {integration.get_status_display()}'
            )

        self.stdout.write('\n💡 Available options:')
        self.stdout.write('   --full-report    Complete integration details')
        self.stdout.write('   --api-stats      API call statistics')
        self.stdout.write('   --health-check   Perform health checks')
