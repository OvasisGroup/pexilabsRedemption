from rest_framework import serializers
from .models import CheckoutPage, PaymentMethodConfig, CheckoutSession


class PaymentMethodConfigSerializer(serializers.ModelSerializer):
    display_name = serializers.SerializerMethodField()
    icon_url = serializers.SerializerMethodField()
    
    class Meta:
        model = PaymentMethodConfig
        fields = [
            'id', 'payment_method', 'is_enabled', 'display_order',
            'display_name', 'icon_url', 'gateway_config'
        ]
    
    def get_display_name(self, obj):
        return obj.get_display_name()
    
    def get_icon_url(self, obj):
        return obj.get_icon_url()


class CheckoutPageSerializer(serializers.ModelSerializer):
    payment_methods = PaymentMethodConfigSerializer(many=True, read_only=True)
    currency_code = serializers.CharField(source='currency.code', read_only=True)
    currency_symbol = serializers.CharField(source='currency.symbol', read_only=True)
    
    class Meta:
        model = CheckoutPage
        fields = [
            'id', 'name', 'slug', 'title', 'description', 'logo',
            'primary_color', 'secondary_color', 'background_color',
            'currency', 'currency_code', 'currency_symbol',
            'min_amount', 'max_amount', 'allow_custom_amount',
            'is_active', 'require_customer_info', 'require_billing_address',
            'require_shipping_address', 'success_url', 'cancel_url',
            'payment_methods', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class CheckoutPageCreateSerializer(serializers.ModelSerializer):
    payment_methods = serializers.ListField(
        child=serializers.CharField(), 
        write_only=True, 
        required=False,
        help_text="List of payment methods to enable"
    )
    
    class Meta:
        model = CheckoutPage
        fields = [
            'name', 'slug', 'title', 'description', 'logo',
            'primary_color', 'secondary_color', 'background_color',
            'currency', 'min_amount', 'max_amount', 'allow_custom_amount',
            'require_customer_info', 'require_billing_address',
            'require_shipping_address', 'success_url', 'cancel_url',
            'payment_methods'
        ]
    
    def create(self, validated_data):
        payment_methods = validated_data.pop('payment_methods', [])
        checkout_page = CheckoutPage.objects.create(**validated_data)
        
        # Create payment method configurations
        for i, method in enumerate(payment_methods):
            PaymentMethodConfig.objects.create(
                checkout_page=checkout_page,
                payment_method=method,
                display_order=i
            )
        
        return checkout_page


class CheckoutSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CheckoutSession
        fields = [
            'id', 'session_token', 'amount', 'currency',
            'customer_email', 'customer_name', 'customer_phone',
            'billing_address', 'shipping_address',
            'selected_payment_method', 'status', 'expires_at',
            'metadata', 'created_at'
        ]
        read_only_fields = ['id', 'session_token', 'expires_at', 'created_at']


class CreateCheckoutSessionSerializer(serializers.Serializer):
    checkout_page_slug = serializers.CharField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    customer_email = serializers.EmailField()
    customer_name = serializers.CharField(max_length=200, required=False)
    customer_phone = serializers.CharField(max_length=20, required=False)
    billing_address = serializers.JSONField(required=False)
    shipping_address = serializers.JSONField(required=False)
    metadata = serializers.JSONField(required=False)
    
    def validate(self, data):
        try:
            checkout_page = CheckoutPage.objects.get(
                slug=data['checkout_page_slug'],
                is_active=True
            )
            data['checkout_page'] = checkout_page
        except CheckoutPage.DoesNotExist:
            raise serializers.ValidationError("Checkout page not found or inactive")
        
        # Validate amount if custom amounts are allowed
        amount = data.get('amount')
        if amount:
            if amount < checkout_page.min_amount:
                raise serializers.ValidationError(f"Amount must be at least {checkout_page.min_amount}")
            if amount > checkout_page.max_amount:
                raise serializers.ValidationError(f"Amount cannot exceed {checkout_page.max_amount}")
        elif not checkout_page.allow_custom_amount:
            raise serializers.ValidationError("Custom amounts not allowed for this checkout page")
        
        return data


class ProcessPaymentSerializer(serializers.Serializer):
    session_token = serializers.CharField()
    payment_method = serializers.CharField()
    
    # Card payment fields
    card_number = serializers.CharField(required=False)
    card_expiry_month = serializers.CharField(required=False)
    card_expiry_year = serializers.CharField(required=False)
    card_cvv = serializers.CharField(required=False)
    card_holder_name = serializers.CharField(required=False)
    
    # Additional payment method data
    payment_data = serializers.JSONField(required=False)
    
    def validate(self, data):
        try:
            session = CheckoutSession.objects.get(
                session_token=data['session_token'],
                status='pending'
            )
            if session.is_expired():
                raise serializers.ValidationError("Checkout session has expired")
            data['session'] = session
        except CheckoutSession.DoesNotExist:
            raise serializers.ValidationError("Invalid or expired session")
        
        return data
