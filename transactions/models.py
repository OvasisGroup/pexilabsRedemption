from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid
import decimal
from decimal import Decimal
import hashlib
import secrets
import json

# Import from authentication app
from authentication.models import CustomUser, Merchant, PreferredCurrency


class PaymentMethod(models.TextChoices):
    """Payment method choices"""
    BANK_TRANSFER = 'bank_transfer', 'Bank Transfer'
    CARD = 'card', 'Card Payment'
    MOBILE_MONEY = 'mobile_money', 'Mobile Money'
    WALLET = 'wallet', 'Digital Wallet'
    CRYPTO = 'crypto', 'Cryptocurrency'
    CASH = 'cash', 'Cash'
    OTHER = 'other', 'Other'


class TransactionType(models.TextChoices):
    """Transaction type choices"""
    PAYMENT = 'payment', 'Payment'
    REFUND = 'refund', 'Refund'
    PAYOUT = 'payout', 'Payout'
    TRANSFER = 'transfer', 'Transfer'
    FEE = 'fee', 'Fee'
    REVERSAL = 'reversal', 'Reversal'
    CHARGEBACK = 'chargeback', 'Chargeback'
    ADJUSTMENT = 'adjustment', 'Adjustment'


class TransactionStatus(models.TextChoices):
    """Transaction status choices"""
    PENDING = 'pending', 'Pending'
    PROCESSING = 'processing', 'Processing'
    COMPLETED = 'completed', 'Completed'
    FAILED = 'failed', 'Failed'
    CANCELLED = 'cancelled', 'Cancelled'
    EXPIRED = 'expired', 'Expired'
    REFUNDED = 'refunded', 'Refunded'
    PARTIALLY_REFUNDED = 'partially_refunded', 'Partially Refunded'
    DISPUTED = 'disputed', 'Disputed'
    FROZEN = 'frozen', 'Frozen'


