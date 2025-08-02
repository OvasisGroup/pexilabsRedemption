#!/usr/bin/env python
"""
Script to generate a complete API key for testing the checkout API.
This will create a new API key and display both public and secret parts.
"""

import os
import sys
import django

# Add the project directory to Python path
sys.path.append('/Users/omambia/workspaces/pexi-labs/pexilabsRedemption')

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pexilabs.settings')
django.setup()

from authentication.models import Merchant, WhitelabelPartner, AppKey, AppKeyType, AppKeyStatus
from django.contrib.auth import get_user_model

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
                print("\n📝 Complete cURL command:")
                print(f"""curl -X POST http://localhost:8001/checkout/make-payment/ \\
  -H "Authorization: Bearer {api_key.public_key}:{raw_secret}" \\
  -H "Content-Type: application/json" \\
  -d '{{
    "amount": 100.00,
    "currency": "USD",
    "customer_email": "test@example.com",
    "description": "Integration Test Payment",
    "callback_url": "http://localhost:8001/success",
    "cancel_url": "http://localhost:8001/cancel"
  }}'""")
                
                return
        
        # Create new API key
        api_key = AppKey.objects.create(
            partner=partner,
            name="Test Integration Key",
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
        print("\n📝 Complete cURL command:")
        print(f"""curl -X POST http://localhost:8001/checkout/make-payment/ \\
  -H "Authorization: Bearer {api_key.public_key}:{raw_secret}" \\
  -H "Content-Type: application/json" \\
  -d '{{
    "amount": 100.00,
    "currency": "USD",
    "customer_email": "test@example.com",
    "description": "Integration Test Payment",
    "callback_url": "http://localhost:8001/success",
    "cancel_url": "http://localhost:8001/cancel"
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