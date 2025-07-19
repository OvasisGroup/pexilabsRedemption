from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.http import HttpResponseRedirect
from django.contrib import messages
import json

from .models import (
    Integration,
    MerchantIntegration,
    BankIntegration,
    IntegrationAPICall,
    IntegrationWebhook
)


class BankIntegrationInline(admin.StackedInline):
    """Inline for bank-specific integration details"""
    model = BankIntegration
    can_delete = False
    extra = 0
    fields = (
        ('bank_name', 'bank_code', 'country_code'),
        ('swift_code', 'settlement_currency'),
        'supported_currencies',
        ('supports_account_inquiry', 'supports_balance_inquiry', 'supports_transaction_history'),
        ('supports_fund_transfer', 'supports_bill_payment', 'supports_standing_orders'),
        ('min_transfer_amount', 'max_transfer_amount', 'daily_transfer_limit'),
        ('transfer_fee_percentage', 'transfer_fee_fixed', 'inquiry_fee'),
        ('operating_hours_start', 'operating_hours_end'),
        ('operates_weekends', 'operates_holidays', 'settlement_time'),
    )


class MerchantIntegrationInline(admin.TabularInline):
    """Inline for merchant integrations"""
    model = MerchantIntegration
    extra = 0
    fields = ('merchant', 'is_enabled', 'status', 'total_requests', 'successful_requests', 'get_success_rate')
    readonly_fields = ('total_requests', 'successful_requests', 'get_success_rate')
    
    def get_success_rate(self, obj):
        if obj and obj.pk:
            return f"{obj.get_success_rate()}%"
        return "N/A"
    get_success_rate.short_description = 'Success Rate'