class PaymentGateway(models.Model):
    """Model for payment gateway configurations"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True, help_text='Gateway name')
    code = models.CharField(max_length=50, unique=True, help_text='Gateway code identifier')
    description = models.TextField(blank=True)
    
    # Gateway configuration
    api_endpoint = models.URLField(help_text='Gateway API endpoint')
    webhook_endpoint = models.URLField(blank=True, help_text='Webhook endpoint for notifications')
    public_key = models.TextField(blank=True, help_text='Public API key')
    private_key = models.TextField(blank=True, help_text='Private API key (encrypted)')
    merchant_id = models.CharField(max_length=100, blank=True, help_text='Merchant ID with gateway')
    
    # Supported features
    supports_payments = models.BooleanField(default=True)
    supports_refunds = models.BooleanField(default=True)
    supports_payouts = models.BooleanField(default=False)
    supports_webhooks = models.BooleanField(default=True)
    supports_recurring = models.BooleanField(default=False)
    
    # Supported payment methods
    supported_payment_methods = models.TextField(
        default='card,bank_transfer',
        help_text='Comma-separated list of supported payment methods'
    )
    supported_currencies = models.TextField(
        default='USD,EUR,GBP',
        help_text='Comma-separated list of supported currency codes'
    )
    
    # Limits and fees
    min_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.01'),
        help_text='Minimum transaction amount'
    )
    max_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('100000.00'),
        help_text='Maximum transaction amount'
    )
    transaction_fee_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=Decimal('0.0290'),
        help_text='Transaction fee percentage (e.g., 2.9% = 0.0290)'
    )
    transaction_fee_fixed = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.30'),
        help_text='Fixed transaction fee amount'
    )
    
    # Status and settings
    is_active = models.BooleanField(default=True)
    is_sandbox = models.BooleanField(default=False, help_text='Whether this is a sandbox/test gateway')
    priority = models.PositiveIntegerField(default=1, help_text='Gateway priority (lower = higher priority)')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Payment Gateway'
        verbose_name_plural = 'Payment Gateways'
        ordering = ['priority', 'name']
    
    def __str__(self):
        return f"{self.name} {'(Sandbox)' if self.is_sandbox else ''}"
    
    def get_supported_payment_methods_list(self):
        """Return list of supported payment methods"""
        return [method.strip() for method in self.supported_payment_methods.split(',') if method.strip()]
    
    def get_supported_currencies_list(self):
        """Return list of supported currencies"""
        return [currency.strip() for currency in self.supported_currencies.split(',') if currency.strip()]
    
    def supports_payment_method(self, method):
        """Check if gateway supports a payment method"""
        return method in self.get_supported_payment_methods_list()
    
    def supports_currency(self, currency_code):
        """Check if gateway supports a currency"""
        return currency_code in self.get_supported_currencies_list()
    
    def calculate_fees(self, amount):
        """Calculate transaction fees for given amount"""
        percentage_fee = amount * self.transaction_fee_percentage
        total_fee = percentage_fee + self.transaction_fee_fixed
        return {
            'percentage_fee': percentage_fee,
            'fixed_fee': self.transaction_fee_fixed,
            'total_fee': total_fee,
            'net_amount': amount - total_fee
        }


class Transaction(models.Model):
    """Main transaction model"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Transaction identification
    reference = models.CharField(
        max_length=100,
        unique=True,
        help_text='Unique transaction reference'
    )
    external_reference = models.CharField(
        max_length=255,
        blank=True,
        help_text='External system reference (e.g., gateway transaction ID)'
    )
    
    # Parties involved
    merchant = models.ForeignKey(
        Merchant,
        on_delete=models.CASCADE,
        related_name='transactions',
        help_text='Merchant processing the transaction'
    )
    customer = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transactions',
        help_text='Customer making the payment (optional for guest payments)'
    )
    customer_email = models.EmailField(
        blank=True,
        help_text='Customer email for guest transactions'
    )
    customer_phone = models.CharField(
        max_length=20,
        blank=True,
        help_text='Customer phone number'
    )
    
    # Transaction details
    transaction_type = models.CharField(
        max_length=20,
        choices=TransactionType.choices,
        default=TransactionType.PAYMENT
    )
    status = models.CharField(
        max_length=20,
        choices=TransactionStatus.choices,
        default=TransactionStatus.PENDING
    )
    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices
    )
    gateway = models.ForeignKey(
        PaymentGateway,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transactions'
    )
    
    # Amount details
    currency = models.ForeignKey(
        PreferredCurrency,
        on_delete=models.PROTECT,
        related_name='transactions'
    )
    amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text='Transaction amount'
    )
    fee_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Transaction fee amount'
    )
    net_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        help_text='Net amount after fees'
    )
    
    # Exchange rate handling (for multi-currency)
    original_currency = models.CharField(
        max_length=3,
        blank=True,
        help_text='Original currency if converted'
    )
    original_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Original amount before currency conversion'
    )
    exchange_rate = models.DecimalField(
        max_digits=10,
        decimal_places=6,
        null=True,
        blank=True,
        help_text='Exchange rate used for conversion'
    )
    
    # Description and metadata
    description = models.TextField(blank=True, help_text='Transaction description')
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text='Additional transaction metadata'
    )
    
    # Payment details
    payment_details = models.JSONField(
        default=dict,
        blank=True,
        help_text='Payment-specific details (card last 4, bank details, etc.)'
    )
    
    # Status tracking
    processed_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    # Failure information
    failure_reason = models.TextField(blank=True)
    failure_code = models.CharField(max_length=50, blank=True)
    
    # Settlement information
    settlement_date = models.DateField(null=True, blank=True)
    settlement_reference = models.CharField(max_length=100, blank=True)
    is_settled = models.BooleanField(default=False)
    
    # Parent/child relationship for refunds, chargebacks, etc.
    parent_transaction = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='child_transactions'
    )
    
    # Security and fraud
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    risk_score = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text='Risk score from 0-100'
    )
    is_flagged = models.BooleanField(default=False, help_text='Flagged for manual review')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Transaction'
        verbose_name_plural = 'Transactions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['reference']),
            models.Index(fields=['external_reference']),
            models.Index(fields=['merchant', 'status']),
            models.Index(fields=['customer', 'status']),
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['gateway', 'status']),
            models.Index(fields=['settlement_date']),
        ]
    
    def __str__(self):
        return f"{self.reference} - {self.amount} {self.currency.code} ({self.get_status_display()})"
    
    def save(self, *args, **kwargs):
        """Override save to generate reference and calculate net amount"""
        if not self.reference:
            self.reference = self.generate_reference()
        
        # Calculate net amount if not set
        if self.net_amount is None:
            self.net_amount = self.amount - self.fee_amount
        
        super().save(*args, **kwargs)
    
    def generate_reference(self):
        """Generate unique transaction reference"""
        prefix = f"TXN{self.transaction_type[:3].upper()}"
        timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
        random_suffix = secrets.token_hex(4).upper()
        return f"{prefix}{timestamp}{random_suffix}"
    
    def can_refund(self):
        """Check if transaction can be refunded"""
        return (
            self.status == TransactionStatus.COMPLETED and
            self.transaction_type == TransactionType.PAYMENT and
            not self.child_transactions.filter(
                transaction_type=TransactionType.REFUND,
                status__in=[TransactionStatus.COMPLETED, TransactionStatus.PROCESSING]
            ).exists()
        )
    
    def get_refunded_amount(self):
        """Get total amount refunded for this transaction"""
        refunds = self.child_transactions.filter(
            transaction_type=TransactionType.REFUND,
            status=TransactionStatus.COMPLETED
        )
        return sum(refund.amount for refund in refunds)
    
    def get_remaining_refundable_amount(self):
        """Get remaining amount that can be refunded"""
        if not self.can_refund():
            return Decimal('0.00')
        return self.amount - self.get_refunded_amount()
    
    def mark_as_processing(self):
        """Mark transaction as processing"""
        self.status = TransactionStatus.PROCESSING
        self.processed_at = timezone.now()
        self.save(update_fields=['status', 'processed_at', 'updated_at'])
    
    def mark_as_completed(self):
        """Mark transaction as completed"""
        self.status = TransactionStatus.COMPLETED
        self.completed_at = timezone.now()
        self.save(update_fields=['status', 'completed_at', 'updated_at'])
    
    def mark_as_failed(self, reason="", code=""):
        """Mark transaction as failed"""
        self.status = TransactionStatus.FAILED
        self.failed_at = timezone.now()
        self.failure_reason = reason
        self.failure_code = code
        self.save(update_fields=['status', 'failed_at', 'failure_reason', 'failure_code', 'updated_at'])
    
    def mark_as_settled(self, settlement_reference="", settlement_date=None):
        """Mark transaction as settled"""
        self.is_settled = True
        self.settlement_reference = settlement_reference
        self.settlement_date = settlement_date or timezone.now().date()
        self.save(update_fields=['is_settled', 'settlement_reference', 'settlement_date', 'updated_at'])
    
    def create_refund(self, amount, reason="", created_by=None):
        """Create a refund transaction"""
        if not self.can_refund():
            raise ValidationError("Transaction cannot be refunded")
        
        if amount > self.get_remaining_refundable_amount():
            raise ValidationError("Refund amount exceeds remaining refundable amount")
        
        refund = Transaction.objects.create(
            merchant=self.merchant,
            customer=self.customer,
            customer_email=self.customer_email,
            transaction_type=TransactionType.REFUND,
            payment_method=self.payment_method,
            gateway=self.gateway,
            currency=self.currency,
            amount=amount,
            net_amount=amount,
            description=f"Refund for {self.reference}: {reason}",
            parent_transaction=self,
            metadata={'refund_reason': reason, 'created_by': str(created_by) if created_by else None}
        )
        
        return refund
    
    def get_transaction_hash(self):
        """Generate hash for transaction integrity verification"""
        data = f"{self.reference}{self.amount}{self.currency.code}{self.merchant.id}{self.created_at}"
        return hashlib.sha256(data.encode()).hexdigest()
    
    @classmethod
    def get_merchant_stats(cls, merchant, start_date=None, end_date=None):
        """Get transaction statistics for a merchant"""
        queryset = cls.objects.filter(merchant=merchant)
        
        if start_date:
            queryset = queryset.filter(created_at__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__lte=end_date)
        
        total_transactions = queryset.count()
        completed_transactions = queryset.filter(status=TransactionStatus.COMPLETED).count()
        failed_transactions = queryset.filter(status=TransactionStatus.FAILED).count()
        
        total_volume = sum(
            t.amount for t in queryset.filter(
                status=TransactionStatus.COMPLETED,
                transaction_type=TransactionType.PAYMENT
            )
        )
        
        total_fees = sum(
            t.fee_amount for t in queryset.filter(status=TransactionStatus.COMPLETED)
        )
        
        success_rate = (completed_transactions / total_transactions * 100) if total_transactions > 0 else 0
        
        return {
            'total_transactions': total_transactions,
            'completed_transactions': completed_transactions,
            'failed_transactions': failed_transactions,
            'success_rate': round(success_rate, 2),
            'total_volume': total_volume,
            'total_fees': total_fees,
            'net_volume': total_volume - total_fees
        }


