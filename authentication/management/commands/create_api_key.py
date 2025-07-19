"""
Management command to create API keys for testing merchant authentication.
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from authentication.models import WhitelabelPartner, AppKey, AppKeyType, AppKeyStatus


class Command(BaseCommand):
    help = 'Create API keys for testing merchant authentication'

    def add_arguments(self, parser):
        parser.add_argument(
            '--partner-name',
            type=str,
            default='Test Partner',
            help='Name of the test partner'
        )
        parser.add_argument(
            '--partner-code',
            type=str,
            default='test_partner',
            help='Code for the test partner'
        )
        parser.add_argument(
            '--key-name',
            type=str,
            default='Test API Key',
            help='Name for the API key'
        )
        parser.add_argument(
            '--key-type',
            type=str,
            choices=['sandbox', 'production', 'development'],
            default='sandbox',
            help='Type of API key'
        )
        parser.add_argument(
            '--scopes',
            type=str,
            default='read,write',
            help='Comma-separated list of scopes'
        )

    @transaction.atomic
    def handle(self, *args, **options):
        partner_name = options['partner_name']
        partner_code = options['partner_code']
        key_name = options['key_name']
        key_type = options['key_type']
        scopes = options['scopes']

        try:
            # Get or create the partner
            partner, created = WhitelabelPartner.objects.get_or_create(
                code=partner_code,
                defaults={
                    'name': partner_name,
                    'contact_email': f'contact@{partner_code}.com',
                    'is_active': True,
                    'is_verified': True,
                    'daily_api_limit': 10000,
                    'monthly_api_limit': 300000,
                    'concurrent_connections_limit': 100,
                }
            )

            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Created partner: {partner.name} ({partner.code})')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Partner already exists: {partner.name} ({partner.code})')
                )

            # Create the API key
            app_key = AppKey.objects.create(
                partner=partner,
                name=key_name,
                key_type=getattr(AppKeyType, key_type.upper()),
                scopes=scopes,
                status=AppKeyStatus.ACTIVE
            )

            # Get the raw secret from the temporary attribute (if available)
            raw_secret = getattr(app_key, '_raw_secret', None)
            
            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS('✅ API Key created successfully!'))
            self.stdout.write('')
            self.stdout.write(f'Partner: {partner.name}')
            self.stdout.write(f'API Key Name: {app_key.name}')
            self.stdout.write(f'Public Key: {app_key.public_key}')
            if raw_secret:
                self.stdout.write(f'Secret Key: {raw_secret}')
                self.stdout.write('')
                self.stdout.write(self.style.SUCCESS('Full API Key (public:secret):'))
                self.stdout.write(self.style.SUCCESS(f'{app_key.public_key}:{raw_secret}'))
            else:
                self.stdout.write(self.style.WARNING('Secret key was not available (already hashed)'))
            self.stdout.write('')
            self.stdout.write('Usage examples:')
            self.stdout.write('1. Authorization header:')
            if raw_secret:
                self.stdout.write(f'   Authorization: Bearer {app_key.public_key}:{raw_secret}')
            else:
                self.stdout.write(f'   Authorization: Bearer {app_key.public_key}:<secret>')
            self.stdout.write('')
            self.stdout.write('2. Custom header:')
            if raw_secret:
                self.stdout.write(f'   X-API-Key: {app_key.public_key}:{raw_secret}')
            else:
                self.stdout.write(f'   X-API-Key: {app_key.public_key}:<secret>')
            self.stdout.write('')

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error creating API key: {str(e)}')
            )
