from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
import uuid
import json
from decimal import Decimal
from datetime import timedelta
from cryptography.fernet import Fernet
from django.conf import settings

# Import from authentication app
from authentication.models import Merchant, PreferredCurrency


class IntegrationType(models.TextChoices):
    """Types of integrations available"""
    BANK = 'bank', 'Bank Integration'
    PAYMENT_GATEWAY = 'payment_gateway', 'Payment Gateway'
    SMS = 'sms', 'SMS Service'
    EMAIL = 'email', 'Email Service'
    KYC = 'kyc', 'KYC/Identity Verification'
    ACCOUNTING = 'accounting', 'Accounting Software'
    CRM = 'crm', 'Customer Relationship Management'
    ANALYTICS = 'analytics', 'Analytics Platform'
    # Specific provider types
    UBA_BANK = 'uba_bank', 'UBA Bank Integration'
    CYBERSOURCE = 'cybersource', 'CyberSource Payment Gateway'
    COREFY = 'corefy', 'Corefy Payment Platform'
    UNIWIRE = 'uniwire', 'Uniwire Cryptocurrency Integration'
    STRIPE = 'stripe', 'Stripe Payment Gateway'
    PAYPAL = 'paypal', 'PayPal Integration'
    FLUTTERWAVE = 'flutterwave', 'Flutterwave Payment Gateway'
    PAYSTACK = 'paystack', 'Paystack Payment Gateway'
    MPESA = 'mpesa', 'M-Pesa Mobile Money'
    TRANSVOUCHER = 'transvoucher', 'TransVoucher Payment Gateway'
    BLOCKCHAIN = 'blockchain', 'Blockchain Integration'
    AI_SERVICE = 'ai_service', 'AI/ML Service'
    LOGISTICS = 'logistics', 'Logistics Provider'
    SOCIAL_MEDIA = 'social_media', 'Social Media Platform'
    MESSAGING = 'messaging', 'Messaging Service'
    CUSTOM_API = 'custom_api', 'Custom API Integration'
    OTHER = 'other', 'Other Integration'


class IntegrationStatus(models.TextChoices):
    """Integration status choices"""
    DRAFT = 'draft', 'Draft'
    ACTIVE = 'active', 'Active'
    INACTIVE = 'inactive', 'Inactive'
    ERROR = 'error', 'Error'
    SUSPENDED = 'suspended', 'Suspended'
    TESTING = 'testing', 'Testing'


class AuthenticationType(models.TextChoices):
    """Authentication types for integrations"""
    API_KEY = 'api_key', 'API Key'
    BEARER_TOKEN = 'bearer_token', 'Bearer Token'
    OAUTH2 = 'oauth2', 'OAuth 2.0'
    BASIC_AUTH = 'basic_auth', 'Basic Authentication'
    JWT = 'jwt', 'JWT Token'
    CUSTOM = 'custom', 'Custom Authentication'


