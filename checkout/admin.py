from django.contrib import admin
from .models import CheckoutPage, PaymentMethodConfig, CheckoutSession


class PaymentMethodConfigInline(admin.TabularInline):
    model = PaymentMethodConfig
    extra = 0
    fields = ['payment_method', 'is_enabled', 'display_order', 'display_name']
    ordering = ['display_order']


@admin.register(CheckoutPage)
class CheckoutPageAdmin(admin.ModelAdmin):
    list_display = ['name', 'merchant', 'title', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at', 'merchant']
    search_fields = ['name', 'title', 'merchant__business_name']
    prepopulated_fields = {'slug': ('name',)}
    inlines = [PaymentMethodConfigInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('merchant', 'name', 'slug', 'title', 'description')
        }),
        ('Branding', {
            'fields': ('logo', 'primary_color', 'secondary_color', 'background_color'),
            'classes': ('collapse',)
        }),
        ('Payment Settings', {
            'fields': ('currency', 'min_amount', 'max_amount', 'allow_custom_amount')
        }),
        ('Page Settings', {
            'fields': ('is_active', 'require_customer_info', 'require_billing_address', 'require_shipping_address')
        }),
        ('URLs', {
            'fields': ('success_url', 'cancel_url'),
            'classes': ('collapse',)
        })
    )


@admin.register(PaymentMethodConfig)
class PaymentMethodConfigAdmin(admin.ModelAdmin):
    list_display = ['checkout_page', 'payment_method', 'is_enabled', 'display_order']
    list_filter = ['payment_method', 'is_enabled', 'checkout_page__merchant']
    search_fields = ['checkout_page__name', 'checkout_page__merchant__business_name']
    ordering = ['checkout_page', 'display_order']


@admin.register(CheckoutSession)
class CheckoutSessionAdmin(admin.ModelAdmin):
    list_display = ['session_token_short', 'checkout_page', 'amount', 'currency', 'customer_email', 'status', 'created_at']
    list_filter = ['status', 'created_at', 'checkout_page__merchant']
    search_fields = ['session_token', 'customer_email', 'checkout_page__name']
    readonly_fields = ['session_token', 'created_at', 'updated_at']
    
    def session_token_short(self, obj):
        return f"{obj.session_token[:8]}..."
    session_token_short.short_description = 'Session Token'
    
    fieldsets = (
        ('Session Info', {
            'fields': ('checkout_page', 'session_token', 'status', 'expires_at')
        }),
        ('Payment Details', {
            'fields': ('amount', 'currency', 'selected_payment_method', 'payment_reference')
        }),
        ('Customer Info', {
            'fields': ('customer_email', 'customer_name', 'customer_phone')
        }),
        ('Addresses', {
            'fields': ('billing_address', 'shipping_address'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('metadata',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'completed_at'),
            'classes': ('collapse',)
        })
    )