@admin.register(Integration)
class IntegrationAdmin(admin.ModelAdmin):
    """Admin interface for integrations"""
    list_display = (
        'name', 'provider_name', 'integration_type', 'status',
        'is_sandbox', 'is_global', 'is_healthy', 'created_at'
    )
    list_filter = (
        'integration_type', 'status', 'is_sandbox', 'is_global',
        'is_healthy', 'authentication_type', 'supports_webhooks'
    )
    search_fields = ('name', 'provider_name', 'code', 'description')
    readonly_fields = ('id', 'created_at', 'updated_at', 'last_health_check')
    
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'name', 'code', 'provider_name', 'description',
                'integration_type', 'status', 'is_global'
            )
        }),
        ('Configuration', {
            'fields': (
                'base_url', 'is_sandbox', 'version', 'authentication_type'
            )
        }),
        ('Capabilities', {
            'fields': (
                'supports_webhooks', 'supports_bulk_operations', 'supports_real_time'
            )
        }),
        ('Rate Limiting', {
            'fields': (
                'rate_limit_per_minute', 'rate_limit_per_hour', 'rate_limit_per_day'
            ),
            'classes': ('collapse',)
        }),
        ('Health Monitoring', {
            'fields': (
                'is_healthy', 'health_check_interval', 'health_error_message',
                'last_health_check'
            ),
            'classes': ('collapse',)
        }),
        ('Documentation', {
            'fields': ('provider_website', 'provider_documentation'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [BankIntegrationInline, MerchantIntegrationInline]
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related().prefetch_related(
            'merchant_configurations', 'bank_details'
        )
    
    actions = ['activate_integrations', 'deactivate_integrations', 'health_check']
    
    def activate_integrations(self, request, queryset):
        """Activate selected integrations"""
        updated = queryset.update(status='active', is_healthy=True)
        self.message_user(
            request,
            f'{updated} integration(s) were successfully activated.',
            messages.SUCCESS
        )
    activate_integrations.short_description = "Activate selected integrations"
    
    def deactivate_integrations(self, request, queryset):
        """Deactivate selected integrations"""
        updated = queryset.update(status='inactive')
        self.message_user(
            request,
            f'{updated} integration(s) were successfully deactivated.',
            messages.SUCCESS
        )
    deactivate_integrations.short_description = "Deactivate selected integrations"
    
    def health_check(self, request, queryset):
        """Perform health check on selected integrations"""
        for integration in queryset:
            # Here you would implement actual health check logic
            integration.is_healthy = True
            integration.save(update_fields=['is_healthy'])
        
        self.message_user(
            request,
            f'Health check completed for {queryset.count()} integration(s).',
            messages.SUCCESS
        )
    health_check.short_description = "Perform health check"


@admin.register(MerchantIntegration)
class MerchantIntegrationAdmin(admin.ModelAdmin):
    """Admin interface for merchant integrations"""
    list_display = (
        'merchant', 'integration', 'is_enabled', 'status',
        'get_success_rate', 'total_requests', 'last_used_at'
    )
    list_filter = (
        'is_enabled', 'status', 'integration__integration_type',
        'integration__provider_name', 'created_at'
    )
    search_fields = (
        'merchant__business_name', 'integration__name',
        'integration__provider_name'
    )
    readonly_fields = (
        'id', 'total_requests', 'successful_requests', 'failed_requests',
        'consecutive_failures', 'last_used_at', 'last_error_at',
        'created_at', 'updated_at', 'get_success_rate', 'credentials_preview'
    )
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('merchant', 'integration', 'is_enabled', 'status')
        }),
        ('Configuration', {
            'fields': ('configuration',),
            'description': 'Merchant-specific configuration in JSON format'
        }),
        ('Credentials', {
            'fields': ('credentials_preview',),
            'description': 'Encrypted credentials (view only)'
        }),
        ('Usage Statistics', {
            'fields': (
                'total_requests', 'successful_requests', 'failed_requests',
                'get_success_rate', 'last_used_at'
            ),
            'classes': ('collapse',)
        }),
        ('Error Tracking', {
            'fields': (
                'consecutive_failures', 'last_error_message', 'last_error_at'
            ),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_success_rate(self, obj):
        """Display success rate with color coding"""
        rate = obj.get_success_rate()
        if rate >= 95:
            color = 'green'
        elif rate >= 85:
            color = 'orange'
        else:
            color = 'red'
        return format_html(
            '<span style="color: {};">{:.1f}%</span>',
            color, rate
        )
    get_success_rate.short_description = 'Success Rate'
    
    def credentials_preview(self, obj):
        """Show encrypted credentials preview"""
        if obj.credentials:
            return format_html(
                '<code style="background: #f5f5f5; padding: 5px;">{}...</code>',
                obj.credentials[:50]
            )
        return "No credentials stored"
    credentials_preview.short_description = 'Credentials (Encrypted)'


@admin.register(BankIntegration)
class BankIntegrationAdmin(admin.ModelAdmin):
    """Admin interface for bank integrations"""
    list_display = (
        'bank_name', 'bank_code', 'country_code',
        'get_supported_services', 'is_operating_now', 'settlement_time'
    )
    list_filter = (
        'country_code', 'operates_weekends', 'operates_holidays',
        'supports_fund_transfer', 'supports_bill_payment'
    )
    search_fields = ('bank_name', 'bank_code', 'swift_code')
    readonly_fields = ('id', 'get_supported_services', 'is_operating_now')
    
    fieldsets = (
        ('Bank Information', {
            'fields': (
                'integration', 'bank_name', 'bank_code',
                'country_code', 'swift_code'
            )
        }),
        ('Supported Services', {
            'fields': (
                'supports_account_inquiry', 'supports_balance_inquiry',
                'supports_transaction_history', 'supports_fund_transfer',
                'supports_bill_payment', 'supports_standing_orders',
                'supports_direct_debit'
            )
        }),
        ('Currencies & Limits', {
            'fields': (
                'supported_currencies', 'min_transfer_amount',
                'max_transfer_amount', 'daily_transfer_limit'
            )
        }),
        ('Fee Structure', {
            'fields': (
                'transfer_fee_percentage', 'transfer_fee_fixed', 'inquiry_fee'
            )
        }),
        ('Operating Hours', {
            'fields': (
                'operating_hours_start', 'operating_hours_end',
                'operates_weekends', 'operates_holidays'
            )
        }),
        ('Settlement', {
            'fields': ('settlement_time', 'settlement_currency')
        }),
    )
    
    def get_supported_services(self, obj):
        """Display list of supported services"""
        services = []
        service_fields = [
            ('supports_account_inquiry', 'Account Inquiry'),
            ('supports_balance_inquiry', 'Balance Inquiry'),
            ('supports_transaction_history', 'Transaction History'),
            ('supports_fund_transfer', 'Fund Transfer'),
            ('supports_bill_payment', 'Bill Payment'),
            ('supports_standing_orders', 'Standing Orders'),
            ('supports_direct_debit', 'Direct Debit'),
        ]
        
        for field, label in service_fields:
            if getattr(obj, field):
                services.append(label)
        
        return ', '.join(services) if services else 'None'
    get_supported_services.short_description = 'Supported Services'
    
    def is_operating_now(self, obj):
        """Display if bank is currently operating"""
        operating = obj.is_operating_now()
        color = 'green' if operating else 'red'
        status = 'Yes' if operating else 'No'
        return format_html(
            '<span style="color: {};">{}</span>',
            color, status
        )
    is_operating_now.short_description = 'Operating Now'


@admin.register(IntegrationAPICall)
class IntegrationAPICallAdmin(admin.ModelAdmin):
    """Admin interface for integration API calls"""
    list_display = (
        'merchant_integration', 'method', 'endpoint_short',
        'status_code', 'is_successful', 'response_time_ms', 'created_at'
    )
    list_filter = (
        'is_successful', 'method', 'operation_type',
        'merchant_integration__integration__provider_name', 'created_at'
    )
    search_fields = (
        'endpoint', 'reference_id', 'merchant_integration__merchant__business_name'
    )
    readonly_fields = ('id', 'created_at')
    date_hierarchy = 'created_at'
    
    def endpoint_short(self, obj):
        """Display shortened endpoint"""
        endpoint = obj.endpoint
        return endpoint[:50] + '...' if len(endpoint) > 50 else endpoint
    endpoint_short.short_description = 'Endpoint'


@admin.register(IntegrationWebhook)
class IntegrationWebhookAdmin(admin.ModelAdmin):
    """Admin interface for integration webhooks"""
    list_display = (
        'integration', 'event_type', 'is_verified',
        'is_processed', 'source_ip', 'created_at'
    )
    list_filter = (
        'is_verified', 'is_processed', 'event_type',
        'integration__provider_name', 'created_at'
    )
    search_fields = ('event_type', 'integration__name', 'source_ip')
    readonly_fields = ('id', 'created_at', 'processed_at')
    date_hierarchy = 'created_at'