class Integration(models.Model):
    """Base model for all integrations"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Basic information
    name = models.CharField(max_length=100, help_text='Integration name')
    code = models.CharField(max_length=50, unique=True, help_text='Unique integration code')
    description = models.TextField(blank=True, help_text='Integration description')
    integration_type = models.CharField(
        max_length=20,
        choices=IntegrationType.choices,
        default=IntegrationType.OTHER
    )
    
    # Provider information
    provider_name = models.CharField(max_length=100, help_text='Service provider name')
    provider_website = models.URLField(blank=True, help_text='Provider website')
    provider_documentation = models.URLField(blank=True, help_text='API documentation URL')
    
    # Configuration
    base_url = models.URLField(help_text='Base API URL')
    is_sandbox = models.BooleanField(default=True, help_text='Whether this is a sandbox environment')
    version = models.CharField(max_length=20, default='v1', help_text='API version')
    
    # Authentication
    authentication_type = models.CharField(
        max_length=20,
        choices=AuthenticationType.choices,
        default=AuthenticationType.API_KEY
    )
    
    # Capabilities
    supports_webhooks = models.BooleanField(default=False)
    supports_bulk_operations = models.BooleanField(default=False)
    supports_real_time = models.BooleanField(default=False)
    
    # Rate limiting
    rate_limit_per_minute = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text='API calls allowed per minute'
    )
    rate_limit_per_hour = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text='API calls allowed per hour'
    )
    rate_limit_per_day = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text='API calls allowed per day'
    )
    
    # Status and settings
    status = models.CharField(
        max_length=20,
        choices=IntegrationStatus.choices,
        default=IntegrationStatus.DRAFT
    )
    is_global = models.BooleanField(
        default=False,
        help_text='Whether this integration is available to all merchants'
    )
    
    # Health monitoring
    last_health_check = models.DateTimeField(null=True, blank=True)
    health_check_interval = models.PositiveIntegerField(
        default=300,
        help_text='Health check interval in seconds'
    )
    is_healthy = models.BooleanField(default=True)
    health_error_message = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Integration'
        verbose_name_plural = 'Integrations'
        ordering = ['provider_name', 'name']
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['integration_type', 'status']),
            models.Index(fields=['status', 'is_global']),
        ]
    
    def __str__(self):
        return f"{self.provider_name} - {self.name}"
    
    def is_active(self):
        """Check if integration is active and healthy"""
        return self.status == IntegrationStatus.ACTIVE and self.is_healthy
    
    def needs_health_check(self):
        """Check if health check is needed"""
        if not self.last_health_check:
            return True
        
        next_check = self.last_health_check + timedelta(seconds=self.health_check_interval)
        return timezone.now() >= next_check


class MerchantIntegration(models.Model):
    """Merchant-specific integration configurations"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    merchant = models.ForeignKey(
        Merchant,
        on_delete=models.CASCADE,
        related_name='integrations'
    )
    integration = models.ForeignKey(
        Integration,
        on_delete=models.CASCADE,
        related_name='merchant_configurations'
    )
    
    # Status
    is_enabled = models.BooleanField(default=False)
    status = models.CharField(
        max_length=20,
        choices=IntegrationStatus.choices,
        default=IntegrationStatus.DRAFT
    )
    
    # Configuration
    configuration = models.JSONField(
        default=dict,
        help_text='Merchant-specific configuration settings'
    )
    
    # Authentication credentials (encrypted)
    credentials = models.TextField(
        blank=True,
        help_text='Encrypted authentication credentials'
    )
    
    # Usage tracking
    total_requests = models.PositiveIntegerField(default=0)
    successful_requests = models.PositiveIntegerField(default=0)
    failed_requests = models.PositiveIntegerField(default=0)
    last_used_at = models.DateTimeField(null=True, blank=True)
    
    # Error tracking
    consecutive_failures = models.PositiveIntegerField(default=0)
    last_error_message = models.TextField(blank=True)
    last_error_at = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Merchant Integration'
        verbose_name_plural = 'Merchant Integrations'
        unique_together = ['merchant', 'integration']
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['merchant', 'is_enabled']),
            models.Index(fields=['integration', 'status']),
        ]
    
    def __str__(self):
        return f"{self.merchant.business_name} - {self.integration.name}"
    
    def encrypt_credentials(self, credentials_dict):
        """Encrypt and store credentials"""
        if not hasattr(settings, 'ENCRYPTION_KEY'):
            raise ValueError("ENCRYPTION_KEY not configured in settings")
        
        fernet = Fernet(settings.ENCRYPTION_KEY.encode())
        credentials_json = json.dumps(credentials_dict)
        encrypted_credentials = fernet.encrypt(credentials_json.encode())
        self.credentials = encrypted_credentials.decode()
        self.save(update_fields=['credentials', 'updated_at'])
    
    def decrypt_credentials(self):
        """Decrypt and return credentials"""
        if not self.credentials:
            return {}
        
        if not hasattr(settings, 'ENCRYPTION_KEY'):
            raise ValueError("ENCRYPTION_KEY not configured in settings")
        
        try:
            fernet = Fernet(settings.ENCRYPTION_KEY.encode())
            decrypted_data = fernet.decrypt(self.credentials.encode())
            return json.loads(decrypted_data.decode())
        except Exception as e:
            raise ValueError(f"Failed to decrypt credentials: {str(e)}")
    
    def record_success(self):
        """Record a successful API call"""
        self.total_requests += 1
        self.successful_requests += 1
        self.consecutive_failures = 0
        self.last_used_at = timezone.now()
        self.save(update_fields=[
            'total_requests', 'successful_requests', 'consecutive_failures',
            'last_used_at', 'updated_at'
        ])
    
    def record_failure(self, error_message=""):
        """Record a failed API call"""
        self.total_requests += 1
        self.failed_requests += 1
        self.consecutive_failures += 1
        self.last_error_message = error_message
        self.last_error_at = timezone.now()
        self.last_used_at = timezone.now()
        self.save(update_fields=[
            'total_requests', 'failed_requests', 'consecutive_failures',
            'last_error_message', 'last_error_at', 'last_used_at', 'updated_at'
        ])
    
    def get_success_rate(self):
        """Calculate success rate percentage"""
        if self.total_requests == 0:
            return 0
        return round((self.successful_requests / self.total_requests) * 100, 2)
    
    def is_healthy(self):
        """Check if integration is healthy"""
        return (
            self.is_enabled and
            self.status == IntegrationStatus.ACTIVE and
            self.consecutive_failures < 5  # Threshold for unhealthy
        )