class PaymentLink(models.Model):
    """Model for payment links that can be shared with customers"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Basic information
    merchant = models.ForeignKey(
        Merchant,
        on_delete=models.CASCADE,
        related_name='payment_links'
    )
    title = models.CharField(max_length=255, help_text='Payment link title')
    description = models.TextField(blank=True, help_text='Payment description')
    
    # Amount details
    currency = models.ForeignKey(
        PreferredCurrency,
        on_delete=models.PROTECT,
        related_name='payment_links'
    )
    amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text='Payment amount'
    )
    is_amount_flexible = models.BooleanField(
        default=False,
        help_text='Allow customers to change the amount'
    )
    min_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Minimum amount (if flexible)'
    )
    max_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Maximum amount (if flexible)'
    )
    
    # Link settings
    slug = models.CharField(
        max_length=100,
        unique=True,
        help_text='Unique slug for the payment link'
    )
    is_active = models.BooleanField(default=True)
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When this payment link expires'
    )
    max_uses = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text='Maximum number of times this link can be used'
    )
    current_uses = models.PositiveIntegerField(default=0)
    
    # Customer information requirements
    require_name = models.BooleanField(default=True)
    require_email = models.BooleanField(default=True)
    require_phone = models.BooleanField(default=False)
    require_address = models.BooleanField(default=False)
    
    # Payment settings
    allowed_payment_methods = models.TextField(
        default='card,bank_transfer',
        help_text='Comma-separated list of allowed payment methods'
    )
    success_url = models.URLField(
        blank=True,
        help_text='URL to redirect after successful payment'
    )
    cancel_url = models.URLField(
        blank=True,
        help_text='URL to redirect after cancelled payment'
    )
    
    # Metadata
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text='Additional metadata'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Payment Link'
        verbose_name_plural = 'Payment Links'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.amount} {self.currency.code}"
    
    def save(self, *args, **kwargs):
        """Override save to generate slug"""
        if not self.slug:
            self.slug = self.generate_slug()
        super().save(*args, **kwargs)
    
    def generate_slug(self):
        """Generate unique slug for payment link"""
        base_slug = f"pay-{secrets.token_urlsafe(8)}"
        while PaymentLink.objects.filter(slug=base_slug).exists():
            base_slug = f"pay-{secrets.token_urlsafe(8)}"
        return base_slug
    
    def is_expired(self):
        """Check if payment link is expired"""
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False
    
    def is_usage_exceeded(self):
        """Check if usage limit is exceeded"""
        if self.max_uses:
            return self.current_uses >= self.max_uses
        return False
    
    def is_usable(self):
        """Check if payment link can be used"""
        return (
            self.is_active and
            not self.is_expired() and
            not self.is_usage_exceeded()
        )
    
    def get_allowed_payment_methods_list(self):
        """Return list of allowed payment methods"""
        return [method.strip() for method in self.allowed_payment_methods.split(',') if method.strip()]
    
    def increment_usage(self):
        """Increment usage counter"""
        self.current_uses += 1
        self.save(update_fields=['current_uses', 'updated_at'])
    
    def get_absolute_url(self):
        """Return absolute URL for this payment link"""
        # This would be implemented based on your URL structure
        return f"/pay/{self.slug}/"


class TransactionEvent(models.Model):
    """Model to track transaction events and state changes"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    transaction = models.ForeignKey(
        Transaction,
        on_delete=models.CASCADE,
        related_name='events'
    )
    
    event_type = models.CharField(
        max_length=50,
        help_text='Type of event (status_change, webhook_received, etc.)'
    )
    old_status = models.CharField(
        max_length=20,
        choices=TransactionStatus.choices,
        blank=True
    )
    new_status = models.CharField(
        max_length=20,
        choices=TransactionStatus.choices,
        blank=True
    )
    
    description = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    
    # Source of the event
    source = models.CharField(
        max_length=50,
        default='system',
        help_text='Source of the event (system, gateway, admin, etc.)'
    )
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text='User who triggered the event (if applicable)'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Transaction Event'
        verbose_name_plural = 'Transaction Events'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.transaction.reference} - {self.event_type}"


