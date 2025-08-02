#!/usr/bin/env python
"""
Test script to verify user role-based dashboard redirects work correctly
"""
import os
import django
from django.conf import settings
from django.urls import reverse
from django.test import Client
from django.contrib.auth import get_user_model

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pexilabs.settings')
django.setup()

from authentication.models import UserRole, Country, PreferredCurrency

User = get_user_model()

def test_dashboard_redirects():
    """Test that users are redirected to the correct dashboard based on their role"""
    
    print("Testing User Role-Based Dashboard Redirects...")
    print("=" * 60)
    
    # Clean up any existing test users
    test_emails = [
        'admin@test.com', 'staff@test.com', 'moderator@test.com', 
        'user@test.com', 'superuser@test.com'
    ]
    User.objects.filter(email__in=test_emails).delete()
    
    # Create test users with different roles
    print("\n1. Creating test users with different roles:")
    print("-" * 40)
    
    # Create a superuser
    superuser = User.objects.create_user(
        email='superuser@test.com',
        password='testpass123',
        first_name='Super',
        last_name='User',
        is_verified=True,
        is_staff=True,
        is_superuser=True
    )
    print(f"✓ Created superuser: {superuser.email}")
    
    # Create an admin user
    admin_user = User.objects.create_user(
        email='admin@test.com',
        password='testpass123',
        first_name='Admin',
        last_name='User',
        role=UserRole.ADMIN,
        is_verified=True,
        is_staff=True
    )
    print(f"✓ Created admin user: {admin_user.email}")
    
    # Create a staff user
    staff_user = User.objects.create_user(
        email='staff@test.com',
        password='testpass123',
        first_name='Staff',
        last_name='User',
        role=UserRole.STAFF,
        is_verified=True,
        is_staff=True
    )
    print(f"✓ Created staff user: {staff_user.email}")
    
    # Create a moderator user
    moderator_user = User.objects.create_user(
        email='moderator@test.com',
        password='testpass123',
        first_name='Moderator',
        last_name='User',
        role=UserRole.MODERATOR,
        is_verified=True
    )
    print(f"✓ Created moderator user: {moderator_user.email}")
    
    # Create a regular user
    regular_user = User.objects.create_user(
        email='user@test.com',
        password='testpass123',
        first_name='Regular',
        last_name='User',
        role=UserRole.USER,
        is_verified=True
    )
    print(f"✓ Created regular user: {regular_user.email}")
    
    print("\n2. Testing login redirects:")
    print("-" * 40)
    
    # Test cases: (user, expected_redirect_url, description)
    test_cases = [
        (superuser, '/admin/', 'Superuser → Django Admin'),
        (admin_user, '/dashboard/admin/', 'Admin → Admin Dashboard'),
        (staff_user, '/dashboard/staff/', 'Staff → Staff Dashboard'),
        (moderator_user, '/dashboard/moderator/', 'Moderator → Moderator Dashboard'),
        (regular_user, '/dashboard/user/', 'Regular User → User Dashboard'),
    ]
    
    client = Client()
    
    for user, expected_url, description in test_cases:
        # Login the user
        client.login(username=user.email, password='testpass123')
        
        # Test dashboard redirect
        response = client.get('/dashboard/')
        
        if response.status_code == 302:
            redirect_url = response.url
            if redirect_url == expected_url:
                print(f"✓ {description}: {redirect_url}")
            else:
                print(f"✗ {description}: Expected {expected_url}, got {redirect_url}")
        else:
            print(f"✗ {description}: Expected redirect, got {response.status_code}")
        
        # Test landing page redirect
        response = client.get('/')
        if response.status_code == 302:
            print(f"  Landing page → {response.url}")
        
        # Logout
        client.logout()
    
    print("\n3. Testing dashboard access controls:")
    print("-" * 40)
    
    # Test that regular user cannot access admin dashboard
    client.login(username=regular_user.email, password='testpass123')
    response = client.get('/dashboard/admin/')
    if response.status_code == 302:
        print("✓ Regular user blocked from admin dashboard")
    else:
        print("✗ Regular user can access admin dashboard")
    
    # Test that moderator can access moderator dashboard
    client.logout()
    client.login(username=moderator_user.email, password='testpass123')
    response = client.get('/dashboard/moderator/')
    if response.status_code == 200:
        print("✓ Moderator can access moderator dashboard")
    else:
        print("✗ Moderator cannot access moderator dashboard")
    
    client.logout()
    
    print("\n" + "=" * 60)
    print("🎉 Dashboard redirect testing completed!")
    
    # Cleanup
    User.objects.filter(email__in=test_emails).delete()
    print("✓ Test users cleaned up")

if __name__ == '__main__':
    test_dashboard_redirects()
