#!/usr/bin/env python3
"""
Management command to validate and check integration requirements

This command validates:
1. UBA Bank Integration Configuration
2. CyberSource Payment Gateway Configuration  
3. Corefy Payment Platform Configuration
4. Integration Feature Flags
5. Global Integration Settings
6. API connectivity and health checks

Usage:
    python manage.py validate_integrations
    python manage.py validate_integrations --check-connectivity
    python manage.py validate_integrations --fix-issues
    python manage.py validate_integrations --show-config
"""

import os
import json
import requests
from decimal import Decimal
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.utils import timezone
from django.db import transaction

from integrations.models import (
    Integration,
    MerchantIntegration,
    BankIntegration,
    IntegrationProvider,
    IntegrationStatus,
    IntegrationType,
    AuthenticationType
)
from integrations.services import (
    UBABankService,
    UBAAPIException,
    CyberSourceService,
    CyberSourceAPIException,
    CorefyService,
    CorefyAPIException
)
from authentication.models import Merchant


class IntegrationValidator:
    """Validator class for integration configurations"""
    
    def __init__(self, stdout=None):
        self.stdout = stdout
        self.errors = []
        self.warnings = []
        self.success_count = 0
        self.total_checks = 0
        
    def log(self, message: str, level: str = 'INFO'):
        """Log message with level"""
        if self.stdout:
            if level == 'ERROR':
                self.stdout.write(f"❌ {message}")
            elif level == 'WARNING':
                self.stdout.write(f"⚠️  {message}")
            elif level == 'SUCCESS':
                self.stdout.write(f"✅ {message}")
            else:
                self.stdout.write(f"ℹ️  {message}")
    
    def check_setting(self, setting_name: str, expected_type: type = str, required: bool = True) -> Tuple[bool, Any]:
        """Check if a setting exists and has the correct type"""
        self.total_checks += 1
        
        if not hasattr(settings, setting_name):
            if required:
                self.errors.append(f"Missing required setting: {setting_name}")
                self.log(f"Missing required setting: {setting_name}", 'ERROR')
                return False, None
            else:
                self.warnings.append(f"Optional setting not found: {setting_name}")
                self.log(f"Optional setting not found: {setting_name}", 'WARNING')
                return False, None
        
        value = getattr(settings, setting_name)
        
        if expected_type == bool:
            # Handle boolean settings that might be strings
            if isinstance(value, str):
                value = value.lower() == 'true'
            elif not isinstance(value, bool):
                self.errors.append(f"Setting {setting_name} should be boolean, got {type(value).__name__}")
                self.log(f"Setting {setting_name} should be boolean, got {type(value).__name__}", 'ERROR')
                return False, value
        elif not isinstance(value, expected_type):
            self.errors.append(f"Setting {setting_name} should be {expected_type.__name__}, got {type(value).__name__}")
            self.log(f"Setting {setting_name} should be {expected_type.__name__}, got {type(value).__name__}", 'ERROR')
            return False, value
        
        self.success_count += 1
        self.log(f"Setting {setting_name}: ✓", 'SUCCESS')
        return True, value
    
    def validate_uba_configuration(self) -> bool:
        """Validate UBA Bank Integration Configuration"""
        self.log("\n🏦 Validating UBA Bank Integration Configuration", 'INFO')
        self.log("-" * 50, 'INFO')
        
        uba_valid = True
        
        # Required UBA settings
        uba_settings = [
            ('UBA_BASE_URL', str, True),
            ('UBA_ACCESS_TOKEN', str, True),
            ('UBA_CONFIGURATION_TEMPLATE_ID', str, True),
            ('UBA_CUSTOMIZATION_TEMPLATE_ID', str, True),
            ('UBA_WEBHOOK_SECRET', str, True),
            ('UBA_TIMEOUT_SECONDS', int, True),
            ('UBA_RETRY_COUNT', int, True),
            ('UBA_RATE_LIMIT_PER_MINUTE', int, True),
            ('UBA_SANDBOX_MODE', bool, True),
        ]
        
        for setting_name, expected_type, required in uba_settings:
            valid, value = self.check_setting(setting_name, expected_type, required)
            if not valid:
                uba_valid = False
            else:
                # Additional validation for specific settings
                if setting_name == 'UBA_BASE_URL' and value:
                    if not value.startswith(('http://', 'https://')):
                        self.errors.append(f"UBA_BASE_URL should start with http:// or https://")
                        self.log(f"UBA_BASE_URL should start with http:// or https://", 'ERROR')
                        uba_valid = False
                elif setting_name == 'UBA_TIMEOUT_SECONDS' and value:
                    if value < 5 or value > 120:
                        self.warnings.append(f"UBA_TIMEOUT_SECONDS ({value}) should be between 5-120 seconds")
                        self.log(f"UBA_TIMEOUT_SECONDS ({value}) should be between 5-120 seconds", 'WARNING')
                elif setting_name == 'UBA_RATE_LIMIT_PER_MINUTE' and value:
                    if value < 1 or value > 1000:
                        self.warnings.append(f"UBA_RATE_LIMIT_PER_MINUTE ({value}) seems unusual (1-1000 expected)")
                        self.log(f"UBA_RATE_LIMIT_PER_MINUTE ({value}) seems unusual (1-1000 expected)", 'WARNING')
        
        return uba_valid
    
    def validate_cybersource_configuration(self) -> bool:
        """Validate CyberSource Payment Gateway Configuration"""
        self.log("\n💳 Validating CyberSource Payment Gateway Configuration", 'INFO')
        self.log("-" * 50, 'INFO')
        
        cybersource_valid = True
        
        # Required CyberSource settings
        cybersource_settings = [
            ('CYBERSOURCE_MERCHANT_ID', str, True),
            ('CYBERSOURCE_SHARED_SECRET', str, True),
            ('CYBERSOURCE_API_KEY', str, True),
            ('CYBERSOURCE_BASE_URL', str, True),
            ('CYBERSOURCE_WEBHOOK_SECRET', str, True),
            ('CYBERSOURCE_TIMEOUT_SECONDS', int, True),
            ('CYBERSOURCE_RETRY_COUNT', int, True),
            ('CYBERSOURCE_RATE_LIMIT_PER_MINUTE', int, True),
            ('CYBERSOURCE_SANDBOX_MODE', bool, True),
        ]
        
        for setting_name, expected_type, required in cybersource_settings:
            valid, value = self.check_setting(setting_name, expected_type, required)
            if not valid:
                cybersource_valid = False
            else:
                # Additional validation for specific settings
                if setting_name == 'CYBERSOURCE_BASE_URL' and value:
                    if not value.startswith(('http://', 'https://')):
                        self.errors.append(f"CYBERSOURCE_BASE_URL should start with http:// or https://")
                        self.log(f"CYBERSOURCE_BASE_URL should start with http:// or https://", 'ERROR')
                        cybersource_valid = False
                elif setting_name == 'CYBERSOURCE_MERCHANT_ID' and value:
                    # Validate UUID format
                    try:
                        import uuid
                        uuid.UUID(value)
                    except ValueError:
                        self.errors.append(f"CYBERSOURCE_MERCHANT_ID should be a valid UUID")
                        self.log(f"CYBERSOURCE_MERCHANT_ID should be a valid UUID", 'ERROR')
                        cybersource_valid = False
                elif setting_name == 'CYBERSOURCE_SHARED_SECRET' and value:
                    # Validate base64 format
                    try:
                        import base64
                        base64.b64decode(value)
                    except Exception:
                        self.errors.append(f"CYBERSOURCE_SHARED_SECRET should be base64 encoded")
                        self.log(f"CYBERSOURCE_SHARED_SECRET should be base64 encoded", 'ERROR')
                        cybersource_valid = False
        
        return cybersource_valid
    
    def validate_corefy_configuration(self) -> bool:
        """Validate Corefy Payment Platform Configuration"""
        self.log("\n🔗 Validating Corefy Payment Platform Configuration", 'INFO')
        self.log("-" * 50, 'INFO')
        
        corefy_valid = True
        
        # Required Corefy settings
        corefy_settings = [
            ('COREFY_API_KEY', str, True),
            ('COREFY_SECRET_KEY', str, True),
            ('COREFY_CLIENT_KEY', str, True),
            ('COREFY_BASE_URL', str, True),
            ('COREFY_WEBHOOK_SECRET', str, True),
            ('COREFY_TIMEOUT_SECONDS', int, True),
            ('COREFY_RETRY_COUNT', int, True),
            ('COREFY_RATE_LIMIT_PER_MINUTE', int, True),
            ('COREFY_SANDBOX_MODE', bool, True),
        ]
        
        for setting_name, expected_type, required in corefy_settings:
            valid, value = self.check_setting(setting_name, expected_type, required)
            if not valid:
                corefy_valid = False
            else:
                # Additional validation for specific settings
                if setting_name == 'COREFY_BASE_URL' and value:
                    if not value.startswith(('http://', 'https://')):
                        self.errors.append(f"COREFY_BASE_URL should start with http:// or https://")
                        self.log(f"COREFY_BASE_URL should start with http:// or https://", 'ERROR')
                        corefy_valid = False
        
        return corefy_valid
    
    def validate_feature_flags(self) -> bool:
        """Validate Integration Feature Flags"""
        self.log("\n🚩 Validating Integration Feature Flags", 'INFO')
        self.log("-" * 50, 'INFO')
        
        flags_valid = True
        
        # Feature flag settings
        flag_settings = [
            ('ENABLE_UBA_INTEGRATION', bool, True),
            ('ENABLE_CYBERSOURCE_INTEGRATION', bool, True),
            ('ENABLE_COREFY_INTEGRATION', bool, True),
        ]
        
        for setting_name, expected_type, required in flag_settings:
            valid, value = self.check_setting(setting_name, expected_type, required)
            if not valid:
                flags_valid = False
        
        return flags_valid
    
    def validate_global_settings(self) -> bool:
        """Validate Global Integration Settings"""
        self.log("\n🌐 Validating Global Integration Settings", 'INFO')
        self.log("-" * 50, 'INFO')
        
        global_valid = True
        
        # Global integration settings
        global_settings = [
            ('INTEGRATION_HEALTH_CHECK_INTERVAL', int, True),
            ('INTEGRATION_LOG_REQUESTS', bool, True),
            ('INTEGRATION_LOG_RESPONSES', bool, True),
        ]
        
        for setting_name, expected_type, required in global_settings:
            valid, value = self.check_setting(setting_name, expected_type, required)
            if not valid:
                global_valid = False
            else:
                # Additional validation
                if setting_name == 'INTEGRATION_HEALTH_CHECK_INTERVAL' and value:
                    if value < 60 or value > 3600:
                        self.warnings.append(f"INTEGRATION_HEALTH_CHECK_INTERVAL ({value}) should be between 60-3600 seconds")
                        self.log(f"INTEGRATION_HEALTH_CHECK_INTERVAL ({value}) should be between 60-3600 seconds", 'WARNING')
        
        return global_valid
    
    def check_database_integrations(self) -> bool:
        """Check if integrations exist in database"""
        self.log("\n🗄️  Checking Database Integration Records", 'INFO')
        self.log("-" * 50, 'INFO')
        
        db_valid = True
        
        expected_integrations = [
            ('uba_kenya', 'UBA Kenya Pay', IntegrationType.UBA_BANK),
            ('cybersource', 'CyberSource Payment Gateway', IntegrationType.CYBERSOURCE),
            ('corefy', 'Corefy Payment Orchestration', IntegrationType.COREFY),
        ]
        
        for code, name, integration_type in expected_integrations:
            try:
                integration = Integration.objects.get(code=code)
                self.log(f"Integration '{name}' found in database ✓", 'SUCCESS')
                
                # Check integration status
                if integration.status != IntegrationStatus.ACTIVE:
                    self.warnings.append(f"Integration '{name}' is not active (status: {integration.status})")
                    self.log(f"Integration '{name}' is not active (status: {integration.status})", 'WARNING')
                
                # Check if it's global
                if not integration.is_global:
                    self.warnings.append(f"Integration '{name}' is not set as global")
                    self.log(f"Integration '{name}' is not set as global", 'WARNING')
                    
            except Integration.DoesNotExist:
                self.errors.append(f"Integration '{name}' not found in database")
                self.log(f"Integration '{name}' not found in database", 'ERROR')
                db_valid = False
        
        return db_valid
    
    def test_api_connectivity(self) -> bool:
        """Test API connectivity for all integrations"""
        self.log("\n🔌 Testing API Connectivity", 'INFO')
        self.log("-" * 50, 'INFO')
        
        connectivity_valid = True
        
        # Test UBA connectivity
        if getattr(settings, 'ENABLE_UBA_INTEGRATION', False):
            try:
                uba_service = UBABankService()
                result = uba_service.test_connection()
                if result.get('success'):
                    self.log(f"UBA API connectivity: ✓", 'SUCCESS')
                else:
                    self.warnings.append(f"UBA API connectivity failed: {result.get('message')}")
                    self.log(f"UBA API connectivity failed: {result.get('message')}", 'WARNING')
                    connectivity_valid = False
            except Exception as e:
                self.errors.append(f"UBA API test failed: {str(e)}")
                self.log(f"UBA API test failed: {str(e)}", 'ERROR')
                connectivity_valid = False
        
        # Test CyberSource connectivity
        if getattr(settings, 'ENABLE_CYBERSOURCE_INTEGRATION', False):
            try:
                cybersource_service = CyberSourceService()
                result = cybersource_service.test_connection()
                if result.get('success'):
                    self.log(f"CyberSource API connectivity: ✓", 'SUCCESS')
                else:
                    self.warnings.append(f"CyberSource API connectivity failed: {result.get('message')}")
                    self.log(f"CyberSource API connectivity failed: {result.get('message')}", 'WARNING')
                    connectivity_valid = False
            except Exception as e:
                self.errors.append(f"CyberSource API test failed: {str(e)}")
                self.log(f"CyberSource API test failed: {str(e)}", 'ERROR')
                connectivity_valid = False
        
        # Test Corefy connectivity
        if getattr(settings, 'ENABLE_COREFY_INTEGRATION', False):
            try:
                corefy_service = CorefyService()
                result = corefy_service.test_connection()
                if result.get('success'):
                    self.log(f"Corefy API connectivity: ✓", 'SUCCESS')
                else:
                    self.warnings.append(f"Corefy API connectivity failed: {result.get('message')}")
                    self.log(f"Corefy API connectivity failed: {result.get('message')}", 'WARNING')
                    connectivity_valid = False
            except Exception as e:
                self.errors.append(f"Corefy API test failed: {str(e)}")
                self.log(f"Corefy API test failed: {str(e)}", 'ERROR')
                connectivity_valid = False
        
        return connectivity_valid
    
    def show_configuration_summary(self):
        """Show current configuration summary"""
        self.log("\n📋 Current Integration Configuration Summary", 'INFO')
        self.log("=" * 60, 'INFO')
        
        # UBA Configuration
        self.log("\n🏦 UBA Bank Integration:", 'INFO')
        uba_config = {
            'Base URL': getattr(settings, 'UBA_BASE_URL', 'Not set'),
            'Sandbox Mode': getattr(settings, 'UBA_SANDBOX_MODE', 'Not set'),
            'Rate Limit/min': getattr(settings, 'UBA_RATE_LIMIT_PER_MINUTE', 'Not set'),
            'Timeout (sec)': getattr(settings, 'UBA_TIMEOUT_SECONDS', 'Not set'),
            'Enabled': getattr(settings, 'ENABLE_UBA_INTEGRATION', 'Not set'),
        }
        for key, value in uba_config.items():
            self.log(f"  {key}: {value}", 'INFO')
        
        # CyberSource Configuration
        self.log("\n💳 CyberSource Payment Gateway:", 'INFO')
        cybersource_config = {
            'Base URL': getattr(settings, 'CYBERSOURCE_BASE_URL', 'Not set'),
            'Merchant ID': getattr(settings, 'CYBERSOURCE_MERCHANT_ID', 'Not set')[:20] + '...' if getattr(settings, 'CYBERSOURCE_MERCHANT_ID', '') else 'Not set',
            'Sandbox Mode': getattr(settings, 'CYBERSOURCE_SANDBOX_MODE', 'Not set'),
            'Rate Limit/min': getattr(settings, 'CYBERSOURCE_RATE_LIMIT_PER_MINUTE', 'Not set'),
            'Enabled': getattr(settings, 'ENABLE_CYBERSOURCE_INTEGRATION', 'Not set'),
        }
        for key, value in cybersource_config.items():
            self.log(f"  {key}: {value}", 'INFO')
        
        # Corefy Configuration
        self.log("\n🔗 Corefy Payment Platform:", 'INFO')
        corefy_config = {
            'Base URL': getattr(settings, 'COREFY_BASE_URL', 'Not set'),
            'Sandbox Mode': getattr(settings, 'COREFY_SANDBOX_MODE', 'Not set'),
            'Rate Limit/min': getattr(settings, 'COREFY_RATE_LIMIT_PER_MINUTE', 'Not set'),
            'Enabled': getattr(settings, 'ENABLE_COREFY_INTEGRATION', 'Not set'),
        }
        for key, value in corefy_config.items():
            self.log(f"  {key}: {value}", 'INFO')
        
        # Global Settings
        self.log("\n🌐 Global Integration Settings:", 'INFO')
        global_config = {
            'Health Check Interval': f"{getattr(settings, 'INTEGRATION_HEALTH_CHECK_INTERVAL', 'Not set')} seconds",
            'Log Requests': getattr(settings, 'INTEGRATION_LOG_REQUESTS', 'Not set'),
            'Log Responses': getattr(settings, 'INTEGRATION_LOG_RESPONSES', 'Not set'),
        }
        for key, value in global_config.items():
            self.log(f"  {key}: {value}", 'INFO')
    
    def get_validation_summary(self) -> Dict[str, Any]:
        """Get validation summary"""
        return {
            'total_checks': self.total_checks,
            'successful_checks': self.success_count,
            'errors': self.errors,
            'warnings': self.warnings,
            'success_rate': (self.success_count / self.total_checks * 100) if self.total_checks > 0 else 0
        }


