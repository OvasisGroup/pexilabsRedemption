#!/usr/bin/env python
"""
Test registration flow with role groups
"""
import os
import sys
import django

# Add the project directory to Python path
sys.path.append('/Users/asd/Desktop/desktop/pexilabs')

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pexilabs.settings')
django.setup()

from django.test import Client
from django.contrib.auth.models import Group
from authentication.models import CustomUser, MerchantCategory, Country, PreferredCurrency
import uuid

def test_registration_with_role_groups():
    """Test registration process and automatic role group assignment"""
    print("🧪 Testing Registration with Role Groups")
    print("=" * 50)
    
    # Setup test data
    country = Country.objects.first()
    currency = PreferredCurrency.objects.first()
    category = MerchantCategory.objects.first()
    
    if not country:
        country = Country.objects.create(name='Test Country', code='TC', phone_code='+123')
    if not currency:
        currency = PreferredCurrency.objects.create(name='Test Dollar', code='TDL', symbol='$')
    if not category:
        category = MerchantCategory.objects.create(name='Test Category', code='test')
    
    # Test registration via web form
    print("\n--- Testing Web Registration ---")
    client = Client()
    
    test_email = f"regtest{uuid.uuid4().hex[:8]}@example.com"
    
    registration_data = {
        'first_name': 'Registration',
        'last_name': 'Test',
        'email': test_email,
        'password': 'testpass123',
        'confirm_password': 'testpass123',
        'phone': '+1234567890',
        'country': str(country.id),
        'currency': str(currency.id),
        'business_name': 'Test Business',
        'merchant_category': str(category.id),
    }
    
    # Submit registration
    response = client.post('/auth/register/', registration_data)
    print(f"Registration response status: {response.status_code}")
    
    if response.status_code == 302:
        print("✅ Registration redirected (expected)")
        
        # Check if user was created
        try:
            user = CustomUser.objects.get(email=test_email)
            print(f"✅ User created: {user.email}")
            
            # Check role assignment
            print(f"User role: {user.role}")
            
            # Check group assignment
            user_groups = [group.name for group in user.groups.all()]
            print(f"User groups: {user_groups}")
            
            if 'merchants' in user_groups:
                print("✅ User automatically assigned to merchants group during registration")
            else:
                print("❌ User NOT assigned to merchants group")
            
            # Check if merchant account was created
            if hasattr(user, 'merchant_account') and user.merchant_account:
                print("ℹ️  Merchant account will be created after email verification")
            else:
                print("ℹ️  Merchant account not yet created (user not verified)")
                
        except CustomUser.DoesNotExist:
            print("❌ User not created during registration")
            
    else:
        print(f"❌ Registration failed with status: {response.status_code}")
        if hasattr(response, 'content'):
            print("Response content:", response.content.decode()[:500])

def test_group_permissions():
    """Test that groups have the correct permissions"""
    print("\n--- Testing Group Permissions ---")
    
    merchants_group = Group.objects.get(name='merchants')
    admin_group = Group.objects.get(name='admin')
    moderator_group = Group.objects.get(name='moderator')
    
    print(f"Merchants group permissions ({merchants_group.permissions.count()}):")
    for perm in merchants_group.permissions.all():
        print(f"  - {perm.codename}: {perm.name}")
    
    print(f"\nModerator group permissions ({moderator_group.permissions.count()}):")
    for perm in moderator_group.permissions.all():
        print(f"  - {perm.codename}: {perm.name}")
    
    print(f"\nAdmin group has {admin_group.permissions.count()} permissions (full access)")

def test_role_group_mappings():
    """Test the role group mappings"""
    print("\n--- Testing Role Group Mappings ---")
    
    from authentication.models import RoleGroup, UserRole
    
    mappings = RoleGroup.objects.all()
    
    for mapping in mappings:
        groups = [group.name for group in mapping.groups.all()]
        print(f"{mapping.get_role_display()} -> {groups}")

if __name__ == '__main__':
    test_registration_with_role_groups()
    test_group_permissions()
    test_role_group_mappings()
    print("\n✅ All role group tests completed!")
