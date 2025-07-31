from django.core.management.base import BaseCommand
from authentication.models import PreferredCurrency
from django.db import transaction


class Command(BaseCommand):
    help = 'Populate all world currencies in the PreferredCurrency model'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing currencies before populating',
        )

    def handle(self, *args, **options):
        """
        Populate the database with all world currencies.
        Data sourced from ISO 4217 currency codes.
        """
        
        # Comprehensive list of world currencies with ISO codes and symbols
        currencies_data = [
            # Major World Currencies
            ('United States Dollar', 'USD', '$'),
            ('Euro', 'EUR', '€'),
            ('British Pound Sterling', 'GBP', '£'),
            ('Japanese Yen', 'JPY', '¥'),
            ('Canadian Dollar', 'CAD', 'C$'),
            ('Australian Dollar', 'AUD', 'A$'),
            ('Swiss Franc', 'CHF', 'CHF'),
            ('Chinese Yuan', 'CNY', '¥'),
            ('Swedish Krona', 'SEK', 'kr'),
            ('New Zealand Dollar', 'NZD', 'NZ$'),
            ('Mexican Peso', 'MXN', '$'),
            ('Singapore Dollar', 'SGD', 'S$'),
            ('Hong Kong Dollar', 'HKD', 'HK$'),
            ('Norwegian Krone', 'NOK', 'kr'),
            ('South Korean Won', 'KRW', '₩'),
            ('Turkish Lira', 'TRY', '₺'),
            ('Russian Ruble', 'RUB', '₽'),
            ('Indian Rupee', 'INR', '₹'),
            ('Brazilian Real', 'BRL', 'R$'),
            ('South African Rand', 'ZAR', 'R'),
            
            # African Currencies
            ('Nigerian Naira', 'NGN', '₦'),
            ('Ghanaian Cedi', 'GHS', '₵'),
            ('Kenyan Shilling', 'KES', 'KSh'),
            ('Ugandan Shilling', 'UGX', 'USh'),
            ('Tanzanian Shilling', 'TZS', 'TSh'),
            ('Ethiopian Birr', 'ETB', 'Br'),
            ('Egyptian Pound', 'EGP', '£'),
            ('Moroccan Dirham', 'MAD', 'د.م.'),
            ('Algerian Dinar', 'DZD', 'د.ج'),
            ('Tunisian Dinar', 'TND', 'د.ت'),
            ('Libyan Dinar', 'LYD', 'ل.د'),
            ('Sudanese Pound', 'SDG', 'ج.س.'),
            ('Rwandan Franc', 'RWF', 'RF'),
            ('Burundian Franc', 'BIF', 'FBu'),
            ('Djiboutian Franc', 'DJF', 'Fdj'),
            ('Eritrean Nakfa', 'ERN', 'Nfk'),
            ('Somali Shilling', 'SOS', 'Sh'),
            ('Central African CFA Franc', 'XAF', 'FCFA'),
            ('West African CFA Franc', 'XOF', 'CFA'),
            ('Comorian Franc', 'KMF', 'CF'),
            ('Cape Verdean Escudo', 'CVE', '$'),
            ('Gambian Dalasi', 'GMD', 'D'),
            ('Guinean Franc', 'GNF', 'FG'),
            ('Guinea-Bissau Peso', 'GWP', 'P'),
            ('Liberian Dollar', 'LRD', 'L$'),
            ('Sierra Leonean Leone', 'SLL', 'Le'),
            ('Mauritanian Ouguiya', 'MRU', 'UM'),
            ('Malawian Kwacha', 'MWK', 'MK'),
            ('Mozambican Metical', 'MZN', 'MT'),
            ('Namibian Dollar', 'NAD', 'N$'),
            ('Botswanan Pula', 'BWP', 'P'),
            ('Lesotho Loti', 'LSL', 'L'),
            ('Swazi Lilangeni', 'SZL', 'L'),
            ('Zambian Kwacha', 'ZMW', 'ZK'),
            ('Zimbabwean Dollar', 'ZWL', 'Z$'),
            ('Angolan Kwanza', 'AOA', 'Kz'),
            ('Congolese Franc', 'CDF', 'FC'),
            ('Malagasy Ariary', 'MGA', 'Ar'),
            ('Mauritian Rupee', 'MUR', '₨'),
            ('Seychellois Rupee', 'SCR', '₨'),
            
            # Asian Currencies
            ('Thai Baht', 'THB', '฿'),
            ('Indonesian Rupiah', 'IDR', 'Rp'),
            ('Malaysian Ringgit', 'MYR', 'RM'),
            ('Philippine Peso', 'PHP', '₱'),
            ('Vietnamese Dong', 'VND', '₫'),
            ('Cambodian Riel', 'KHR', '៛'),
            ('Laotian Kip', 'LAK', '₭'),
            ('Myanmar Kyat', 'MMK', 'K'),
            ('Bangladeshi Taka', 'BDT', '৳'),
            ('Pakistani Rupee', 'PKR', '₨'),
            ('Sri Lankan Rupee', 'LKR', '₨'),
            ('Nepalese Rupee', 'NPR', '₨'),
            ('Bhutanese Ngultrum', 'BTN', 'Nu'),
            ('Maldivian Rufiyaa', 'MVR', '.ރ'),
            ('Afghan Afghani', 'AFN', '؋'),
            ('Uzbekistani Som', 'UZS', "so'm"),
            ('Kazakhstani Tenge', 'KZT', '₸'),
            ('Kyrgystani Som', 'KGS', 'лв'),
            ('Tajikistani Somoni', 'TJS', 'ЅМ'),
            ('Turkmenistani Manat', 'TMT', 'T'),
            ('Mongolian Tugrik', 'MNT', '₮'),
            ('North Korean Won', 'KPW', '₩'),
            ('Taiwanese Dollar', 'TWD', 'NT$'),
            ('Macanese Pataca', 'MOP', 'P'),
            ('Brunei Dollar', 'BND', 'B$'),
            ('East Timor US Dollar', 'USD', '$'),
            
            # Middle Eastern Currencies
            ('Saudi Riyal', 'SAR', '﷼'),
            ('UAE Dirham', 'AED', 'د.إ'),
            ('Qatari Riyal', 'QAR', '﷼'),
            ('Kuwaiti Dinar', 'KWD', 'د.ك'),
            ('Bahraini Dinar', 'BHD', '.د.ب'),
            ('Omani Rial', 'OMR', '﷼'),
            ('Yemeni Rial', 'YER', '﷼'),
            ('Jordanian Dinar', 'JOD', 'د.ا'),
            ('Lebanese Pound', 'LBP', 'ل.ل'),
            ('Syrian Pound', 'SYP', '£'),
            ('Iraqi Dinar', 'IQD', 'ع.د'),
            ('Iranian Rial', 'IRR', '﷼'),
            ('Israeli New Shekel', 'ILS', '₪'),
            
            # European Currencies (non-Euro)
            ('Albanian Lek', 'ALL', 'L'),
            ('Bosnian Convertible Mark', 'BAM', 'KM'),
            ('Bulgarian Lev', 'BGN', 'лв'),
            ('Croatian Kuna', 'HRK', 'kn'),
            ('Czech Koruna', 'CZK', 'Kč'),
            ('Danish Krone', 'DKK', 'kr'),
            ('Hungarian Forint', 'HUF', 'Ft'),
            ('Icelandic Krona', 'ISK', 'kr'),
            ('Moldovan Leu', 'MDL', 'L'),
            ('North Macedonian Denar', 'MKD', 'ден'),
            ('Polish Zloty', 'PLN', 'zł'),
            ('Romanian Leu', 'RON', 'lei'),
            ('Serbian Dinar', 'RSD', 'Дин.'),
            ('Ukrainian Hryvnia', 'UAH', '₴'),
            ('Belarusian Ruble', 'BYN', 'Br'),
            ('Georgian Lari', 'GEL', '₾'),
            ('Armenian Dram', 'AMD', '֏'),
            ('Azerbaijani Manat', 'AZN', '₼'),
            
            # Caribbean and Central American Currencies
            ('Barbadian Dollar', 'BBD', '$'),
            ('Belize Dollar', 'BZD', 'BZ$'),
            ('Costa Rican Colón', 'CRC', '₡'),
            ('Cuban Peso', 'CUP', '₱'),
            ('Dominican Peso', 'DOP', 'RD$'),
            ('Guatemalan Quetzal', 'GTQ', 'Q'),
            ('Haitian Gourde', 'HTG', 'G'),
            ('Honduran Lempira', 'HNL', 'L'),
            ('Jamaican Dollar', 'JMD', 'J$'),
            ('Nicaraguan Córdoba', 'NIO', 'C$'),
            ('Panamanian Balboa', 'PAB', 'B/.'),
            ('Trinidad and Tobago Dollar', 'TTD', 'TT$'),
            ('Eastern Caribbean Dollar', 'XCD', '$'),
            ('Bahamian Dollar', 'BSD', '$'),
            ('Cayman Islands Dollar', 'KYD', '$'),
            ('Bermudian Dollar', 'BMD', '$'),
            
            # South American Currencies
            ('Argentine Peso', 'ARS', '$'),
            ('Bolivian Boliviano', 'BOB', '$b'),
            ('Chilean Peso', 'CLP', '$'),
            ('Colombian Peso', 'COP', '$'),
            ('Ecuadorian US Dollar', 'USD', '$'),
            ('Guyanese Dollar', 'GYD', '$'),
            ('Paraguayan Guaraní', 'PYG', 'Gs'),
            ('Peruvian Sol', 'PEN', 'S/'),
            ('Surinamese Dollar', 'SRD', '$'),
            ('Uruguayan Peso', 'UYU', '$U'),
            ('Venezuelan Bolívar', 'VES', 'Bs'),
            
            # Pacific Currencies
            ('Fijian Dollar', 'FJD', '$'),
            ('Papua New Guinean Kina', 'PGK', 'K'),
            ('Samoan Tālā', 'WST', 'T'),
            ('Tongan Paʻanga', 'TOP', 'T$'),
            ('Vanuatu Vatu', 'VUV', 'Vt'),
            ('Solomon Islands Dollar', 'SBD', '$'),
            ('CFP Franc', 'XPF', '₣'),
            
            # Cryptocurrencies (Popular ones)
            ('Bitcoin', 'BTC', '₿'),
            ('Ethereum', 'ETH', 'Ξ'),
            ('Litecoin', 'LTC', 'Ł'),
            ('Ripple', 'XRP', 'XRP'),
            ('Bitcoin Cash', 'BCH', 'BCH'),
            ('Cardano', 'ADA', 'ADA'),
            ('Polkadot', 'DOT', 'DOT'),
            ('Chainlink', 'LINK', 'LINK'),
            ('Stellar', 'XLM', 'XLM'),
            ('Dogecoin', 'DOGE', 'Ð'),
            
            # Precious Metals
            ('Gold', 'XAU', 'Au'),
            ('Silver', 'XAG', 'Ag'),
            ('Platinum', 'XPT', 'Pt'),
            ('Palladium', 'XPD', 'Pd'),
            
            # Special Drawing Rights and Others
            ('Special Drawing Rights', 'XDR', 'SDR'),
            ('Bitcoin', 'BTC', '₿'),
            ('Tether', 'USDT', '₮'),
            ('USD Coin', 'USDC', 'USDC'),
            ('Binance USD', 'BUSD', 'BUSD'),
        ]

        if options['clear']:
            self.stdout.write('Clearing existing currencies...')
            PreferredCurrency.objects.all().delete()

        created_count = 0
        updated_count = 0
        skipped_count = 0

        self.stdout.write('Starting currency population...')

        with transaction.atomic():
            for name, code, symbol in currencies_data:
                try:
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
                            self.style.SUCCESS(f'✓ Created: {name} ({code})')
                        )
                    else:
                        # Update existing currency if name or symbol is different
                        if currency.name != name or currency.symbol != symbol:
                            currency.name = name
                            currency.symbol = symbol
                            currency.save()
                            updated_count += 1
                            self.stdout.write(
                                self.style.WARNING(f'↻ Updated: {name} ({code})')
                            )
                        else:
                            skipped_count += 1
                            self.stdout.write(
                                self.style.HTTP_INFO(f'- Skipped: {name} ({code}) - already exists')
                            )
                            
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'✗ Error creating {name} ({code}): {str(e)}')
                    )

        # Summary
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('CURRENCY POPULATION COMPLETED'))
        self.stdout.write('='*60)
        self.stdout.write(f'✓ Created: {created_count} currencies')
        self.stdout.write(f'↻ Updated: {updated_count} currencies')
        self.stdout.write(f'- Skipped: {skipped_count} currencies')
        self.stdout.write(f'Total processed: {created_count + updated_count + skipped_count} currencies')
        
        # Show some statistics
        total_currencies = PreferredCurrency.objects.count()
        active_currencies = PreferredCurrency.objects.filter(is_active=True).count()
        
        self.stdout.write('\n' + '-'*40)
        self.stdout.write('DATABASE STATISTICS:')
        self.stdout.write('-'*40)
        self.stdout.write(f'Total currencies in database: {total_currencies}')
        self.stdout.write(f'Active currencies: {active_currencies}')
        self.stdout.write(f'Inactive currencies: {total_currencies - active_currencies}')
        
        # Show most popular currencies
        major_currencies = PreferredCurrency.objects.filter(
            code__in=['USD', 'EUR', 'GBP', 'JPY', 'AUD', 'CAD', 'CHF', 'CNY', 'NGN', 'INR']
        ).values_list('name', 'code', 'symbol')
        
        if major_currencies:
            self.stdout.write('\n' + '-'*40)
            self.stdout.write('MAJOR CURRENCIES AVAILABLE:')
            self.stdout.write('-'*40)
            for name, code, symbol in major_currencies:
                self.stdout.write(f'{symbol} {name} ({code})')
        
        self.stdout.write('\n' + self.style.SUCCESS('All currencies have been successfully populated!'))
        self.stdout.write('You can now run: python manage.py runserver')
