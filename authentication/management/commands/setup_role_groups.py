from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.db import models
from authentication.models import CustomUser, RoleGroup, UserRole, Merchant


class Command(BaseCommand):
    help = 'Create role groups: admin, merchants, moderator and set up automatic assignment'

    def handle(self, *args, **options):
        self.create_role_groups()
        self.create_role_group_mappings()
        self.create_custom_permissions()
        self.assign_existing_users()
        self.stdout.write(
            self.style.SUCCESS('Successfully created role groups and automatic assignment system')
        )

    def create_role_groups(self):
        """Create the three main role groups"""
        groups_data = [
            {
                'name': 'admin',
                'description': 'Administrators with full system access'
            },
            {
                'name': 'merchants',
                'description': 'Merchant users with business account access'
            },
            {
                'name': 'moderator',
                'description': 'Moderators with verification and review access'
            }
        ]

        for group_data in groups_data:
            group, created = Group.objects.get_or_create(
                name=group_data['name']
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Created group: {group.name}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Group already exists: {group.name}')
                )

    def create_role_group_mappings(self):
        """Create role to group mappings for automatic assignment"""
        # Get groups
        admin_group = Group.objects.get(name='admin')
        merchants_group = Group.objects.get(name='merchants')
        moderator_group = Group.objects.get(name='moderator')

        # Create role mappings - users will be assigned to merchants group by default
        role_mappings = [
            {
                'role': UserRole.ADMIN,
                'groups': [admin_group]
            },
            {
                'role': UserRole.STAFF,
                'groups': [admin_group]  # Staff users get admin group access
            },
            {
                'role': UserRole.MODERATOR,
                'groups': [moderator_group]
            },
            {
                'role': UserRole.USER,
                'groups': [merchants_group]  # Regular users go to merchants group
            }
        ]

        for mapping in role_mappings:
            role_group, created = RoleGroup.objects.get_or_create(
                role=mapping['role']
            )
            
            # Clear existing groups and add new ones
            role_group.groups.clear()
            for group in mapping['groups']:
                role_group.groups.add(group)
            
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Created role mapping: {role_group.get_role_display()} -> {[g.name for g in mapping["groups"]]}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Updated role mapping: {role_group.get_role_display()} -> {[g.name for g in mapping["groups"]]}')
                )

    def create_custom_permissions(self):
        """Create custom permissions for the authentication system"""
        content_type = ContentType.objects.get_for_model(CustomUser)
        
        custom_permissions = [
            ('can_view_user_stats', 'Can view user statistics'),
            ('can_manage_users', 'Can manage users'),
            ('can_manage_roles', 'Can manage user roles'),
            ('can_view_all_users', 'Can view all users'),
            ('can_deactivate_users', 'Can deactivate users'),
            ('can_verify_users', 'Can verify user emails'),
            ('can_manage_sessions', 'Can manage user sessions'),
            ('can_access_admin_endpoints', 'Can access admin endpoints'),
            ('can_verify_merchants', 'Can verify merchant applications'),
            ('can_view_merchant_stats', 'Can view merchant statistics'),
        ]

        for codename, name in custom_permissions:
            permission, created = Permission.objects.get_or_create(
                codename=codename,
                content_type=content_type,
                defaults={'name': name}
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Created permission: {permission.name}')
                )

        # Assign permissions to groups
        self.assign_permissions_to_groups()

    def assign_permissions_to_groups(self):
        """Assign permissions to groups"""
        # Get groups
        admin_group = Group.objects.get(name='admin')
        merchants_group = Group.objects.get(name='merchants')
        moderator_group = Group.objects.get(name='moderator')

        # Get custom permissions
        content_type = ContentType.objects.get_for_model(CustomUser)
        
        # Admin permissions (all permissions)
        admin_permissions = Permission.objects.all()
        admin_group.permissions.set(admin_permissions)

        # Moderator permissions
        moderator_permission_codenames = [
            'can_view_all_users',
            'can_verify_users',
            'can_verify_merchants',
            'can_view_merchant_stats',
            'view_customuser',
            'change_customuser',
            'view_merchant',
            'change_merchant',
        ]
        moderator_permissions = Permission.objects.filter(
            models.Q(content_type=content_type, codename__in=moderator_permission_codenames) |
            models.Q(codename__in=['view_merchant', 'change_merchant'])
        )
        moderator_group.permissions.set(moderator_permissions)

        # Merchants permissions (basic user and merchant permissions)
        merchant_ct = ContentType.objects.get_for_model(Merchant)
        
        merchant_permission_codenames = [
            'view_customuser',    # Can view their own user profile
            'change_customuser',  # Can change their own user profile
        ]
        merchant_permissions = Permission.objects.filter(
            models.Q(content_type=content_type, codename__in=merchant_permission_codenames) |
            models.Q(content_type=merchant_ct, codename__in=['view_merchant', 'change_merchant'])
        )
        merchants_group.permissions.set(merchant_permissions)

        self.stdout.write(
            self.style.SUCCESS('Assigned permissions to groups')
        )

    def assign_existing_users(self):
        """Assign existing users to appropriate groups based on their roles"""
        
        # Clear all existing group assignments first
        for user in CustomUser.objects.all():
            user.groups.clear()
        
        # Get groups
        admin_group = Group.objects.get(name='admin')
        merchants_group = Group.objects.get(name='merchants')
        moderator_group = Group.objects.get(name='moderator')
        
        # Assign users based on their roles
        admin_users = CustomUser.objects.filter(
            models.Q(is_superuser=True) | 
            models.Q(role=UserRole.ADMIN) | 
            models.Q(role=UserRole.STAFF)
        )
        for user in admin_users:
            user.groups.add(admin_group)
            self.stdout.write(f'Added {user.email} to admin group')
        
        # Assign moderator users
        moderator_users = CustomUser.objects.filter(role=UserRole.MODERATOR)
        for user in moderator_users:
            user.groups.add(moderator_group)
            self.stdout.write(f'Added {user.email} to moderator group')
        
        # Assign all other users to merchants group (default group)
        merchant_users = CustomUser.objects.exclude(
            models.Q(is_superuser=True) | 
            models.Q(role=UserRole.ADMIN) | 
            models.Q(role=UserRole.STAFF) |
            models.Q(role=UserRole.MODERATOR)
        )
        for user in merchant_users:
            user.groups.add(merchants_group)
            self.stdout.write(f'Added {user.email} to merchants group')
        
        self.stdout.write(
            self.style.SUCCESS('Assigned existing users to appropriate groups')
        )
