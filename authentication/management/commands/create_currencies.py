from django.core.management.base import BaseCommand
from authentication.models import PreferredCurrency


class Command(BaseCommand):
    help = 'Create initial currencies data'

    def handle(self, *args, **options):
        currencies_data = [
            {'name': 'US Dollar', 'code': 'USD', 'symbol': '$'},
            {'name': 'Euro', 'code': 'EUR', 'symbol': '€'},
            {'name': 'British Pound', 'code': 'GBP', 'symbol': '£'},
            {'name': 'Canadian Dollar', 'code': 'CAD', 'symbol': 'C$'},
            {'name': 'Australian Dollar', 'code': 'AUD', 'symbol': 'A$'},
            {'name': 'Japanese Yen', 'code': 'JPY', 'symbol': '¥'},
            {'name': 'Swiss Franc', 'code': 'CHF', 'symbol': 'CHF'},
            {'name': 'Chinese Yuan', 'code': 'CNY', 'symbol': '¥'},
            {'name': 'Indian Rupee', 'code': 'INR', 'symbol': '₹'},
            {'name': 'South Korean Won', 'code': 'KRW', 'symbol': '₩'},
            {'name': 'Singapore Dollar', 'code': 'SGD', 'symbol': 'S$'},
            {'name': 'Hong Kong Dollar', 'code': 'HKD', 'symbol': 'HK$'},
            {'name': 'Swedish Krona', 'code': 'SEK', 'symbol': 'kr'},
            {'name': 'Norwegian Krone', 'code': 'NOK', 'symbol': 'kr'},
            {'name': 'Danish Krone', 'code': 'DKK', 'symbol': 'kr'},
            {'name': 'Polish Zloty', 'code': 'PLN', 'symbol': 'zł'},
            {'name': 'Czech Koruna', 'code': 'CZK', 'symbol': 'Kč'},
            {'name': 'Hungarian Forint', 'code': 'HUF', 'symbol': 'Ft'},
            {'name': 'Russian Ruble', 'code': 'RUB', 'symbol': '₽'},
            {'name': 'Brazilian Real', 'code': 'BRL', 'symbol': 'R$'},
            {'name': 'Mexican Peso', 'code': 'MXN', 'symbol': '$'},
            {'name': 'South African Rand', 'code': 'ZAR', 'symbol': 'R'},
            {'name': 'Turkish Lira', 'code': 'TRY', 'symbol': '₺'},
            {'name': 'Israeli Shekel', 'code': 'ILS', 'symbol': '₪'},
            {'name': 'Thai Baht', 'code': 'THB', 'symbol': '฿'},
            {'name': 'Malaysian Ringgit', 'code': 'MYR', 'symbol': 'RM'},
            {'name': 'Philippine Peso', 'code': 'PHP', 'symbol': '₱'},
            {'name': 'Indonesian Rupiah', 'code': 'IDR', 'symbol': 'Rp'},
            {'name': 'Vietnamese Dong', 'code': 'VND', 'symbol': '₫'},
            {'name': 'New Zealand Dollar', 'code': 'NZD', 'symbol': 'NZ$'},
        ]

        created_count = 0
        for currency_data in currencies_data:
            currency, created = PreferredCurrency.objects.get_or_create(
                code=currency_data['code'],
                defaults=currency_data
            )
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created currency: {currency.name}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Currency already exists: {currency.name}')
                )

        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {created_count} currencies')
        )
