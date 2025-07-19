from rest_framework import serializers
from django.utils import timezone
from decimal import Decimal
from django.contrib.auth import get_user_model

from .models import (
    PaymentGateway,
    Transaction,
    PaymentLink,
    TransactionEvent,
    Webhook,
    PaymentMethod,
    TransactionType,
    TransactionStatus
)
from authentication.models import Merchant, PreferredCurrency

User = get_user_model()


class PaymentGatewaySerializer(serializers.ModelSerializer):
    """Serializer for Payment Gateway"""
    supported_payment_methods_list = serializers.ReadOnlyField(source='get_supported_payment_methods_list')
    supported_currencies_list = serializers.ReadOnlyField(source='get_supported_currencies_list')
    transaction_count = serializers.SerializerMethodField()

    class Meta:
        model = PaymentGateway
        fields = [
            'id', 'name', 'code', 'description', 'api_endpoint', 'webhook_endpoint',
            'merchant_id', 'supports_payments', 'supports_refunds', 'supports_payouts',
            'supports_webhooks', 'supports_recurring', 'supported_payment_methods',
            'supported_currencies', 'supported_payment_methods_list', 'supported_currencies_list',
            'min_amount', 'max_amount', 'transaction_fee_percentage', 'transaction_fee_fixed',
            'is_active', 'is_sandbox', 'priority', 'transaction_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
        extra_kwargs = {
            'private_key': {'write_only': True},
            'public_key': {'write_only': True}
        }

    def get_transaction_count(self, obj):
        """Get transaction count for this gateway"""
        return obj.transactions.count()


class TransactionEventSerializer(serializers.ModelSerializer):
    """Serializer for Transaction Event"""
    user_email = serializers.CharField(source='user.email', read_only=True)

    class Meta:
        model = TransactionEvent
        fields = [
            'id', 'event_type', 'old_status', 'new_status', 'description',
            'metadata', 'source', 'user', 'user_email', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class WebhookSerializer(serializers.ModelSerializer):
    """Serializer for Webhook"""
    
    class Meta:
        model = Webhook
        fields = [
            'id', 'url', 'event_type', 'payload', 'headers', 'status_code',
            'response_body', 'response_time_ms', 'attempts', 'max_attempts',
            'is_delivered', 'delivered_at', 'next_attempt_at', 'error_message',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'delivered_at']


class TransactionListSerializer(serializers.ModelSerializer):
    """Simplified serializer for transaction lists"""
    merchant_name = serializers.CharField(source='merchant.business_name', read_only=True)
    customer_email = serializers.SerializerMethodField()
    currency_code = serializers.CharField(source='currency.code', read_only=True)
    gateway_name = serializers.CharField(source='gateway.name', read_only=True)
    amount_display = serializers.SerializerMethodField()
    can_refund = serializers.ReadOnlyField()

    class Meta:
        model = Transaction
        fields = [
            'id', 'reference', 'external_reference', 'merchant_name',
            'customer_email', 'transaction_type', 'status', 'payment_method',
            'gateway_name', 'currency_code', 'amount', 'amount_display',
            'fee_amount', 'net_amount', 'description', 'can_refund',
            'is_settled', 'is_flagged', 'created_at'
        ]

    def get_customer_email(self, obj):
        """Get customer email"""
        if obj.customer:
            return obj.customer.email
        return obj.customer_email

    def get_amount_display(self, obj):
        """Get formatted amount display"""
        return f"{obj.amount} {obj.currency.code}"


class TransactionDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for transaction details"""
    merchant_name = serializers.CharField(source='merchant.business_name', read_only=True)
    customer_email = serializers.SerializerMethodField()
    currency_code = serializers.CharField(source='currency.code', read_only=True)
    gateway_name = serializers.CharField(source='gateway.name', read_only=True)
    events = TransactionEventSerializer(many=True, read_only=True)
    webhooks = WebhookSerializer(many=True, read_only=True)
    child_transactions = TransactionListSerializer(many=True, read_only=True)
    refunded_amount = serializers.ReadOnlyField(source='get_refunded_amount')
    remaining_refundable_amount = serializers.ReadOnlyField(source='get_remaining_refundable_amount')
    can_refund = serializers.ReadOnlyField()
    transaction_hash = serializers.ReadOnlyField(source='get_transaction_hash')

    class Meta:
        model = Transaction
        fields = [
            'id', 'reference', 'external_reference', 'merchant', 'merchant_name',
            'customer', 'customer_email', 'customer_phone', 'transaction_type',
            'status', 'payment_method', 'gateway', 'gateway_name', 'currency',
            'currency_code', 'amount', 'fee_amount', 'net_amount', 'original_currency',
            'original_amount', 'exchange_rate', 'description', 'metadata',
            'payment_details', 'processed_at', 'completed_at', 'failed_at',
            'expires_at', 'failure_reason', 'failure_code', 'settlement_date',
            'settlement_reference', 'is_settled', 'parent_transaction',
            'ip_address', 'user_agent', 'risk_score', 'is_flagged',
            'events', 'webhooks', 'child_transactions', 'refunded_amount',
            'remaining_refundable_amount', 'can_refund', 'transaction_hash',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'reference', 'net_amount', 'created_at', 'updated_at',
            'processed_at', 'completed_at', 'failed_at'
        ]

    def get_customer_email(self, obj):
        """Get customer email"""
        if obj.customer:
            return obj.customer.email
        return obj.customer_email


class TransactionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating transactions"""
    
    class Meta:
        model = Transaction
        fields = [
            'merchant', 'customer', 'customer_email', 'customer_phone',
            'transaction_type', 'payment_method', 'gateway', 'currency',
            'amount', 'description', 'metadata', 'payment_details',
            'expires_at', 'ip_address', 'user_agent'
        ]

    def validate(self, data):
        """Validate transaction data"""
        # Ensure either customer or customer_email is provided
        if not data.get('customer') and not data.get('customer_email'):
            raise serializers.ValidationError(
                "Either customer or customer_email must be provided"
            )
        
        # Validate amount is positive
        if data.get('amount') and data['amount'] <= 0:
            raise serializers.ValidationError(
                "Amount must be greater than zero"
            )
        
        # Validate gateway supports payment method
        gateway = data.get('gateway')
        payment_method = data.get('payment_method')
        if gateway and payment_method:
            if not gateway.supports_payment_method(payment_method):
                raise serializers.ValidationError(
                    f"Gateway {gateway.name} does not support {payment_method}"
                )
        
        # Validate gateway supports currency
        currency = data.get('currency')
        if gateway and currency:
            if not gateway.supports_currency(currency.code):
                raise serializers.ValidationError(
                    f"Gateway {gateway.name} does not support {currency.code}"
                )
        
        return data

    def create(self, validated_data):
        """Create transaction with fee calculation"""
        gateway = validated_data.get('gateway')
        amount = validated_data.get('amount')
        
        # Calculate fees if gateway is provided
        if gateway and amount:
            fees = gateway.calculate_fees(amount)
            validated_data['fee_amount'] = fees['total_fee']
        
        return super().create(validated_data)


class TransactionUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating transactions"""
    
    class Meta:
        model = Transaction
        fields = [
            'status', 'external_reference', 'description', 'metadata',
            'payment_details', 'failure_reason', 'failure_code',
            'settlement_date', 'settlement_reference', 'is_settled',
            'risk_score', 'is_flagged'
        ]

    def validate_status(self, value):
        """Validate status transitions"""
        instance = self.instance
        if instance:
            current_status = instance.status
            
            # Define allowed status transitions
            allowed_transitions = {
                'pending': ['processing', 'failed', 'cancelled', 'expired'],
                'processing': ['completed', 'failed'],
                'completed': ['refunded', 'partially_refunded', 'disputed'],
                'failed': [],
                'cancelled': [],
                'expired': [],
                'refunded': [],
                'partially_refunded': ['refunded', 'disputed'],
                'disputed': ['completed', 'refunded'],
                'frozen': ['completed', 'failed', 'cancelled']
            }
            
            if value != current_status and value not in allowed_transitions.get(current_status, []):
                raise serializers.ValidationError(
                    f"Cannot change status from {current_status} to {value}"
                )
        
        return value


class RefundCreateSerializer(serializers.Serializer):
    """Serializer for creating refunds"""
    amount = serializers.DecimalField(max_digits=15, decimal_places=2, min_value=Decimal('0.01'))
    reason = serializers.CharField(max_length=500, required=False, allow_blank=True)
    
    def validate_amount(self, value):
        """Validate refund amount"""
        transaction = self.context.get('transaction')
        if transaction:
            if not transaction.can_refund():
                raise serializers.ValidationError(
                    "This transaction cannot be refunded"
                )
            
            remaining_amount = transaction.get_remaining_refundable_amount()
            if value > remaining_amount:
                raise serializers.ValidationError(
                    f"Refund amount cannot exceed remaining refundable amount of {remaining_amount}"
                )
        
        return value


class PaymentLinkSerializer(serializers.ModelSerializer):
    """Serializer for Payment Link"""
    allowed_payment_methods_list = serializers.ReadOnlyField(source='get_allowed_payment_methods_list')
    is_usable = serializers.ReadOnlyField()
    absolute_url = serializers.ReadOnlyField(source='get_absolute_url')
    usage_display = serializers.SerializerMethodField()

    class Meta:
        model = PaymentLink
        fields = [
            'id', 'merchant', 'title', 'description', 'currency', 'amount',
            'is_amount_flexible', 'min_amount', 'max_amount', 'slug', 'is_active',
            'expires_at', 'max_uses', 'current_uses', 'require_name', 'require_email',
            'require_phone', 'require_address', 'allowed_payment_methods',
            'allowed_payment_methods_list', 'success_url', 'cancel_url', 'metadata',
            'is_usable', 'absolute_url', 'usage_display', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'slug', 'current_uses', 'created_at', 'updated_at']

    def get_usage_display(self, obj):
        """Get usage display"""
        if obj.max_uses:
            return f"{obj.current_uses}/{obj.max_uses}"
        return f"{obj.current_uses}/∞"

    def validate(self, data):
        """Validate payment link data"""
        # Validate amount settings
        if data.get('is_amount_flexible'):
            min_amount = data.get('min_amount')
            max_amount = data.get('max_amount')
            if min_amount and max_amount and min_amount >= max_amount:
                raise serializers.ValidationError(
                    "Minimum amount must be less than maximum amount"
                )
        
        # Validate expiration date
        expires_at = data.get('expires_at')
        if expires_at and expires_at <= timezone.now():
            raise serializers.ValidationError(
                "Expiration date must be in the future"
            )
        
        return data


class PaymentLinkCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating payment links"""
    
    class Meta:
        model = PaymentLink
        fields = [
            'merchant', 'title', 'description', 'currency', 'amount',
            'is_amount_flexible', 'min_amount', 'max_amount', 'expires_at',
            'max_uses', 'require_name', 'require_email', 'require_phone',
            'require_address', 'allowed_payment_methods', 'success_url',
            'cancel_url', 'metadata'
        ]


class TransactionStatsSerializer(serializers.Serializer):
    """Serializer for transaction statistics"""
    total_transactions = serializers.IntegerField()
    completed_transactions = serializers.IntegerField()
    failed_transactions = serializers.IntegerField()
    success_rate = serializers.FloatField()
    total_volume = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_fees = serializers.DecimalField(max_digits=15, decimal_places=2)
    net_volume = serializers.DecimalField(max_digits=15, decimal_places=2)


# Choice field serializers for API documentation
class PaymentMethodChoiceSerializer(serializers.Serializer):
    """Serializer for payment method choices"""
    value = serializers.CharField()
    display = serializers.CharField()


class TransactionTypeChoiceSerializer(serializers.Serializer):
    """Serializer for transaction type choices"""
    value = serializers.CharField()
    display = serializers.CharField()


class TransactionStatusChoiceSerializer(serializers.Serializer):
    """Serializer for transaction status choices"""
    value = serializers.CharField()
    display = serializers.CharField()
