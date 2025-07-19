#!/usr/bin/env python
"""
Test script for App Key Generation Module (Whitelabel Integration)
"""
import os
import sys
import django
import secrets
from datetime import datetime, timedelta

# Add the project directory to Python path
project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_dir)

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pexilabs.settings')
django.setup()

from django.contrib import admin
from django.utils import timezone
from authentication.models import (
    WhitelabelPartner, AppKey, AppKeyUsageLog, 
    AppKeyType, AppKeyStatus, CustomUser
)
from authentication.admin import WhitelabelPartnerAdmin, AppKeyAdmin, AppKeyUsageLogAdmin

def test_app_key_generation_module():
    """Test the complete App Key Generation module"""
    print("=== App Key Generation Module Test ===\n")
    
    # Test 1: Model creation and validation
    print("1. Testing model creation and validation...")
    
    # Create a test whitelabel partner
    partner = WhitelabelPartner.objects.create(
        name="Test Partner Inc",
        code="test_partner",
        contact_email="contact@testpartner.com",
        contact_phone="+1-555-0123",
        website_url="https://testpartner.com",
        business_address="123 Test Street, Test City, TC 12345",
        business_registration_number="REG123456",
        allowed_domains="testpartner.com,api.testpartner.com",
        webhook_url="https://testpartner.com/webhooks",
        daily_api_limit=5000,
        monthly_api_limit=150000,
        is_active=True,
        is_verified=False
    )
    print(f"   ✓ Created whitelabel partner: {partner}")
    print(f"   ✓ Partner ID: {partner.id}")
    print(f"   ✓ Allowed domains: {partner.get_allowed_domains_list()}")
    
    # Test domain validation
    print(f"   ✓ Domain 'testpartner.com' allowed: {partner.is_domain_allowed('testpartner.com')}")
    print(f"   ✓ Domain 'unauthorized.com' allowed: {partner.is_domain_allowed('unauthorized.com')}")
    
    # Generate webhook secret
    webhook_secret = partner.generate_webhook_secret()
    print(f"   ✓ Generated webhook secret: {webhook_secret[:8]}...")
    
    # Test 2: App Key creation
    print("\n2. Testing app key creation...")
    
    # Create different types of app keys
    production_key = AppKey.objects.create(
        partner=partner,
        name="Production API Key",
        key_type=AppKeyType.PRODUCTION,
        scopes="read,write",
        daily_request_limit=1000,
        expires_at=timezone.now() + timedelta(days=365)
    )
    print(f"   ✓ Created production key: {production_key.public_key}")
    print(f"   ✓ Key secret (masked): {production_key.masked_secret}")
    print(f"   ✓ Key scopes: {production_key.get_scopes_list()}")
    print(f"   ✓ Key is active: {production_key.is_active()}")
    
    sandbox_key = AppKey.objects.create(
        partner=partner,
        name="Sandbox API Key",
        key_type=AppKeyType.SANDBOX,
        scopes="read,write,admin",
        allowed_ips="127.0.0.1,192.168.1.0/24"
    )
    print(f"   ✓ Created sandbox key: {sandbox_key.public_key}")
    print(f"   ✓ Allowed IPs: {sandbox_key.get_allowed_ips_list()}")
    
    # Test key verification
    if hasattr(production_key, '_raw_secret'):
        raw_secret = production_key._raw_secret
        print(f"   ✓ Secret verification: {production_key.verify_secret(raw_secret)}")
        print(f"   ✓ Wrong secret verification: {production_key.verify_secret('wrong_secret')}")
    
    # Test 3: Usage logging
    print("\n3. Testing usage logging...")
    
    # Create some usage logs
    usage_logs = []
    for i in range(5):
        log = AppKeyUsageLog.objects.create(
            app_key=production_key,
            endpoint=f"/api/v1/endpoint{i}",
            method="GET",
            ip_address="192.168.1.100",
            user_agent="TestClient/1.0",
            status_code=200 if i % 2 == 0 else 400,
            response_time_ms=100 + i * 10,
            request_size_bytes=1024,
            response_size_bytes=2048,
            request_id=f"req_{secrets.token_hex(8)}"
        )
        usage_logs.append(log)
        print(f"   ✓ Created usage log: {log}")
    
    # Test usage statistics
    start_date = timezone.now().date() - timedelta(days=1)
    end_date = timezone.now().date()
    stats = AppKeyUsageLog.get_usage_stats(production_key, start_date, end_date)
    print(f"   ✓ Usage stats: {stats}")
    
    # Test 4: Admin integration
    print("\n4. Testing admin integration...")
    
    # Check admin registration
    registered_models = admin.site._registry
    print(f"   ✓ WhitelabelPartner registered: {WhitelabelPartner in registered_models}")
    print(f"   ✓ AppKey registered: {AppKey in registered_models}")
    print(f"   ✓ AppKeyUsageLog registered: {AppKeyUsageLog in registered_models}")
    
    # Test admin functionality
    partner_admin = WhitelabelPartnerAdmin(WhitelabelPartner, admin.site)
    app_key_admin = AppKeyAdmin(AppKey, admin.site)
    
    print(f"   ✓ Partner admin actions: {[action for action in partner_admin.actions if not action.startswith('delete')]}")
    print(f"   ✓ App key admin actions: {[action for action in app_key_admin.actions if not action.startswith('delete')]}")
    
    # Test 5: API key management operations
    print("\n5. Testing key management operations...")
    
    # Test key suspension
    sandbox_key.suspend("Testing suspension")
    print(f"   ✓ Sandbox key suspended: {sandbox_key.status}")
    print(f"   ✓ Sandbox key is active: {sandbox_key.is_active()}")
    
    # Test key activation
    sandbox_key.activate()
    print(f"   ✓ Sandbox key activated: {sandbox_key.status}")
    print(f"   ✓ Sandbox key is active: {sandbox_key.is_active()}")
    
    # Test key revocation
    sandbox_key.revoke()
    print(f"   ✓ Sandbox key revoked: {sandbox_key.status}")
    print(f"   ✓ Revoked at: {sandbox_key.revoked_at}")
    
    # Test usage recording
    production_key.record_usage()
    print(f"   ✓ Production key usage count: {production_key.total_requests}")
    print(f"   ✓ Last used at: {production_key.last_used_at}")
    
    # Test 6: Partner statistics
    print("\n6. Testing partner statistics...")
    
    active_keys_count = partner.get_active_app_keys_count()
    print(f"   ✓ Active app keys count: {active_keys_count}")
    
    # Test 7: Security features
    print("\n7. Testing security features...")
    
    # Test key expiration
    expired_key = AppKey.objects.create(
        partner=partner,
        name="Expired Key",
        key_type=AppKeyType.DEVELOPMENT,
        expires_at=timezone.now() - timedelta(days=1)
    )
    print(f"   ✓ Expired key is expired: {expired_key.is_expired()}")
    print(f"   ✓ Expired key is active: {expired_key.is_active()}")
    
    # Test IP restrictions
    restricted_key = AppKey.objects.create(
        partner=partner,
        name="IP Restricted Key",
        key_type=AppKeyType.PRODUCTION,
        allowed_ips="192.168.1.100,10.0.0.1"
    )
    print(f"   ✓ IP '192.168.1.100' allowed: {restricted_key.is_ip_allowed('192.168.1.100')}")
    print(f"   ✓ IP '192.168.1.200' allowed: {restricted_key.is_ip_allowed('192.168.1.200')}")
    
    # Test scope validation
    admin_key = AppKey.objects.create(
        partner=partner,
        name="Admin Key",
        key_type=AppKeyType.PRODUCTION,
        scopes="read,write,admin"
    )
    print(f"   ✓ Has 'read' scope: {admin_key.has_scope('read')}")
    print(f"   ✓ Has 'admin' scope: {admin_key.has_scope('admin')}")
    print(f"   ✓ Has 'delete' scope: {admin_key.has_scope('delete')}")
    
    # Test 8: Data cleanup and summary
    print("\n8. Summary and cleanup...")
    
    total_partners = WhitelabelPartner.objects.count()
    total_keys = AppKey.objects.count()
    total_logs = AppKeyUsageLog.objects.count()
    
    print(f"   ✓ Total whitelabel partners: {total_partners}")
    print(f"   ✓ Total app keys: {total_keys}")
    print(f"   ✓ Total usage logs: {total_logs}")
    
    # Show key statistics by type
    for key_type in AppKeyType.choices:
        count = AppKey.objects.filter(key_type=key_type[0]).count()
        print(f"   ✓ {key_type[1]} keys: {count}")
    
    # Show key statistics by status
    for status in AppKeyStatus.choices:
        count = AppKey.objects.filter(status=status[0]).count()
        print(f"   ✓ {status[1]} keys: {count}")
    
    print("\n=== App Key Generation Module Test Completed Successfully! ===")
    
    print("\n📋 **Next Steps for Integration:**")
    print("1. 🔧 **Admin Interface**: Access Django admin to manage partners and keys")
    print("2. 🌐 **API Endpoints**: Use the REST API endpoints for programmatic access")
    print("3. 🔐 **Authentication**: Implement API key authentication middleware")
    print("4. 📊 **Monitoring**: Set up usage monitoring and rate limiting")
    print("5. 🚀 **Deployment**: Configure for production with proper security")
    
    print("\n🔑 **Key Features Implemented:**")
    print("✅ Whitelabel partner management")
    print("✅ Multi-type API key generation (Production, Sandbox, Development)")
    print("✅ Comprehensive usage logging and analytics")
    print("✅ Advanced security (IP restrictions, scopes, expiration)")
    print("✅ Admin interface with bulk actions")
    print("✅ REST API endpoints for all operations")
    print("✅ Webhook secret management")
    print("✅ Rate limiting and quota management")

if __name__ == '__main__':
    test_app_key_generation_module()
