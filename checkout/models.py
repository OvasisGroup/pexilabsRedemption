from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid
import decimal
from decimal import Decimal
import json

# Import from authentication app
from authentication.models import CustomUser, Merchant, PreferredCurrency


class CheckoutPage(models.Model):
    """Model for merchant checkout pages"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    merchant = models.ForeignKey(Merchant, on_delete=models.CASCADE, related_name='checkout_pages')
    
    # Page Configuration
    name = models.CharField(max_length=200, help_text='Internal name for this checkout page')
    slug = models.SlugField(max_length=200, unique=True, help_text='URL slug for the checkout page')
    title = models.CharField(max_length=200, help_text='Page title displayed to customers')
    description = models.TextField(blank=True, help_text='Description displayed on checkout page')
    
    # Branding
    logo = models.ImageField(upload_to='checkout_logos/', blank=True, null=True)
    primary_color = models.CharField(max_length=7, default='#3B82F6', help_text='Primary brand color (hex)')
    secondary_color = models.CharField(max_length=7, default='#1E40AF', help_text='Secondary brand color (hex)')
    background_color = models.CharField(max_length=7, default='#F8FAFC', help_text='Background color (hex)')
    
    # Payment Settings
    currency = models.ForeignKey(PreferredCurrency, on_delete=models.CASCADE, default=None)
    min_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('1.00'))
    max_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('10000.00'))
    allow_custom_amount = models.BooleanField(default=True, help_text='Allow customers to enter custom amounts')
    
    # Page Settings
    is_active = models.BooleanField(default=True)
    require_customer_info = models.BooleanField(default=True, help_text='Require customer email and name')
    require_billing_address = models.BooleanField(default=False, help_text='Require billing address')
    require_shipping_address = models.BooleanField(default=False, help_text='Require shipping address')
    
    # Success/Cancel URLs
    success_url = models.URLField(blank=True, help_text='Redirect URL after successful payment')
    cancel_url = models.URLField(blank=True, help_text='Redirect URL after cancelled payment')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Checkout Page'
        verbose_name_plural = 'Checkout Pages'
        unique_together = [['merchant', 'name']]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.merchant.business_name} - {self.name}"
    
    def get_absolute_url(self):
        return f"/checkout/{self.slug}/"


class PaymentMethodConfig(models.Model):
    """Configuration for payment methods on checkout pages"""
    
    PAYMENT_METHOD_CHOICES = [
        ('visa', 'Visa'),
        ('mastercard', 'Mastercard'),
        ('amex', 'American Express'),
        ('discover', 'Discover'),
        ('paypal', 'PayPal'),
        ('apple_pay', 'Apple Pay'),
        ('google_pay', 'Google Pay'),
        ('bank_transfer', 'Bank Transfer'),
        ('crypto', 'Cryptocurrency'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    checkout_page = models.ForeignKey(CheckoutPage, on_delete=models.CASCADE, related_name='payment_methods')
    payment_method = models.CharField(max_length=50, choices=PAYMENT_METHOD_CHOICES)
    is_enabled = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)
    
    # Method-specific configuration
    gateway_config = models.JSONField(default=dict, blank=True, help_text='Gateway-specific configuration')
    
    # Display settings
    display_name = models.CharField(max_length=100, blank=True, help_text='Custom display name')
    icon_override = models.ImageField(upload_to='payment_method_icons/', blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Payment Method Configuration'
        verbose_name_plural = 'Payment Method Configurations'
        unique_together = [['checkout_page', 'payment_method']]
        ordering = ['display_order', 'payment_method']
    
    def __str__(self):
        return f"{self.checkout_page.name} - {self.get_payment_method_display()}"
    
    def get_display_name(self):
        return self.display_name or self.get_payment_method_display()
    
    def get_icon_url(self):
        if self.icon_override:
            return self.icon_override.url
        # Return default icon URL based on payment method
        return f"/static/images/payment_methods/{self.payment_method}.svg"


class CheckoutSession(models.Model):
    """Model to track checkout sessions"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    checkout_page = models.ForeignKey(CheckoutPage, on_delete=models.CASCADE, related_name='sessions')
    
    # Session data
    session_token = models.CharField(max_length=255, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.ForeignKey(PreferredCurrency, on_delete=models.CASCADE)
    
    # Customer information
    customer_email = models.EmailField()
    customer_name = models.CharField(max_length=200, blank=True)
    customer_phone = models.CharField(max_length=20, blank=True)
    
    # Address information
    billing_address = models.JSONField(default=dict, blank=True)
    shipping_address = models.JSONField(default=dict, blank=True)
    
    # Payment details
    selected_payment_method = models.CharField(max_length=50, blank=True)
    payment_reference = models.CharField(max_length=255, blank=True)
    
    # Status and tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    expires_at = models.DateTimeField()
    completed_at = models.DateTimeField(blank=True, null=True)
    
    # Metadata
    metadata = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Checkout Session'
        verbose_name_plural = 'Checkout Sessions'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Session {self.session_token[:8]}... - {self.status}"
    
    def is_expired(self):
        return timezone.now() > self.expires_at
    
    def generate_session_token(self):
        """Generate a unique session token"""
        import secrets
        return secrets.token_urlsafe(32)
    
    def save(self, *args, **kwargs):
        if not self.session_token:
            self.session_token = self.generate_session_token()
        if not self.expires_at:
            # Session expires in 1 hour by default
            self.expires_at = timezone.now() + timezone.timedelta(hours=1)
        super().save(*args, **kwargs)
