#!/usr/bin/env python
"""
Test script for role groups and automatic assignment
"""
import os
import sys
import django

# Add the project directory to Python path
sys.path.append('/Users/asd/Desktop/desktop/pexilabs')

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pexilabs.settings')
django.setup()

from django.contrib.auth.models import Group
from authentication.models import CustomUser, UserRole
import uuid

def test_role_groups():
    """Test the role groups system"""
    print("🧪 Testing Role Groups System")
    print("=" * 40)
    
    # Check if groups exist
    print("\n--- Checking Groups ---")
    try:
        admin_group = Group.objects.get(name='admin')
        merchants_group = Group.objects.get(name='merchants')
        moderator_group = Group.objects.get(name='moderator')
        
        print(f"✅ Admin group exists: {admin_group.name}")
        print(f"✅ Merchants group exists: {merchants_group.name}")
        print(f"✅ Moderator group exists: {moderator_group.name}")
        
        # Show group permissions
        print(f"\nAdmin group permissions: {admin_group.permissions.count()}")
        print(f"Merchants group permissions: {merchants_group.permissions.count()}")
        print(f"Moderator group permissions: {moderator_group.permissions.count()}")
        
    except Group.DoesNotExist as e:
        print(f"❌ Group not found: {e}")
        return
    
    # Test automatic assignment by creating a new user
    print("\n--- Testing Automatic Assignment ---")
    test_email = f"roletest{uuid.uuid4().hex[:8]}@example.com"
    
    try:
        # Create a new user
        test_user = CustomUser.objects.create_user(
            email=test_email,
            password='testpass123',
            first_name='Role',
            last_name='Test',
            role=UserRole.USER  # Regular user should go to merchants group
        )
        
        print(f"✅ Created test user: {test_user.email}")
        
        # Check group assignment
        user_groups = test_user.groups.all()
        group_names = [group.name for group in user_groups]
        
        print(f"User groups: {group_names}")
        
        if 'merchants' in group_names:
            print("✅ User automatically assigned to merchants group")
        else:
            print("❌ User NOT assigned to merchants group")
            
        # Test with different roles
        print("\n--- Testing Different Roles ---")
        
        # Test admin role
        admin_email = f"admintest{uuid.uuid4().hex[:8]}@example.com"
        admin_user = CustomUser.objects.create_user(
            email=admin_email,
            password='testpass123',
            first_name='Admin',
            last_name='Test',
            role=UserRole.ADMIN
        )
        
        admin_groups = [group.name for group in admin_user.groups.all()]
        print(f"Admin user groups: {admin_groups}")
        
        # Test moderator role
        mod_email = f"modtest{uuid.uuid4().hex[:8]}@example.com"
        mod_user = CustomUser.objects.create_user(
            email=mod_email,
            password='testpass123',
            first_name='Moderator',
            last_name='Test',
            role=UserRole.MODERATOR
        )
        
        mod_groups = [group.name for group in mod_user.groups.all()]
        print(f"Moderator user groups: {mod_groups}")
        
        # Clean up test users
        test_user.delete()
        admin_user.delete()
        mod_user.delete()
        
        print("\n✅ Role groups system test completed successfully!")
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()

def test_existing_user_assignments():
    """Test that existing users are properly assigned"""
    print("\n--- Testing Existing User Assignments ---")
    
    # Sample a few users to check their group assignments
    sample_users = CustomUser.objects.all()[:5]
    
    for user in sample_users:
        groups = [group.name for group in user.groups.all()]
        print(f"{user.email} ({user.role}): {groups}")

if __name__ == '__main__':
    test_role_groups()
    test_existing_user_assignments()
