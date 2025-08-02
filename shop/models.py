from django.db import models
from django.contrib.auth import get_user_model
from decimal import Decimal

User = get_user_model()

class Product(models.Model):
    CATEGORY_CHOICES = [
        ('Gaming Peripherals', 'Gaming Peripherals'),
        ('Gaming Audio', 'Gaming Audio'),
        ('Gaming Furniture', 'Gaming Furniture'),
        ('Gaming Displays', 'Gaming Displays'),
        ('Gaming Hardware', 'Gaming Hardware'),
        ('Gaming Accessories', 'Gaming Accessories'),
        ('Gaming Streaming', 'Gaming Streaming'),
        ('Gaming Controllers', 'Gaming Controllers'),
        ('Gaming Storage', 'Gaming Storage'),
        ('Gaming Memory', 'Gaming Memory'),
        ('Gaming VR', 'Gaming VR'),
        ('Gaming Cooling', 'Gaming Cooling'),
    ]
    
    name = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image_url = models.URLField(blank=True, null=True)
    stock_quantity = models.PositiveIntegerField(default=0)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='Gaming Accessories')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['-created_at']

class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Cart for {self.user.username}"

    @property
    def total_amount(self):
        return sum(item.total_price for item in self.items.all())

    @property
    def total_items(self):
        return sum(item.quantity for item in self.items.all())

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('cart', 'product')

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"

    @property
    def total_price(self):
        return self.product.price * self.quantity
