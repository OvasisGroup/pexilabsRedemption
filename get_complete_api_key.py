#!/usr/bin/env python3
"""
Script to generate complete API keys for testing integrations.
This script creates or regenerates API keys and provides the complete
cURL command for testing the payment endpoint.

Usage:
  python get_complete_api_key.py                                    # Uses default localhost:8001
  python get_complete_api_key.py --host 127.0.0.1 --port 8000      # Custom host and port
  python get_complete_api_key.py --scheme https --host api.com --port 443  # HTTPS with custom domain
  DJANGO_HOST=api.example.com DJANGO_PORT=443 python get_complete_api_key.py  # Environment variables

Priority order for URL configuration:
  1. Command line arguments (--host, --port, --scheme)
  2. Environment variables (DJANGO_HOST, DJANGO_PORT, DJANGO_SCHEME)
  3. Django settings (ALLOWED_HOSTS)
  4. Default (http://localhost:8001)
"""

import os
import sys
import django
import argparse
from urllib.parse import urlparse

# Parse arguments first to handle help before Django setup
parser = argparse.ArgumentParser(description='Generate API key with dynamic URL')
parser.add_argument('--host', default=None, help='Host for the API (e.g., localhost, 127.0.0.1)')
parser.add_argument('--port', default=None, type=int, help='Port for the API (e.g., 8000, 8001)')
parser.add_argument('--scheme', default='http', choices=['http', 'https'], help='URL scheme')
args = parser.parse_args()

# Add the project root to Python path
sys.path.append('/Users/omambia/workspaces/pexi-labs/pexilabsRedemption')

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pexilabs.settings')
django.setup()

from authentication.models import Merchant, WhitelabelPartner, AppKey, AppKeyType, AppKeyStatus
from django.contrib.auth import get_user_model
from django.conf import settings

User = get_user_model()

def get_or_create_merchant_partner(merchant):
    """Get or create whitelabel partner for merchant"""
    partner_code = f"merchant_{merchant.id}"
    partner, created = WhitelabelPartner.objects.get_or_create(
        code=partner_code,
        defaults={
            'name': f"{merchant.business_name} Partner",
            'description': f"Auto-generated partner for merchant {merchant.business_name}",
            'is_active': True,
        }
    )
    return partner, created

def get_base_url():
    """
    Get the base URL for the application from various sources.
    Priority: command line args > environment variable > Django settings > default
    """
    # If both host and port are provided via command line
    if args.host and args.port:
        return f"{args.scheme}://{args.host}:{args.port}"
    
    # Check environment variables
    env_host = os.environ.get('DJANGO_HOST')
    env_port = os.environ.get('DJANGO_PORT')
    env_scheme = os.environ.get('DJANGO_SCHEME', 'http')
    
    # If environment variables are set, use them
    if env_host and env_port:
        return f"{env_scheme}://{env_host}:{env_port}"
    
    # Use command line args if provided
    if args.host or args.port:
        host = args.host or 'localhost'
        port = args.port or 8001
        return f"{args.scheme}://{host}:{port}"
    
    # Try to get from Django settings if available
    host = 'localhost'
    port = 8001
    scheme = 'http'
    
    try:
        if hasattr(settings, 'ALLOWED_HOSTS') and settings.ALLOWED_HOSTS:
            # Use the first allowed host that's not '*' or '127.0.0.1'
            for allowed_host in settings.ALLOWED_HOSTS:
                if allowed_host not in ['*', '127.0.0.1', 'localhost', 'testserver']:
                    host = allowed_host
                    break
    except:
        pass
    
    return f"{scheme}://{host}:{port}"

