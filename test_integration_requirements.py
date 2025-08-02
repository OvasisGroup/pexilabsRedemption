#!/usr/bin/env python3
"""
Comprehensive Integration Requirements Test Script

This script validates all integration requirements:
1. UBA Bank Integration Configuration
2. CyberSource Payment Gateway Configuration  
3. Corefy Payment Platform Configuration
4. Integration Feature Flags
5. Global Integration Settings
6. API connectivity and health checks
7. Database integration records

Usage:
    python test_integration_requirements.py
    python test_integration_requirements.py --verbose
    python test_integration_requirements.py --test-apis
    python test_integration_requirements.py --fix-issues
"""

import os
import sys
import json
import requests
import argparse
from datetime import datetime
from typing import Dict, List, Tuple, Any
from urllib.parse import urlparse

# Add Django project to path
sys.path.append('/Users/omambia/workspaces/pexi-labs/pexilabsRedemption')

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pexilabs.settings')
import django
django.setup()

from django.conf import settings
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
from authentication.models import Merchant


class Colors:
    """ANSI color codes for terminal output"""
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'


class IntegrationTester:
    """Comprehensive integration requirements tester"""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.errors = []
        self.warnings = []
        self.successes = []
        self.total_checks = 0
        self.passed_checks = 0
        
    def log(self, message: str, level: str = 'INFO', force: bool = False):
        """Log message with color coding"""
        if not self.verbose and not force and level == 'INFO':
            return
            
        timestamp = datetime.now().strftime('%H:%M:%S')
        
        if level == 'ERROR':
            print(f"{Colors.RED}❌ [{timestamp}] {message}{Colors.END}")
        elif level == 'WARNING':
            print(f"{Colors.YELLOW}⚠️  [{timestamp}] {message}{Colors.END}")
        elif level == 'SUCCESS':
            print(f"{Colors.GREEN}✅ [{timestamp}] {message}{Colors.END}")
        elif level == 'INFO':
            print(f"{Colors.CYAN}ℹ️  [{timestamp}] {message}{Colors.END}")
        elif level == 'HEADER':
            print(f"{Colors.BOLD}{Colors.BLUE}{message}{Colors.END}")
        else:
            print(f"[{timestamp}] {message}")
    
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
        
        # Handle boolean settings
        if expected_type == bool:
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
        
        self.passed_checks += 1
        self.successes.append(f"Setting {setting_name}: ✓")
        self.log(f"Setting {setting_name}: ✓", 'SUCCESS')
        return True, value
    
    def test_uba_configuration(self) -> bool:
        """Test UBA Bank Integration Configuration"""
        self.log("\n🏦 Testing UBA Bank Integration Configuration", 'HEADER', True)
        self.log("-" * 50, 'INFO', True)
        
        uba_valid = True
        
        # Required UBA settings with validation
        uba_tests = [
            ('UBA_BASE_URL', str, True, self._validate_url),
            ('UBA_ACCESS_TOKEN', str, True, self._validate_jwt_token),
            ('UBA_CONFIGURATION_TEMPLATE_ID', str, True, self._validate_mongodb_id),
            ('UBA_CUSTOMIZATION_TEMPLATE_ID', str, True, self._validate_mongodb_id),
            ('UBA_WEBHOOK_SECRET', str, True, None),
            ('UBA_TIMEOUT_SECONDS', int, True, lambda x: 5 <= x <= 120),
            ('UBA_RETRY_COUNT', int, True, lambda x: 1 <= x <= 10),
            ('UBA_RATE_LIMIT_PER_MINUTE', int, True, lambda x: 1 <= x <= 1000),
            ('UBA_SANDBOX_MODE', bool, True, None),
        ]
        
        for setting_name, expected_type, required, validator in uba_tests:
            valid, value = self.check_setting(setting_name, expected_type, required)
            if not valid:
                uba_valid = False
            elif validator and value:
                if not validator(value):
                    self.errors.append(f"{setting_name} validation failed")
                    self.log(f"{setting_name} validation failed", 'ERROR')
                    uba_valid = False
        
        return uba_valid
    
    def test_cybersource_configuration(self) -> bool:
        """Test CyberSource Payment Gateway Configuration"""
        self.log("\n💳 Testing CyberSource Payment Gateway Configuration", 'HEADER', True)
        self.log("-" * 50, 'INFO', True)
        
        cybersource_valid = True
        
        # Required CyberSource settings with validation
        cybersource_tests = [
            ('CYBERSOURCE_MERCHANT_ID', str, True, self._validate_uuid),
            ('CYBERSOURCE_SHARED_SECRET', str, True, self._validate_base64),
            ('CYBERSOURCE_API_KEY', str, True, None),
            ('CYBERSOURCE_BASE_URL', str, True, self._validate_url),
            ('CYBERSOURCE_WEBHOOK_SECRET', str, True, None),
            ('CYBERSOURCE_TIMEOUT_SECONDS', int, True, lambda x: 5 <= x <= 120),
            ('CYBERSOURCE_RETRY_COUNT', int, True, lambda x: 1 <= x <= 10),
            ('CYBERSOURCE_RATE_LIMIT_PER_MINUTE', int, True, lambda x: 1 <= x <= 10000),
            ('CYBERSOURCE_SANDBOX_MODE', bool, True, None),
        ]
        
        for setting_name, expected_type, required, validator in cybersource_tests:
            valid, value = self.check_setting(setting_name, expected_type, required)
            if not valid:
                cybersource_valid = False
            elif validator and value:
                if not validator(value):
                    self.errors.append(f"{setting_name} validation failed")
                    self.log(f"{setting_name} validation failed", 'ERROR')
                    cybersource_valid = False
        
        return cybersource_valid
    
    def test_corefy_configuration(self) -> bool:
        """Test Corefy Payment Platform Configuration"""
        self.log("\n🔗 Testing Corefy Payment Platform Configuration", 'HEADER', True)
        self.log("-" * 50, 'INFO', True)
        
        corefy_valid = True
        
        # Required Corefy settings with validation
        corefy_tests = [
            ('COREFY_API_KEY', str, True, None),
            ('COREFY_SECRET_KEY', str, True, None),
            ('COREFY_CLIENT_KEY', str, True, None),
            ('COREFY_BASE_URL', str, True, self._validate_url),
            ('COREFY_WEBHOOK_SECRET', str, True, None),
            ('COREFY_TIMEOUT_SECONDS', int, True, lambda x: 5 <= x <= 120),
            ('COREFY_RETRY_COUNT', int, True, lambda x: 1 <= x <= 10),
            ('COREFY_RATE_LIMIT_PER_MINUTE', int, True, lambda x: 1 <= x <= 1000),
            ('COREFY_SANDBOX_MODE', bool, True, None),
        ]
        
        for setting_name, expected_type, required, validator in corefy_tests:
            valid, value = self.check_setting(setting_name, expected_type, required)
            if not valid:
                corefy_valid = False
            elif validator and value:
                if not validator(value):
                    self.errors.append(f"{setting_name} validation failed")
                    self.log(f"{setting_name} validation failed", 'ERROR')
                    corefy_valid = False
        
        return corefy_valid
    
    def test_feature_flags(self) -> bool:
        """Test Integration Feature Flags"""
        self.log("\n🚩 Testing Integration Feature Flags", 'HEADER', True)
        self.log("-" * 50, 'INFO', True)
        
        flags_valid = True
        
        # Feature flag settings
        flag_tests = [
            ('ENABLE_UBA_INTEGRATION', bool, True),
            ('ENABLE_CYBERSOURCE_INTEGRATION', bool, True),
            ('ENABLE_COREFY_INTEGRATION', bool, True),
        ]
        
        for setting_name, expected_type, required in flag_tests:
            valid, value = self.check_setting(setting_name, expected_type, required)
            if not valid:
                flags_valid = False
        
        return flags_valid
    
    def test_global_settings(self) -> bool:
        """Test Global Integration Settings"""
        self.log("\n🌐 Testing Global Integration Settings", 'HEADER', True)
        self.log("-" * 50, 'INFO', True)
        
        global_valid = True
        
        # Global integration settings with validation
        global_tests = [
            ('INTEGRATION_HEALTH_CHECK_INTERVAL', int, True, lambda x: 60 <= x <= 3600),
            ('INTEGRATION_LOG_REQUESTS', bool, True, None),
            ('INTEGRATION_LOG_RESPONSES', bool, True, None),
        ]
        
        for setting_name, expected_type, required, validator in global_tests:
            valid, value = self.check_setting(setting_name, expected_type, required)
            if not valid:
                global_valid = False
            elif validator and value:
                if not validator(value):
                    self.warnings.append(f"{setting_name} value ({value}) outside recommended range")
                    self.log(f"{setting_name} value ({value}) outside recommended range", 'WARNING')
        
        return global_valid
    
    def test_database_integrations(self) -> bool:
        """Test database integration records"""
        self.log("\n🗄️  Testing Database Integration Records", 'HEADER', True)
        self.log("-" * 50, 'INFO', True)
        
        db_valid = True
        
        expected_integrations = [
            ('uba_kenya', 'UBA Kenya Pay', IntegrationType.UBA_BANK),
            ('cybersource', 'CyberSource Payment Gateway', IntegrationType.CYBERSOURCE),
            ('corefy', 'Corefy Payment Orchestration', IntegrationType.COREFY),
        ]
        
        for code, name, integration_type in expected_integrations:
            self.total_checks += 1
            try:
                integration = Integration.objects.get(code=code)
                self.passed_checks += 1
                self.successes.append(f"Integration '{name}' found in database")
                self.log(f"Integration '{name}' found in database ✓", 'SUCCESS')
                
                # Additional checks
                if integration.status != IntegrationStatus.ACTIVE:
                    self.warnings.append(f"Integration '{name}' is not active (status: {integration.status})")
                    self.log(f"Integration '{name}' is not active (status: {integration.status})", 'WARNING')
                
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
        self.log("\n🔌 Testing API Connectivity", 'HEADER', True)
        self.log("-" * 50, 'INFO', True)
        
        connectivity_results = []
        
        # Test UBA API
        if getattr(settings, 'ENABLE_UBA_INTEGRATION', False):
            uba_result = self._test_uba_api()
            connectivity_results.append(uba_result)
        
        # Test CyberSource API
        if getattr(settings, 'ENABLE_CYBERSOURCE_INTEGRATION', False):
            cybersource_result = self._test_cybersource_api()
            connectivity_results.append(cybersource_result)
        
        # Test Corefy API
        if getattr(settings, 'ENABLE_COREFY_INTEGRATION', False):
            corefy_result = self._test_corefy_api()
            connectivity_results.append(corefy_result)
        
        return all(connectivity_results)
    
    def _test_uba_api(self) -> bool:
        """Test UBA API connectivity"""
        self.total_checks += 1
        
        try:
            base_url = getattr(settings, 'UBA_BASE_URL', '')
            access_token = getattr(settings, 'UBA_ACCESS_TOKEN', '')
            
            if not base_url or not access_token:
                self.errors.append("UBA API credentials not configured")
                self.log("UBA API credentials not configured", 'ERROR')
                return False
            
            # Test basic connectivity
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json',
                'User-Agent': 'PexiLabs-Integration-Test/1.0'
            }
            
            # Try to access the API root or health endpoint
            response = requests.get(
                f"{base_url.rstrip('/')}/",
                headers=headers,
                timeout=10,
                verify=True
            )
            
            if response.status_code in [200, 401, 403]:  # API is responding
                self.passed_checks += 1
                self.successes.append("UBA API is reachable")
                self.log(f"UBA API connectivity: ✓ (Status: {response.status_code})", 'SUCCESS')
                return True
            else:
                self.warnings.append(f"UBA API returned unexpected status: {response.status_code}")
                self.log(f"UBA API returned unexpected status: {response.status_code}", 'WARNING')
                return False
                
        except requests.exceptions.RequestException as e:
            self.errors.append(f"UBA API connectivity failed: {str(e)}")
            self.log(f"UBA API connectivity failed: {str(e)}", 'ERROR')
            return False
        except Exception as e:
            self.errors.append(f"UBA API test error: {str(e)}")
            self.log(f"UBA API test error: {str(e)}", 'ERROR')
            return False
    
    def _test_cybersource_api(self) -> bool:
        """Test CyberSource API connectivity"""
        self.total_checks += 1
        
        try:
            base_url = getattr(settings, 'CYBERSOURCE_BASE_URL', '')
            merchant_id = getattr(settings, 'CYBERSOURCE_MERCHANT_ID', '')
            
            if not base_url or not merchant_id:
                self.errors.append("CyberSource API credentials not configured")
                self.log("CyberSource API credentials not configured", 'ERROR')
                return False
            
            # Test basic connectivity
            response = requests.get(
                f"{base_url.rstrip('/')}/",
                timeout=10,
                verify=True
            )
            
            if response.status_code in [200, 401, 403, 404]:  # API is responding
                self.passed_checks += 1
                self.successes.append("CyberSource API is reachable")
                self.log(f"CyberSource API connectivity: ✓ (Status: {response.status_code})", 'SUCCESS')
                return True
            else:
                self.warnings.append(f"CyberSource API returned unexpected status: {response.status_code}")
                self.log(f"CyberSource API returned unexpected status: {response.status_code}", 'WARNING')
                return False
                
        except requests.exceptions.RequestException as e:
            self.errors.append(f"CyberSource API connectivity failed: {str(e)}")
            self.log(f"CyberSource API connectivity failed: {str(e)}", 'ERROR')
            return False
        except Exception as e:
            self.errors.append(f"CyberSource API test error: {str(e)}")
            self.log(f"CyberSource API test error: {str(e)}", 'ERROR')
            return False
    
    def _test_corefy_api(self) -> bool:
        """Test Corefy API connectivity"""
        self.total_checks += 1
        
        try:
            base_url = getattr(settings, 'COREFY_BASE_URL', '')
            api_key = getattr(settings, 'COREFY_API_KEY', '')
            
            if not base_url or not api_key:
                self.errors.append("Corefy API credentials not configured")
                self.log("Corefy API credentials not configured", 'ERROR')
                return False
            
            # Test basic connectivity
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
                'User-Agent': 'PexiLabs-Integration-Test/1.0'
            }
            
            response = requests.get(
                f"{base_url.rstrip('/')}/",
                headers=headers,
                timeout=10,
                verify=True
            )
            
            if response.status_code in [200, 401, 403, 404]:  # API is responding
                self.passed_checks += 1
                self.successes.append("Corefy API is reachable")
                self.log(f"Corefy API connectivity: ✓ (Status: {response.status_code})", 'SUCCESS')
                return True
            else:
                self.warnings.append(f"Corefy API returned unexpected status: {response.status_code}")
                self.log(f"Corefy API returned unexpected status: {response.status_code}", 'WARNING')
                return False
                
        except requests.exceptions.RequestException as e:
            self.errors.append(f"Corefy API connectivity failed: {str(e)}")
            self.log(f"Corefy API connectivity failed: {str(e)}", 'ERROR')
            return False
        except Exception as e:
            self.errors.append(f"Corefy API test error: {str(e)}")
            self.log(f"Corefy API test error: {str(e)}", 'ERROR')
            return False
    
    # Validation helper methods
    def _validate_url(self, url: str) -> bool:
        """Validate URL format"""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc]) and result.scheme in ['http', 'https']
        except:
            return False
    
    def _validate_jwt_token(self, token: str) -> bool:
        """Validate JWT token format"""
        try:
            parts = token.split('.')
            return len(parts) == 3 and all(len(part) > 0 for part in parts)
        except:
            return False
    
    def _validate_mongodb_id(self, obj_id: str) -> bool:
        """Validate MongoDB ObjectId format"""
        try:
            return len(obj_id) == 24 and all(c in '0123456789abcdef' for c in obj_id.lower())
        except:
            return False
    
    def _validate_uuid(self, uuid_str: str) -> bool:
        """Validate UUID format"""
        try:
            import uuid
            uuid.UUID(uuid_str)
            return True
        except:
            return False
    
    def _validate_base64(self, b64_str: str) -> bool:
        """Validate base64 format"""
        try:
            import base64
            base64.b64decode(b64_str)
            return True
        except:
            return False
    
    def show_configuration_summary(self):
        """Show current configuration summary"""
        self.log("\n📋 Current Integration Configuration Summary", 'HEADER', True)
        self.log("=" * 60, 'INFO', True)
        
        # UBA Configuration
        self.log("\n🏦 UBA Bank Integration:", 'INFO', True)
        uba_config = {
            'Base URL': getattr(settings, 'UBA_BASE_URL', 'Not set'),
            'Sandbox Mode': getattr(settings, 'UBA_SANDBOX_MODE', 'Not set'),
            'Rate Limit/min': getattr(settings, 'UBA_RATE_LIMIT_PER_MINUTE', 'Not set'),
            'Timeout (sec)': getattr(settings, 'UBA_TIMEOUT_SECONDS', 'Not set'),
            'Enabled': getattr(settings, 'ENABLE_UBA_INTEGRATION', 'Not set'),
        }
        for key, value in uba_config.items():
            self.log(f"  {key}: {value}", 'INFO', True)
        
        # CyberSource Configuration
        self.log("\n💳 CyberSource Payment Gateway:", 'INFO', True)
        cybersource_config = {
            'Base URL': getattr(settings, 'CYBERSOURCE_BASE_URL', 'Not set'),
            'Merchant ID': getattr(settings, 'CYBERSOURCE_MERCHANT_ID', 'Not set')[:20] + '...' if getattr(settings, 'CYBERSOURCE_MERCHANT_ID', '') else 'Not set',
            'Sandbox Mode': getattr(settings, 'CYBERSOURCE_SANDBOX_MODE', 'Not set'),
            'Rate Limit/min': getattr(settings, 'CYBERSOURCE_RATE_LIMIT_PER_MINUTE', 'Not set'),
            'Enabled': getattr(settings, 'ENABLE_CYBERSOURCE_INTEGRATION', 'Not set'),
        }
        for key, value in cybersource_config.items():
            self.log(f"  {key}: {value}", 'INFO', True)
        
        # Corefy Configuration
        self.log("\n🔗 Corefy Payment Platform:", 'INFO', True)
        corefy_config = {
            'Base URL': getattr(settings, 'COREFY_BASE_URL', 'Not set'),
            'Sandbox Mode': getattr(settings, 'COREFY_SANDBOX_MODE', 'Not set'),
            'Rate Limit/min': getattr(settings, 'COREFY_RATE_LIMIT_PER_MINUTE', 'Not set'),
            'Enabled': getattr(settings, 'ENABLE_COREFY_INTEGRATION', 'Not set'),
        }
        for key, value in corefy_config.items():
            self.log(f"  {key}: {value}", 'INFO', True)
        
        # Global Settings
        self.log("\n🌐 Global Integration Settings:", 'INFO', True)
        global_config = {
            'Health Check Interval': f"{getattr(settings, 'INTEGRATION_HEALTH_CHECK_INTERVAL', 'Not set')} seconds",
            'Log Requests': getattr(settings, 'INTEGRATION_LOG_REQUESTS', 'Not set'),
            'Log Responses': getattr(settings, 'INTEGRATION_LOG_RESPONSES', 'Not set'),
        }
        for key, value in global_config.items():
            self.log(f"  {key}: {value}", 'INFO', True)
    
    def run_all_tests(self, test_apis: bool = False) -> bool:
        """Run all integration tests"""
        self.log(f"{Colors.BOLD}{Colors.MAGENTA}🔍 Integration Requirements Validation{Colors.END}", 'HEADER', True)
        self.log("=" * 60, 'INFO', True)
        
        tests = [
            self.test_uba_configuration(),
            self.test_cybersource_configuration(),
            self.test_corefy_configuration(),
            self.test_feature_flags(),
            self.test_global_settings(),
            self.test_database_integrations(),
        ]
        
        if test_apis:
            tests.append(self.test_api_connectivity())
        
        return all(tests)
    
    def show_summary(self):
        """Show test summary"""
        self.log("\n📊 Test Summary", 'HEADER', True)
        self.log("=" * 60, 'INFO', True)
        
        success_rate = (self.passed_checks / self.total_checks * 100) if self.total_checks > 0 else 0
        
        self.log(f"Total Checks: {self.total_checks}", 'INFO', True)
        self.log(f"Passed: {self.passed_checks}", 'INFO', True)
        self.log(f"Success Rate: {success_rate:.1f}%", 'INFO', True)
        
        if self.errors:
            self.log(f"\n❌ Errors ({len(self.errors)}):", 'ERROR', True)
            for error in self.errors:
                self.log(f"  • {error}", 'ERROR', True)
        
        if self.warnings:
            self.log(f"\n⚠️  Warnings ({len(self.warnings)}):", 'WARNING', True)
            for warning in self.warnings:
                self.log(f"  • {warning}", 'WARNING', True)
        
        if not self.errors and not self.warnings:
            self.log(f"\n{Colors.BOLD}{Colors.GREEN}🎉 All integration requirements are properly configured!{Colors.END}", 'SUCCESS', True)
        elif not self.errors:
            self.log(f"\n{Colors.BOLD}{Colors.GREEN}✅ All critical requirements are met (some warnings exist){Colors.END}", 'SUCCESS', True)
        else:
            self.log(f"\n{Colors.BOLD}{Colors.RED}❌ Integration validation failed - please fix the errors above{Colors.END}", 'ERROR', True)
        
        return len(self.errors) == 0


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Test integration requirements')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--test-apis', '-a', action='store_true', help='Test API connectivity')
    parser.add_argument('--show-config', '-c', action='store_true', help='Show configuration summary')
    parser.add_argument('--fix-issues', '-f', action='store_true', help='Attempt to fix issues')
    
    args = parser.parse_args()
    
    tester = IntegrationTester(verbose=args.verbose)
    
    if args.show_config:
        tester.show_configuration_summary()
        return
    
    # Run tests
    success = tester.run_all_tests(test_apis=args.test_apis)
    
    # Show summary
    overall_success = tester.show_summary()
    
    # Exit with appropriate code
    sys.exit(0 if overall_success else 1)


if __name__ == '__main__':
    main()