from django.core.management.base import BaseCommand
from shop.models import Product
from decimal import Decimal

class Command(BaseCommand):
    help = 'Seed the database with gaming products (MCC: 7995 - Gambling/Gaming)'

    def handle(self, *args, **options):
        gaming_products = [
            {
                'name': 'Gaming Mechanical Keyboard RGB',
                'description': 'Professional mechanical gaming keyboard with RGB backlighting, Cherry MX switches, and programmable keys. Perfect for competitive gaming and typing.',
                'price': Decimal('149.99'),
                'stock_quantity': 25,
                'category': 'Gaming Peripherals'
            },
            {
                'name': 'Wireless Gaming Mouse Pro',
                'description': 'High-precision wireless gaming mouse with 16000 DPI sensor, customizable buttons, and 70-hour battery life.',
                'price': Decimal('89.99'),
                'stock_quantity': 30,
                'category': 'Gaming Peripherals'
            },
            {
                'name': 'Gaming Headset 7.1 Surround',
                'description': 'Premium gaming headset with 7.1 surround sound, noise-canceling microphone, and comfortable over-ear design.',
                'price': Decimal('129.99'),
                'stock_quantity': 20,
                'category': 'Gaming Audio'
            },
            {
                'name': 'Gaming Chair Ergonomic Pro',
                'description': 'Professional gaming chair with lumbar support, adjustable armrests, and premium PU leather. Built for long gaming sessions.',
                'price': Decimal('299.99'),
                'stock_quantity': 15,
                'category': 'Gaming Furniture'
            },
            {
                'name': 'Gaming Monitor 27" 144Hz',
                'description': '27-inch gaming monitor with 144Hz refresh rate, 1ms response time, and FreeSync technology for smooth gameplay.',
                'price': Decimal('349.99'),
                'stock_quantity': 12,
                'category': 'Gaming Displays'
            },
            {
                'name': 'Gaming Laptop RTX 4060',
                'description': 'High-performance gaming laptop with RTX 4060 graphics, Intel i7 processor, 16GB RAM, and 1TB SSD.',
                'price': Decimal('1299.99'),
                'stock_quantity': 8,
                'category': 'Gaming Hardware'
            },
            {
                'name': 'Gaming Desktop PC Custom',
                'description': 'Custom-built gaming PC with RTX 4070, AMD Ryzen 7, 32GB RAM, and liquid cooling system.',
                'price': Decimal('1899.99'),
                'stock_quantity': 5,
                'category': 'Gaming Hardware'
            },
            {
                'name': 'Gaming Mousepad XXL',
                'description': 'Extra-large gaming mousepad with smooth surface, anti-slip base, and stitched edges for durability.',
                'price': Decimal('29.99'),
                'stock_quantity': 50,
                'category': 'Gaming Accessories'
            },
            {
                'name': 'Gaming Webcam 4K',
                'description': '4K gaming webcam with auto-focus, built-in microphone, and streaming software compatibility.',
                'price': Decimal('199.99'),
                'stock_quantity': 18,
                'category': 'Gaming Streaming'
            },
            {
                'name': 'Gaming Controller Wireless Pro',
                'description': 'Professional wireless gaming controller with haptic feedback, adaptive triggers, and 40-hour battery.',
                'price': Decimal('79.99'),
                'stock_quantity': 35,
                'category': 'Gaming Controllers'
            },
            {
                'name': 'Gaming SSD 2TB NVMe',
                'description': 'High-speed 2TB NVMe SSD designed for gaming with fast load times and reliable performance.',
                'price': Decimal('249.99'),
                'stock_quantity': 22,
                'category': 'Gaming Storage'
            },
            {
                'name': 'Gaming RAM 32GB DDR5',
                'description': '32GB DDR5 gaming memory kit with RGB lighting and optimized timings for maximum performance.',
                'price': Decimal('299.99'),
                'stock_quantity': 16,
                'category': 'Gaming Memory'
            },
            {
                'name': 'Gaming Graphics Card RTX 4080',
                'description': 'NVIDIA RTX 4080 graphics card with ray tracing, DLSS 3, and 16GB GDDR6X memory.',
                'price': Decimal('1199.99'),
                'stock_quantity': 6,
                'category': 'Gaming Hardware'
            },
            {
                'name': 'Gaming Microphone USB',
                'description': 'Professional USB gaming microphone with cardioid pattern, pop filter, and real-time monitoring.',
                'price': Decimal('149.99'),
                'stock_quantity': 24,
                'category': 'Gaming Audio'
            },
            {
                'name': 'Gaming Speakers 2.1 System',
                'description': '2.1 gaming speaker system with subwoofer, RGB lighting, and immersive sound quality.',
                'price': Decimal('119.99'),
                'stock_quantity': 19,
                'category': 'Gaming Audio'
            },
            {
                'name': 'Gaming Desk RGB LED',
                'description': 'Gaming desk with built-in RGB LED lighting, cable management, and ergonomic design.',
                'price': Decimal('399.99'),
                'stock_quantity': 10,
                'category': 'Gaming Furniture'
            },
            {
                'name': 'Gaming VR Headset',
                'description': 'Virtual reality gaming headset with 4K display, 120Hz refresh rate, and wireless connectivity.',
                'price': Decimal('599.99'),
                'stock_quantity': 7,
                'category': 'Gaming VR'
            },
            {
                'name': 'Gaming Capture Card 4K',
                'description': '4K gaming capture card for streaming and recording with zero latency passthrough.',
                'price': Decimal('179.99'),
                'stock_quantity': 14,
                'category': 'Gaming Streaming'
            },
            {
                'name': 'Gaming Power Supply 850W',
                'description': '850W modular gaming power supply with 80+ Gold certification and RGB lighting.',
                'price': Decimal('159.99'),
                'stock_quantity': 21,
                'category': 'Gaming Hardware'
            },
            {
                'name': 'Gaming Cooling Fan RGB',
                'description': 'RGB gaming cooling fans with PWM control, silent operation, and customizable lighting effects.',
                'price': Decimal('49.99'),
                'stock_quantity': 40,
                'category': 'Gaming Cooling'
            }
        ]

        created_count = 0
        updated_count = 0

        for product_data in gaming_products:
            product, created = Product.objects.get_or_create(
                name=product_data['name'],
                defaults={
                    'description': product_data['description'],
                    'price': product_data['price'],
                    'stock_quantity': product_data['stock_quantity'],
                    'is_active': True
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created product: {product.name}')
                )
            else:
                # Update existing product
                product.description = product_data['description']
                product.price = product_data['price']
                product.stock_quantity = product_data['stock_quantity']
                product.save()
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f'Updated product: {product.name}')
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'\nSeeding completed!\n'
                f'Created: {created_count} products\n'
                f'Updated: {updated_count} products\n'
                f'Total products in database: {Product.objects.count()}'
            )
        )