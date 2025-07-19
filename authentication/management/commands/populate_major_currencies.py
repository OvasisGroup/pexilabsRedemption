from django.core.management.base import BaseCommand
from authentication.models import PreferredCurrency
from django.db import transaction


class Command(BaseCommand):
    help = 'Populate major world currencies in the PreferredCurrency model'

    def handle(self, *args, **options):
        """
        Populate the database with major world currencies only.
        """
        
        # Major currencies list
        major_currencies = [
            ('United States Dollar', 'USD', '$'),
            ('Euro', 'EUR', '€'),
            ('British Pound Sterling', 'GBP', '£'),
            ('Japanese Yen', 'JPY', '¥'),
            ('Canadian Dollar', 'CAD', 'C$'),
            ('Australian Dollar', 'AUD', 'A$'),
            ('Swiss Franc', 'CHF', 'CHF'),
            ('Chinese Yuan', 'CNY', '¥'),
            ('Indian Rupee', 'INR', '₹'),
            ('Brazilian Real', 'BRL', 'R$'),
            ('Russian Ruble', 'RUB', '₽'),
            ('South Korean Won', 'KRW', '₩'),
            ('Mexican Peso', 'MXN', '$'),
            ('Singapore Dollar', 'SGD', 'S$'),
            ('Hong Kong Dollar', 'HKD', 'HK$'),
            ('Norwegian Krone', 'NOK', 'kr'),
            ('Swedish Krona', 'SEK', 'kr'),
            ('Turkish Lira', 'TRY', '₺'),
            ('South African Rand', 'ZAR', 'R'),
            ('Nigerian Naira', 'NGN', '₦'),
            ('Ghanaian Cedi', 'GHS', '₵'),
            ('Kenyan Shilling', 'KES', 'KSh'),
            ('Egyptian Pound', 'EGP', '£'),
            ('Thai Baht', 'THB', '฿'),
            ('Indonesian Rupiah', 'IDR', 'Rp'),
            ('Malaysian Ringgit', 'MYR', 'RM'),
            ('Philippine Peso', 'PHP', '₱'),
            ('Vietnamese Dong', 'VND', '₫'),
            ('Pakistani Rupee', 'PKR', '₨'),
            ('Bangladeshi Taka', 'BDT', '৳'),
            ('Saudi Riyal', 'SAR', '﷼'),
            ('UAE Dirham', 'AED', 'د.إ'),
            ('Israeli New Shekel', 'ILS', '₪'),
            ('Polish Zloty', 'PLN', 'zł'),
            ('Czech Koruna', 'CZK', 'Kč'),
            ('Hungarian Forint', 'HUF', 'Ft'),
            ('Romanian Leu', 'RON', 'lei'),
            ('Chilean Peso', 'CLP', '$'),
            ('Colombian Peso', 'COP', '$'),
            ('Argentine Peso', 'ARS', '$'),
            ('Bitcoin', 'BTC', '₿'),
            ('Ethereum', 'ETH', 'Ξ'),
        ]

        created_count = 0

        self.stdout.write('Creating major world currencies...')

        with transaction.atomic():
            for name, code, symbol in major_currencies:
                currency, created = PreferredCurrency.objects.get_or_create(
                    code=code,
                    defaults={
                        'name': name,
                        'symbol': symbol,
                        'is_active': True
                    }
                )
                
                if created:
                    created_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(f'✓ Created: {name} ({code}) {symbol}')
                    )

        self.stdout.write(
            self.style.SUCCESS(f'\nSuccessfully created {created_count} currencies!')
        )