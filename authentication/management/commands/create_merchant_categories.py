from django.core.management.base import BaseCommand
from authentication.models import MerchantCategory


class Command(BaseCommand):
    help = 'Create default merchant categories'

    def handle(self, *args, **options):
        categories = [
            {
                'name': 'Retail',
                'code': 'retail',
                'description': 'Physical and online retail stores'
            },
            {
                'name': 'Food & Beverage',
                'code': 'food_beverage',
                'description': 'Restaurants, cafes, and food delivery services'
            },
            {
                'name': 'Professional Services',
                'code': 'professional_services',
                'description': 'Consulting, legal, accounting, and other professional services'
            },
            {
                'name': 'Healthcare',
                'code': 'healthcare',
                'description': 'Medical practices, pharmacies, and healthcare providers'
            },
            {
                'name': 'Technology',
                'code': 'technology',
                'description': 'Software, hardware, and technology services'
            },
            {
                'name': 'Education',
                'code': 'education',
                'description': 'Schools, training centers, and educational services'
            },
            {
                'name': 'Transportation',
                'code': 'transportation',
                'description': 'Taxi, ride-sharing, and transportation services'
            },
            {
                'name': 'Hospitality',
                'code': 'hospitality',
                'description': 'Hotels, resorts, and hospitality services'
            },
            {
                'name': 'Entertainment',
                'code': 'entertainment',
                'description': 'Gaming, media, and entertainment services'
            },
            {
                'name': 'Beauty & Wellness',
                'code': 'beauty_wellness',
                'description': 'Salons, spas, and wellness services'
            },
            {
                'name': 'E-commerce',
                'code': 'ecommerce',
                'description': 'Online marketplaces and e-commerce platforms'
            },
            {
                'name': 'Non-profit',
                'code': 'nonprofit',
                'description': 'Charitable organizations and non-profits'
            },
            {
                'name': 'Other',
                'code': 'other',
                'description': 'Other business categories not listed above'
            }
        ]

        created_count = 0
        updated_count = 0

        for category_data in categories:
            category, created = MerchantCategory.objects.get_or_create(
                code=category_data['code'],
                defaults={
                    'name': category_data['name'],
                    'description': category_data['description'],
                    'is_active': True
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created merchant category: {category.name}')
                )
            else:
                # Update existing category if name or description changed
                if category.name != category_data['name'] or category.description != category_data['description']:
                    category.name = category_data['name']
                    category.description = category_data['description']
                    category.save()
                    updated_count += 1
                    self.stdout.write(
                        self.style.WARNING(f'Updated merchant category: {category.name}')
                    )

        self.stdout.write(
            self.style.SUCCESS(
                f'\nMerchant categories setup complete!\n'
                f'Created: {created_count}\n'
                f'Updated: {updated_count}\n'
                f'Total: {MerchantCategory.objects.count()}'
            )
        )
