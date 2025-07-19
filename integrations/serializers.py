from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal
import json

from .models import (
    Integration,
    MerchantIntegration,
    BankIntegration,
    IntegrationAPICall,
    IntegrationWebhook,
    IntegrationType,
    IntegrationStatus,
    AuthenticationType
)
from authentication.models import Merchant, PreferredCurrency

User = get_user_model()


class IntegrationListSerializer(serializers.ModelSerializer):
    """Serializer for listing integrations"""
    
    class Meta:
        model = Integration
        fields = [
            'id', 'name', 'code', 'provider_name', 'integration_type',
            'status', 'is_sandbox', 'is_global', 'is_healthy',
            'supports_webhooks', 'supports_bulk_operations', 'supports_real_time',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class IntegrationDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for integrations"""
    
    class Meta:
        model = Integration
        fields = [
            'id', 'name', 'code', 'description', 'integration_type',
            'provider_name', 'provider_website', 'provider_documentation',
            'base_url', 'is_sandbox', 'version', 'authentication_type',
            'supports_webhooks', 'supports_bulk_operations', 'supports_real_time',
            'rate_limit_per_minute', 'rate_limit_per_hour', 'rate_limit_per_day',
            'status', 'is_global', 'is_healthy', 'health_check_interval',
            'health_error_message', 'last_health_check',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'last_health_check'
        ]


class BankIntegrationSerializer(serializers.ModelSerializer):
    """Serializer for bank integration details"""
    supported_currencies = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=PreferredCurrency.objects.all()
    )
    settlement_currency = serializers.PrimaryKeyRelatedField(
        queryset=PreferredCurrency.objects.all(),
        allow_null=True,
        required=False
    )
    
    class Meta:
        model = BankIntegration
        fields = [
            'id', 'bank_name', 'bank_code', 'country_code', 'swift_code',
            'supports_account_inquiry', 'supports_balance_inquiry',
            'supports_transaction_history', 'supports_fund_transfer',
            'supports_bill_payment', 'supports_standing_orders',
            'supports_direct_debit', 'supported_currencies',
            'min_transfer_amount', 'max_transfer_amount', 'daily_transfer_limit',
            'transfer_fee_percentage', 'transfer_fee_fixed', 'inquiry_fee',
            'operating_hours_start', 'operating_hours_end',
            'operates_weekends', 'operates_holidays',
            'settlement_time', 'settlement_currency'
        ]
        read_only_fields = ['id']


class MerchantIntegrationListSerializer(serializers.ModelSerializer):
    """Serializer for listing merchant integrations"""
    integration_name = serializers.CharField(source='integration.name', read_only=True)
    integration_type = serializers.CharField(source='integration.integration_type', read_only=True)
    provider_name = serializers.CharField(source='integration.provider_name', read_only=True)
    success_rate = serializers.SerializerMethodField()
    
    class Meta:
        model = MerchantIntegration
        fields = [
            'id', 'integration', 'integration_name', 'integration_type',
            'provider_name', 'is_enabled', 'status', 'total_requests',
            'successful_requests', 'failed_requests', 'success_rate',
            'last_used_at', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'total_requests', 'successful_requests', 'failed_requests',
            'last_used_at', 'created_at', 'updated_at'
        ]
    
    def get_success_rate(self, obj):
        """Calculate success rate"""
        return obj.get_success_rate()


class MerchantIntegrationDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for merchant integrations"""
    integration_details = IntegrationDetailSerializer(source='integration', read_only=True)
    bank_details = BankIntegrationSerializer(source='integration.bank_details', read_only=True)
    success_rate = serializers.SerializerMethodField()
    is_healthy = serializers.SerializerMethodField()
    
    class Meta:
        model = MerchantIntegration
        fields = [
            'id', 'integration', 'integration_details', 'bank_details',
            'is_enabled', 'status', 'configuration',
            'total_requests', 'successful_requests', 'failed_requests',
            'success_rate', 'consecutive_failures', 'last_error_message',
            'last_error_at', 'last_used_at', 'is_healthy',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'total_requests', 'successful_requests', 'failed_requests',
            'consecutive_failures', 'last_error_message', 'last_error_at',
            'last_used_at', 'created_at', 'updated_at'
        ]
    
    def get_success_rate(self, obj):
        """Calculate success rate"""
        return obj.get_success_rate()
    
    def get_is_healthy(self, obj):
        """Check if integration is healthy"""
        return obj.is_healthy()


class MerchantIntegrationCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating merchant integrations"""
    credentials = serializers.JSONField(write_only=True, required=False)
    
    class Meta:
        model = MerchantIntegration
        fields = [
            'integration', 'is_enabled', 'status', 'configuration', 'credentials'
        ]
    
    def create(self, validated_data):
        """Create merchant integration with encrypted credentials"""
        credentials = validated_data.pop('credentials', {})
        merchant = self.context['request'].user.merchant
        
        merchant_integration = MerchantIntegration.objects.create(
            merchant=merchant,
            **validated_data
        )
        
        if credentials:
            merchant_integration.encrypt_credentials(credentials)
        
        return merchant_integration


class MerchantIntegrationUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating merchant integrations"""
    credentials = serializers.JSONField(write_only=True, required=False)
    
    class Meta:
        model = MerchantIntegration
        fields = [
            'is_enabled', 'status', 'configuration', 'credentials'
        ]
    
    def update(self, instance, validated_data):
        """Update merchant integration"""
        credentials = validated_data.pop('credentials', None)
        
        # Update other fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update credentials if provided
        if credentials is not None:
            instance.encrypt_credentials(credentials)
        
        return instance


class IntegrationAPICallSerializer(serializers.ModelSerializer):
    """Serializer for integration API calls"""
    merchant_name = serializers.CharField(
        source='merchant_integration.merchant.business_name',
        read_only=True
    )
    integration_name = serializers.CharField(
        source='merchant_integration.integration.name',
        read_only=True
    )
    
    class Meta:
        model = IntegrationAPICall
        fields = [
            'id', 'merchant_integration', 'merchant_name', 'integration_name',
            'method', 'endpoint', 'operation_type', 'reference_id',
            'status_code', 'response_time_ms', 'is_successful',
            'error_message', 'error_code', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class IntegrationWebhookSerializer(serializers.ModelSerializer):
    """Serializer for integration webhooks"""
    integration_name = serializers.CharField(source='integration.name', read_only=True)
    
    class Meta:
        model = IntegrationWebhook
        fields = [
            'id', 'integration', 'integration_name', 'event_type',
            'payload', 'headers', 'is_processed', 'processed_at',
            'processing_error', 'is_verified', 'verification_method',
            'source_ip', 'user_agent', 'created_at'
        ]
        read_only_fields = [
            'id', 'processed_at', 'created_at'
        ]


class UBAPaymentPageSerializer(serializers.Serializer):
    """Serializer for creating UBA payment pages"""
    amount = serializers.DecimalField(max_digits=15, decimal_places=2, min_value=Decimal('0.01'))
    currency = serializers.CharField(max_length=3, default='KES')
    customer_email = serializers.EmailField(required=False, allow_blank=True)
    customer_phone = serializers.CharField(max_length=20, required=False, allow_blank=True)
    description = serializers.CharField(max_length=255, required=False, allow_blank=True)
    reference = serializers.CharField(max_length=100, required=False, allow_blank=True)
    callback_url = serializers.URLField(required=False, allow_blank=True)
    redirect_url = serializers.URLField(required=False, allow_blank=True)


class UBAAccountInquirySerializer(serializers.Serializer):
    """Serializer for UBA account inquiry"""
    account_number = serializers.CharField(max_length=20)
    bank_code = serializers.CharField(max_length=10, required=False, default='UBA_KE')


class UBAFundTransferSerializer(serializers.Serializer):
    """Serializer for UBA fund transfer"""
    amount = serializers.DecimalField(max_digits=15, decimal_places=2, min_value=Decimal('0.01'))
    source_account = serializers.CharField(max_length=20)
    destination_account = serializers.CharField(max_length=20)
    destination_bank_code = serializers.CharField(max_length=10)
    narration = serializers.CharField(max_length=255, required=False, allow_blank=True)
    reference = serializers.CharField(max_length=100, required=False, allow_blank=True)


class UBABalanceInquirySerializer(serializers.Serializer):
    """Serializer for UBA balance inquiry"""
    account_number = serializers.CharField(max_length=20)


class UBATransactionHistorySerializer(serializers.Serializer):
    """Serializer for UBA transaction history"""
    account_number = serializers.CharField(max_length=20)
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)
    limit = serializers.IntegerField(min_value=1, max_value=100, default=50)


class UBABillPaymentSerializer(serializers.Serializer):
    """Serializer for UBA bill payment"""
    amount = serializers.DecimalField(max_digits=15, decimal_places=2, min_value=Decimal('0.01'))
    biller_code = serializers.CharField(max_length=20)
    customer_reference = serializers.CharField(max_length=50)
    source_account = serializers.CharField(max_length=20)
    narration = serializers.CharField(max_length=255, required=False, allow_blank=True)
    reference = serializers.CharField(max_length=100, required=False, allow_blank=True)


class UBAWebhookSerializer(serializers.Serializer):
    """Serializer for UBA webhook validation"""
    event_type = serializers.CharField(max_length=50)
    data = serializers.JSONField()
    timestamp = serializers.DateTimeField()
    signature = serializers.CharField(max_length=255)


class IntegrationChoiceSerializer(serializers.Serializer):
    """Serializer for choice fields"""
    value = serializers.CharField()
    display = serializers.CharField()


class IntegrationStatsSerializer(serializers.Serializer):
    """Serializer for integration statistics"""
    total_integrations = serializers.IntegerField()
    active_integrations = serializers.IntegerField()
    enabled_merchant_integrations = serializers.IntegerField()
    total_api_calls_today = serializers.IntegerField()
    successful_api_calls_today = serializers.IntegerField()
    failed_api_calls_today = serializers.IntegerField()
    success_rate_today = serializers.DecimalField(max_digits=5, decimal_places=2)
    avg_response_time_ms = serializers.DecimalField(max_digits=10, decimal_places=2)
    most_used_integration = serializers.CharField()
    most_used_operation = serializers.CharField()


class IntegrationHealthSerializer(serializers.Serializer):
    """Serializer for integration health status"""
    integration_id = serializers.UUIDField()
    integration_name = serializers.CharField()
    provider_name = serializers.CharField()
    is_healthy = serializers.BooleanField()
    last_health_check = serializers.DateTimeField()
    health_error_message = serializers.CharField(allow_blank=True)
    status = serializers.CharField()
    consecutive_failures = serializers.IntegerField()
    success_rate = serializers.DecimalField(max_digits=5, decimal_places=2)


# CyberSource Serializers

class CyberSourcePaymentSerializer(serializers.Serializer):
    """Serializer for CyberSource payment creation"""
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    currency = serializers.CharField(max_length=3, default='USD')
    card_number = serializers.CharField(max_length=19)
    expiry_month = serializers.CharField(max_length=2)
    expiry_year = serializers.CharField(max_length=4)
    cvv = serializers.CharField(max_length=4)
    cardholder_name = serializers.CharField(max_length=100, required=False)
    description = serializers.CharField(max_length=255, required=False, default='')
    reference = serializers.CharField(max_length=50, required=False)
    
    # Billing address fields
    billing_first_name = serializers.CharField(max_length=50, required=False)
    billing_last_name = serializers.CharField(max_length=50, required=False)
    billing_address1 = serializers.CharField(max_length=100, required=False)
    billing_address2 = serializers.CharField(max_length=100, required=False)
    billing_city = serializers.CharField(max_length=50, required=False)
    billing_state = serializers.CharField(max_length=50, required=False)
    billing_postal_code = serializers.CharField(max_length=20, required=False)
    billing_country = serializers.CharField(max_length=2, required=False, default='US')
    billing_email = serializers.EmailField(required=False)
    billing_phone = serializers.CharField(max_length=20, required=False)
    
    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than 0")
        return value
    
    def validate_card_number(self, value):
        # Remove spaces and validate length
        card_number = value.replace(' ', '')
        if not card_number.isdigit() or len(card_number) < 13 or len(card_number) > 19:
            raise serializers.ValidationError("Invalid card number format")
        return card_number
    
    def validate_expiry_month(self, value):
        try:
            month = int(value)
            if month < 1 or month > 12:
                raise serializers.ValidationError("Invalid month")
        except ValueError:
            raise serializers.ValidationError("Month must be numeric")
        return value.zfill(2)  # Ensure 2 digits
    
    def validate_expiry_year(self, value):
        try:
            year = int(value)
            if len(value) == 2:
                # Convert 2-digit year to 4-digit
                current_year = timezone.now().year
                century = (current_year // 100) * 100
                if year < (current_year % 100):
                    century += 100
                value = str(century + year)
            elif len(value) != 4:
                raise serializers.ValidationError("Year must be 2 or 4 digits")
        except ValueError:
            raise serializers.ValidationError("Year must be numeric")
        return value
    
    def to_internal_value(self, data):
        validated_data = super().to_internal_value(data)
        
        # Build billing address if any billing fields are provided
        billing_fields = [
            'billing_first_name', 'billing_last_name', 'billing_address1', 
            'billing_address2', 'billing_city', 'billing_state', 
            'billing_postal_code', 'billing_country', 'billing_email', 'billing_phone'
        ]
        
        billing_address = {}
        for field in billing_fields:
            if field in validated_data:
                # Remove 'billing_' prefix for CyberSource API
                api_field = field.replace('billing_', '')
                if api_field == 'address1':
                    api_field = 'address1'
                elif api_field == 'address2':
                    api_field = 'address2'
                elif api_field == 'postal_code':
                    api_field = 'postalCode'
                elif api_field == 'first_name':
                    api_field = 'firstName'
                elif api_field == 'last_name':
                    api_field = 'lastName'
                
                billing_address[api_field] = validated_data.pop(field)
        
        if billing_address:
            validated_data['billing_address'] = billing_address
        
        return validated_data


class CyberSourceCaptureSerializer(serializers.Serializer):
    """Serializer for CyberSource payment capture"""
    payment_id = serializers.CharField(max_length=100)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    currency = serializers.CharField(max_length=3, default='USD')


class CyberSourceRefundSerializer(serializers.Serializer):
    """Serializer for CyberSource payment refund"""
    payment_id = serializers.CharField(max_length=100)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    currency = serializers.CharField(max_length=3, default='USD')
    reason = serializers.CharField(max_length=255, required=False, default='')
    
    def validate_amount(self, value):
        if value is not None and value <= 0:
            raise serializers.ValidationError("Amount must be greater than 0")
        return value


class CyberSourceCustomerSerializer(serializers.Serializer):
    """Serializer for CyberSource customer profile creation"""
    customer_id = serializers.CharField(max_length=100)
    email = serializers.EmailField(required=False)
    phone = serializers.CharField(max_length=20, required=False)
    
    # Billing address fields (same as payment)
    billing_first_name = serializers.CharField(max_length=50, required=False)
    billing_last_name = serializers.CharField(max_length=50, required=False)
    billing_address1 = serializers.CharField(max_length=100, required=False)
    billing_city = serializers.CharField(max_length=50, required=False)
    billing_state = serializers.CharField(max_length=50, required=False)
    billing_postal_code = serializers.CharField(max_length=20, required=False)
    billing_country = serializers.CharField(max_length=2, required=False, default='US')


class CyberSourceTokenSerializer(serializers.Serializer):
    """Serializer for CyberSource payment token creation"""
    card_number = serializers.CharField(max_length=19)
    expiry_month = serializers.CharField(max_length=2)
    expiry_year = serializers.CharField(max_length=4)
    customer_id = serializers.CharField(max_length=100, required=False)
    
    def validate_card_number(self, value):
        # Remove spaces and validate length
        card_number = value.replace(' ', '')
        if not card_number.isdigit() or len(card_number) < 13 or len(card_number) > 19:
            raise serializers.ValidationError("Invalid card number format")
        return card_number


class CyberSourceWebhookSerializer(serializers.Serializer):
    """Serializer for CyberSource webhook data"""
    eventType = serializers.CharField(max_length=100)
    eventId = serializers.CharField(max_length=100)
    eventTime = serializers.DateTimeField()
    payload = serializers.JSONField()
    signature = serializers.CharField(max_length=500, required=False)


# Corefy Serializers

class CorefyPaymentIntentSerializer(serializers.Serializer):
    """Serializer for Corefy payment intent creation"""
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    currency = serializers.CharField(max_length=3, default='USD')
    payment_method = serializers.CharField(max_length=50, default='card')
    customer_id = serializers.CharField(max_length=100, required=False)
    description = serializers.CharField(max_length=255, required=False)
    reference_id = serializers.CharField(max_length=100, required=False)
    return_url = serializers.URLField(required=False)
    failure_url = serializers.URLField(required=False)
    
    # Customer information (if customer_id not provided)
    customer_email = serializers.EmailField(required=False)
    customer_name = serializers.CharField(max_length=100, required=False)
    customer_phone = serializers.CharField(max_length=20, required=False)
    
    # Billing address
    billing_first_name = serializers.CharField(max_length=50, required=False)
    billing_last_name = serializers.CharField(max_length=50, required=False)
    billing_address_line1 = serializers.CharField(max_length=100, required=False)
    billing_address_line2 = serializers.CharField(max_length=100, required=False)
    billing_city = serializers.CharField(max_length=50, required=False)
    billing_state = serializers.CharField(max_length=50, required=False)
    billing_postal_code = serializers.CharField(max_length=20, required=False)
    billing_country = serializers.CharField(max_length=2, required=False)
    
    # Metadata
    metadata = serializers.JSONField(required=False)
    
    def validate_currency(self, value):
        """Validate currency code"""
        supported_currencies = ['USD', 'EUR', 'GBP', 'KES', 'NGN', 'ZAR', 'GHS']
        if value.upper() not in supported_currencies:
            raise serializers.ValidationError(
                f"Currency {value} not supported. Supported currencies: {', '.join(supported_currencies)}"
            )
        return value.upper()
    
    def validate_amount(self, value):
        """Validate payment amount"""
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than 0")
        if value > 1000000:  # 1M limit
            raise serializers.ValidationError("Amount cannot exceed 1,000,000")
        return value
    
    def validate(self, attrs):
        """Cross-field validation"""
        # If customer_id is not provided, require customer email
        if not attrs.get('customer_id') and not attrs.get('customer_email'):
            raise serializers.ValidationError(
                "Either customer_id or customer_email must be provided"
            )
        
        return attrs


class CorefyConfirmPaymentSerializer(serializers.Serializer):
    """Serializer for confirming a Corefy payment intent"""
    payment_intent_id = serializers.CharField(max_length=100)
    
    # Payment method data for card payments
    card_number = serializers.CharField(max_length=19, required=False)
    card_expiry_month = serializers.CharField(max_length=2, required=False)
    card_expiry_year = serializers.CharField(max_length=4, required=False)
    card_cvv = serializers.CharField(max_length=4, required=False)
    card_holder_name = serializers.CharField(max_length=100, required=False)
    
    # Saved payment method
    payment_method_id = serializers.CharField(max_length=100, required=False)
    
    # 3DS authentication data
    three_ds_version = serializers.CharField(max_length=10, required=False)
    three_ds_eci = serializers.CharField(max_length=2, required=False)
    three_ds_cavv = serializers.CharField(max_length=100, required=False)
    three_ds_xid = serializers.CharField(max_length=100, required=False)
    
    def validate(self, attrs):
        """Validate payment confirmation data"""
        # Check if either card details or payment method ID is provided
        has_card_data = any([
            attrs.get('card_number'),
            attrs.get('payment_method_id')
        ])
        
        if not has_card_data:
            raise serializers.ValidationError(
                "Either card details or payment_method_id must be provided"
            )
        
        # If card data is provided, validate required fields
        if attrs.get('card_number'):
            required_card_fields = ['card_expiry_month', 'card_expiry_year', 'card_cvv']
            missing_fields = [field for field in required_card_fields if not attrs.get(field)]
            if missing_fields:
                raise serializers.ValidationError(
                    f"Missing required card fields: {', '.join(missing_fields)}"
                )
        
        return attrs


class CorefyRefundSerializer(serializers.Serializer):
    """Serializer for Corefy payment refund"""
    payment_id = serializers.CharField(max_length=100)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    reason = serializers.CharField(max_length=255, required=False)
    reference_id = serializers.CharField(max_length=100, required=False)
    
    def validate_amount(self, value):
        """Validate refund amount"""
        if value is not None and value <= 0:
            raise serializers.ValidationError("Refund amount must be greater than 0")
        return value


class CorefyCustomerSerializer(serializers.Serializer):
    """Serializer for Corefy customer creation"""
    email = serializers.EmailField()
    name = serializers.CharField(max_length=100, required=False)
    phone = serializers.CharField(max_length=20, required=False)
    
    # Address information
    address_line1 = serializers.CharField(max_length=100, required=False)
    address_line2 = serializers.CharField(max_length=100, required=False)
    city = serializers.CharField(max_length=50, required=False)
    state = serializers.CharField(max_length=50, required=False)
    postal_code = serializers.CharField(max_length=20, required=False)
    country = serializers.CharField(max_length=2, required=False)
    
    # Metadata
    metadata = serializers.JSONField(required=False)
    reference_id = serializers.CharField(max_length=100, required=False)


class CorefyPaymentMethodSerializer(serializers.Serializer):
    """Serializer for Corefy payment method creation"""
    customer_id = serializers.CharField(max_length=100)
    payment_method_type = serializers.CharField(max_length=50, default='card')
    
    # Card data
    card_number = serializers.CharField(max_length=19, required=False)
    card_expiry_month = serializers.CharField(max_length=2, required=False)
    card_expiry_year = serializers.CharField(max_length=4, required=False)
    card_holder_name = serializers.CharField(max_length=100, required=False)
    
    # Alternative payment method data
    payment_method_data = serializers.JSONField(required=False)
    
    def validate(self, attrs):
        """Validate payment method data"""
        payment_type = attrs.get('payment_method_type', 'card')
        
        if payment_type == 'card':
            required_fields = ['card_number', 'card_expiry_month', 'card_expiry_year']
            missing_fields = [field for field in required_fields if not attrs.get(field)]
            if missing_fields:
                raise serializers.ValidationError(
                    f"Missing required card fields: {', '.join(missing_fields)}"
                )
        
        return attrs


class CorefyWebhookSerializer(serializers.Serializer):
    """Serializer for Corefy webhook data"""
    event_type = serializers.CharField(max_length=100)
    event_id = serializers.CharField(max_length=100)
    event_time = serializers.DateTimeField()
    payment_id = serializers.CharField(max_length=100, required=False)
    payment_intent_id = serializers.CharField(max_length=100, required=False)
    customer_id = serializers.CharField(max_length=100, required=False)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    currency = serializers.CharField(max_length=3, required=False)
    status = serializers.CharField(max_length=50, required=False)
    payment_method = serializers.CharField(max_length=50, required=False)
    reference_id = serializers.CharField(max_length=100, required=False)
    metadata = serializers.JSONField(required=False)
    signature = serializers.CharField(max_length=500, required=False)