def main():
    try:
        # Find the admin user's merchant account
        admin_user = User.objects.get(email='admin@pexilabs.com')
        
        if not hasattr(admin_user, 'merchant_account') or not admin_user.merchant_account:
            print("❌ Admin user doesn't have a merchant account")
            return
        
        merchant = admin_user.merchant_account
        print(f"✅ Found merchant: {merchant.business_name}")
        
        # Get or create partner
        partner, created = get_or_create_merchant_partner(merchant)
        if created:
            print(f"✅ Created new partner: {partner.name}")
        else:
            print(f"✅ Using existing partner: {partner.name}")
        
        # Check for existing API keys
        existing_keys = AppKey.objects.filter(partner=partner, status=AppKeyStatus.ACTIVE)
        
        if existing_keys.exists():
            print(f"\n📋 Found {existing_keys.count()} existing API key(s):")
            for key in existing_keys:
                print(f"   - {key.name}: {key.public_key}")
            
            # Ask if user wants to create a new one or regenerate existing
            choice = input("\nDo you want to (1) Create new API key or (2) Regenerate existing key? [1/2]: ")
            
            if choice == '2' and existing_keys.exists():
                # Regenerate the first existing key
                api_key = existing_keys.first()
                
                # Generate new secret
                import secrets
                import hashlib
                
                raw_secret = secrets.token_urlsafe(32)
                api_key.secret_key = hashlib.sha256(raw_secret.encode()).hexdigest()
                api_key.save()
                
                print(f"\n🔄 Regenerated API key: {api_key.name}")
                print(f"📋 Public Key: {api_key.public_key}")
                print(f"🔐 Secret Key: {raw_secret}")
                print(f"\n🔗 Complete API Key: {api_key.public_key}:{raw_secret}")
                
                # Show the complete cURL command
                base_url = get_base_url()
                print("\n📝 Complete cURL command:")
                print(f"""curl -X POST {base_url}/checkout/make-payment/ \\
  -H "Authorization: Bearer {api_key.public_key}:{raw_secret}" \\
  -H "Content-Type: application/json" \\
  -d '{{
    "amount": 100.00,
    "currency": "USD",
    "customer_email": "test@example.com",
    "description": "Integration Test Payment",
    "callback_url": "{base_url}/success",
    "cancel_url": "{base_url}/cancel"
  }}'""")
                
                return
        
        # Create new API key with unique name
        import uuid
        unique_suffix = str(uuid.uuid4())[:8]
        api_key = AppKey.objects.create(
            partner=partner,
            name=f"Test Integration Key {unique_suffix}",
            key_type=AppKeyType.SANDBOX,
            scopes="read,write",
            status=AppKeyStatus.ACTIVE
        )
        
        # Get the raw secret (it's stored in _raw_secret temporarily)
        raw_secret = getattr(api_key, '_raw_secret', None)
        
        if not raw_secret:
            # If _raw_secret is not available, regenerate
            import secrets
            import hashlib
            
            raw_secret = secrets.token_urlsafe(32)
            api_key.secret_key = hashlib.sha256(raw_secret.encode()).hexdigest()
            api_key.save()
        
        print(f"\n✅ Created new API key: {api_key.name}")
        print(f"📋 Public Key: {api_key.public_key}")
        print(f"🔐 Secret Key: {raw_secret}")
        print(f"\n🔗 Complete API Key: {api_key.public_key}:{raw_secret}")
        
        # Show the complete cURL command
        base_url = get_base_url()
        print("\n📝 Complete cURL command:")
        print(f"""curl -X POST {base_url}/checkout/make-payment/ \\
  -H "Authorization: Bearer {api_key.public_key}:{raw_secret}" \\
  -H "Content-Type: application/json" \\
  -d '{{
    "amount": 100.00,
    "currency": "USD",
    "customer_email": "test@example.com",
    "description": "Integration Test Payment",
    "callback_url": "{base_url}/success",
    "cancel_url": "{base_url}/cancel"
  }}'""")
        
        print("\n⚠️  Important: Save this secret key securely. It won't be shown again!")
        
    except User.DoesNotExist:
        print("❌ Admin user (admin@pexilabs.com) not found")
        print("   Please make sure you're logged in as admin first")
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()