class BankIntegration(models.Model):
    """Specific model for bank integrations"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    integration = models.OneToOneField(
        Integration,
        on_delete=models.CASCADE,
        related_name='bank_details'
    )
    
    # Bank-specific information
    bank_name = models.CharField(max_length=100)
    bank_code = models.CharField(max_length=20, unique=True)
    country_code = models.CharField(max_length=2, help_text='ISO country code')
    swift_code = models.CharField(max_length=11, blank=True)
    
    # Supported services
    supports_account_inquiry = models.BooleanField(default=False)
    supports_balance_inquiry = models.BooleanField(default=False)
    supports_transaction_history = models.BooleanField(default=False)
    supports_fund_transfer = models.BooleanField(default=False)
    supports_bill_payment = models.BooleanField(default=False)
    supports_standing_orders = models.BooleanField(default=False)
    supports_direct_debit = models.BooleanField(default=False)
    
    # Supported currencies
    supported_currencies = models.ManyToManyField(
        PreferredCurrency,
        blank=True,
        related_name='supported_by_banks'
    )
    
    # Transaction limits
    min_transfer_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('1.00')
    )
    max_transfer_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('1000000.00')
    )
    daily_transfer_limit = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True
    )
    
    # Fee structure
    transfer_fee_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=Decimal('0.0000'),
        help_text='Transfer fee as percentage'
    )
    transfer_fee_fixed = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Fixed transfer fee amount'
    )
    inquiry_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Fee for account/balance inquiries'
    )
    
    # Operating hours
    operating_hours_start = models.TimeField(null=True, blank=True)
    operating_hours_end = models.TimeField(null=True, blank=True)
    operates_weekends = models.BooleanField(default=False)
    operates_holidays = models.BooleanField(default=False)
    
    # Settlement information
    settlement_time = models.PositiveIntegerField(
        default=24,
        help_text='Settlement time in hours'
    )
    settlement_currency = models.ForeignKey(
        PreferredCurrency,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='settlement_for_banks'
    )
    
    class Meta:
        verbose_name = 'Bank Integration'
        verbose_name_plural = 'Bank Integrations'
        ordering = ['bank_name']
    
    def __str__(self):
        return f"{self.bank_name} ({self.bank_code})"
    
    def calculate_transfer_fee(self, amount):
        """Calculate transfer fee for given amount"""
        percentage_fee = amount * self.transfer_fee_percentage
        total_fee = percentage_fee + self.transfer_fee_fixed
        return {
            'percentage_fee': percentage_fee,
            'fixed_fee': self.transfer_fee_fixed,
            'total_fee': total_fee,
            'net_amount': amount - total_fee
        }
    
    def is_operating_now(self):
        """Check if bank is currently operating"""
        now = timezone.now()
        current_time = now.time()
        current_weekday = now.weekday()  # 0 = Monday, 6 = Sunday
        
        # Check weekend operations
        if current_weekday >= 5 and not self.operates_weekends:  # Saturday (5) or Sunday (6)
            return False
        
        # Check operating hours
        if self.operating_hours_start and self.operating_hours_end:
            return self.operating_hours_start <= current_time <= self.operating_hours_end
        
        return True  # If no hours specified, assume 24/7


class IntegrationProvider(models.Model):
    """Model for specific integration provider configurations"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    integration = models.OneToOneField(
        Integration,
        on_delete=models.CASCADE,
        related_name='provider_config'
    )
    
    # Provider-specific configuration
    provider_config = models.JSONField(
        default=dict,
        help_text='Provider-specific configuration and capabilities'
    )
    
    # API endpoints configuration
    endpoints = models.JSONField(
        default=dict,
        help_text='API endpoints mapping for different operations'
    )
    
    # Supported operations
    supported_operations = models.JSONField(
        default=list,
        help_text='List of supported operations for this provider'
    )
    
    # Fee structure
    fee_structure = models.JSONField(
        default=dict,
        help_text='Fee structure for different operations'
    )
    
    # Limits and constraints
    limits = models.JSONField(
        default=dict,
        help_text='Transaction limits and constraints'
    )
    
    # Webhook configuration
    webhook_config = models.JSONField(
        default=dict,
        help_text='Webhook configuration and event types'
    )
    
    # Environment-specific settings
    sandbox_config = models.JSONField(
        default=dict,
        help_text='Sandbox environment specific configuration'
    )
    production_config = models.JSONField(
        default=dict,
        help_text='Production environment specific configuration'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Integration Provider'
        verbose_name_plural = 'Integration Providers'
        ordering = ['integration__provider_name']
    
    def __str__(self):
        return f"{self.integration.provider_name} - {self.integration.name} Config"
    
    def get_endpoint(self, operation):
        """Get endpoint URL for specific operation"""
        return self.endpoints.get(operation)
    
    def supports_operation(self, operation):
        """Check if provider supports specific operation"""
        return operation in self.supported_operations
    
    def get_fee_for_operation(self, operation, amount=None):
        """Calculate fee for specific operation"""
        fee_config = self.fee_structure.get(operation, {})
        if not fee_config:
            return Decimal('0.00')
        
        fixed_fee = Decimal(str(fee_config.get('fixed', '0.00')))
        percentage = Decimal(str(fee_config.get('percentage', '0.00')))
        
        if amount and percentage > 0:
            percentage_fee = amount * (percentage / 100)
            return fixed_fee + percentage_fee
        
        return fixed_fee
    
    def get_limit(self, limit_type):
        """Get specific limit value"""
        return self.limits.get(limit_type)
    
    def get_config_for_environment(self, is_sandbox=True):
        """Get configuration for specific environment"""
        if is_sandbox:
            return {**self.provider_config, **self.sandbox_config}
        return {**self.provider_config, **self.production_config}


class IntegrationAPICall(models.Model):
    """Model to log API calls made to integrations"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    merchant_integration = models.ForeignKey(
        MerchantIntegration,
        on_delete=models.CASCADE,
        related_name='api_calls'
    )
    
    # Request details
    method = models.CharField(max_length=10, help_text='HTTP method')
    endpoint = models.CharField(max_length=255, help_text='API endpoint called')
    request_headers = models.JSONField(default=dict, blank=True)
    request_body = models.TextField(blank=True)
    
    # Response details
    status_code = models.PositiveIntegerField(null=True, blank=True)
    response_headers = models.JSONField(default=dict, blank=True)
    response_body = models.TextField(blank=True)
    response_time_ms = models.PositiveIntegerField(null=True, blank=True)
    
    # Metadata
    operation_type = models.CharField(
        max_length=50,
        help_text='Type of operation (transfer, inquiry, etc.)'
    )
    reference_id = models.CharField(
        max_length=100,
        blank=True,
        help_text='Reference ID for the operation'
    )
    
    # Success/failure tracking
    is_successful = models.BooleanField(default=False)
    error_message = models.TextField(blank=True)
    error_code = models.CharField(max_length=50, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Integration API Call'
        verbose_name_plural = 'Integration API Calls'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['merchant_integration', 'created_at']),
            models.Index(fields=['operation_type', 'is_successful']),
            models.Index(fields=['reference_id']),
        ]
    
    def __str__(self):
        return f"{self.method} {self.endpoint} - {self.status_code}"


class IntegrationWebhook(models.Model):
    """Model to handle webhooks from integrations"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    integration = models.ForeignKey(
        Integration,
        on_delete=models.CASCADE,
        related_name='webhooks'
    )
    
    # Webhook details
    event_type = models.CharField(max_length=50, help_text='Type of webhook event')
    payload = models.JSONField(help_text='Webhook payload')
    headers = models.JSONField(default=dict, help_text='Request headers')
    
    # Processing
    is_processed = models.BooleanField(default=False)
    processed_at = models.DateTimeField(null=True, blank=True)
    processing_error = models.TextField(blank=True)
    
    # Verification
    is_verified = models.BooleanField(default=False)
    verification_method = models.CharField(
        max_length=50,
        blank=True,
        help_text='Method used to verify webhook (signature, token, etc.)'
    )
    
    # Metadata
    source_ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Integration Webhook'
        verbose_name_plural = 'Integration Webhooks'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['integration', 'event_type']),
            models.Index(fields=['is_processed', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.integration.name} - {self.event_type}"
    
    def mark_as_processed(self, error_message=""):
        """Mark webhook as processed"""
        self.is_processed = True
        self.processed_at = timezone.now()
        if error_message:
            self.processing_error = error_message
        self.save(update_fields=['is_processed', 'processed_at', 'processing_error'])