class Command(BaseCommand):
    help = 'Validate integration requirements and configurations'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--check-connectivity',
            action='store_true',
            help='Test API connectivity for all integrations',
        )
        parser.add_argument(
            '--show-config',
            action='store_true',
            help='Show current integration configurations',
        )
        parser.add_argument(
            '--fix-issues',
            action='store_true',
            help='Attempt to fix common integration issues',
        )
        parser.add_argument(
            '--create-missing',
            action='store_true',
            help='Create missing integration records in database',
        )
    
    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('🔍 Integration Requirements Validation')
        )
        self.stdout.write('=' * 60)
        
        validator = IntegrationValidator(stdout=self.stdout)
        
        # Show configuration if requested
        if options['show_config']:
            validator.show_configuration_summary()
            return
        
        # Run all validations
        validations = [
            validator.validate_uba_configuration(),
            validator.validate_cybersource_configuration(),
            validator.validate_corefy_configuration(),
            validator.validate_feature_flags(),
            validator.validate_global_settings(),
            validator.check_database_integrations(),
        ]
        
        # Test connectivity if requested
        if options['check_connectivity']:
            validations.append(validator.test_api_connectivity())
        
        # Create missing integrations if requested
        if options['create_missing']:
            self.create_missing_integrations()
        
        # Fix issues if requested
        if options['fix_issues']:
            self.fix_common_issues(validator)
        
        # Show summary
        self.show_validation_summary(validator)
        
        # Exit with error code if there are errors
        if validator.errors:
            raise CommandError(f"Validation failed with {len(validator.errors)} errors")
    
    def create_missing_integrations(self):
        """Create missing integration records"""
        self.stdout.write("\n🏗️  Creating Missing Integration Records", self.style.HTTP_INFO)
        self.stdout.write("-" * 50)
        
        integrations_to_create = [
            {
                'code': 'uba_kenya',
                'name': 'UBA Kenya Pay',
                'provider_name': 'United Bank for Africa (Kenya)',
                'integration_type': IntegrationType.UBA_BANK,
                'base_url': getattr(settings, 'UBA_BASE_URL', 'https://api-sandbox.ubakenya-pay.com'),
                'is_sandbox': getattr(settings, 'UBA_SANDBOX_MODE', True),
            },
            {
                'code': 'cybersource',
                'name': 'CyberSource Payment Gateway',
                'provider_name': 'Visa CyberSource',
                'integration_type': IntegrationType.CYBERSOURCE,
                'base_url': getattr(settings, 'CYBERSOURCE_BASE_URL', 'https://apitest.cybersource.com'),
                'is_sandbox': getattr(settings, 'CYBERSOURCE_SANDBOX_MODE', True),
            },
            {
                'code': 'corefy',
                'name': 'Corefy Payment Orchestration',
                'provider_name': 'Corefy',
                'integration_type': IntegrationType.COREFY,
                'base_url': getattr(settings, 'COREFY_BASE_URL', 'https://api.sandbox.corefy.com'),
                'is_sandbox': getattr(settings, 'COREFY_SANDBOX_MODE', True),
            },
        ]
        
        for integration_data in integrations_to_create:
            integration, created = Integration.objects.get_or_create(
                code=integration_data['code'],
                defaults={
                    'name': integration_data['name'],
                    'provider_name': integration_data['provider_name'],
                    'integration_type': integration_data['integration_type'],
                    'base_url': integration_data['base_url'],
                    'is_sandbox': integration_data['is_sandbox'],
                    'status': IntegrationStatus.ACTIVE,
                    'is_global': True,
                    'supports_webhooks': True,
                    'authentication_type': AuthenticationType.API_KEY,
                }
            )
            
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f"✅ Created integration: {integration_data['name']}")
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f"⚠️  Integration already exists: {integration_data['name']}")
                )
    
    def fix_common_issues(self, validator: IntegrationValidator):
        """Fix common integration issues"""
        self.stdout.write("\n🔧 Fixing Common Integration Issues", self.style.HTTP_INFO)
        self.stdout.write("-" * 50)
        
        # Update integration statuses
        integrations = Integration.objects.filter(
            code__in=['uba_kenya', 'cybersource', 'corefy']
        )
        
        for integration in integrations:
            if integration.status != IntegrationStatus.ACTIVE:
                integration.status = IntegrationStatus.ACTIVE
                integration.save()
                self.stdout.write(
                    self.style.SUCCESS(f"✅ Updated {integration.name} status to ACTIVE")
                )
            
            if not integration.is_global:
                integration.is_global = True
                integration.save()
                self.stdout.write(
                    self.style.SUCCESS(f"✅ Set {integration.name} as global")
                )
    
    def show_validation_summary(self, validator: IntegrationValidator):
        """Show validation summary"""
        summary = validator.get_validation_summary()
        
        self.stdout.write("\n📊 Validation Summary", self.style.HTTP_INFO)
        self.stdout.write("=" * 60)
        
        self.stdout.write(f"Total Checks: {summary['total_checks']}")
        self.stdout.write(f"Successful: {summary['successful_checks']}")
        self.stdout.write(f"Success Rate: {summary['success_rate']:.1f}%")
        
        if summary['errors']:
            self.stdout.write(f"\n❌ Errors ({len(summary['errors'])}):", self.style.ERROR)
            for error in summary['errors']:
                self.stdout.write(f"  • {error}", self.style.ERROR)
        
        if summary['warnings']:
            self.stdout.write(f"\n⚠️  Warnings ({len(summary['warnings'])}):", self.style.WARNING)
            for warning in summary['warnings']:
                self.stdout.write(f"  • {warning}", self.style.WARNING)
        
        if not summary['errors'] and not summary['warnings']:
            self.stdout.write(
                self.style.SUCCESS("\n🎉 All integration requirements are properly configured!")
            )
        elif not summary['errors']:
            self.stdout.write(
                self.style.SUCCESS("\n✅ All critical requirements are met (some warnings exist)")
            )
        else:
            self.stdout.write(
                self.style.ERROR("\n❌ Integration validation failed - please fix the errors above")
            )