class Webhook(models.Model):
    """Model to track webhook deliveries"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    transaction = models.ForeignKey(
        Transaction,
        on_delete=models.CASCADE,
        related_name='webhooks'
    )
    
    url = models.URLField(help_text='Webhook delivery URL')
    event_type = models.CharField(max_length=50, help_text='Event that triggered the webhook')
    
    # Request details
    payload = models.JSONField(help_text='Webhook payload sent')
    headers = models.JSONField(default=dict, help_text='Headers sent with the webhook')
    
    # Response details
    status_code = models.PositiveIntegerField(null=True, blank=True)
    response_body = models.TextField(blank=True)
    response_time_ms = models.PositiveIntegerField(null=True, blank=True)
    
    # Delivery tracking
    attempts = models.PositiveIntegerField(default=0)
    max_attempts = models.PositiveIntegerField(default=3)
    is_delivered = models.BooleanField(default=False)
    delivered_at = models.DateTimeField(null=True, blank=True)
    next_attempt_at = models.DateTimeField(null=True, blank=True)
    
    # Error tracking
    error_message = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Webhook'
        verbose_name_plural = 'Webhooks'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Webhook for {self.transaction.reference} - {self.event_type}"
    
    def mark_as_delivered(self):
        """Mark webhook as successfully delivered"""
        self.is_delivered = True
        self.delivered_at = timezone.now()
        self.save(update_fields=['is_delivered', 'delivered_at', 'updated_at'])
    
    def schedule_retry(self):
        """Schedule next retry attempt"""
        if self.attempts < self.max_attempts:
            # Exponential backoff: 1min, 5min, 30min
            delay_minutes = [1, 5, 30][min(self.attempts, 2)]
            self.next_attempt_at = timezone.now() + timezone.timedelta(minutes=delay_minutes)
            self.save(update_fields=['next_attempt_at', 'updated_at'])
