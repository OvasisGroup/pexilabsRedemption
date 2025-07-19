from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.db.models import Count, Sum
from django.utils import timezone
from datetime import timedelta

from .models import (
    PaymentGateway,
    Transaction,
    PaymentLink,
    TransactionEvent,
    Webhook
)


@admin.register(PaymentGateway)
class PaymentGatewayAdmin(admin.ModelAdmin):
    """Admin interface for Payment Gateway"""
    list_display = [
        'name', 'code', 'is_active', 'is_sandbox', 'priority',
        'supports_payments', 'supports_refunds', 'transaction_count',
        'created_at'
    ]
    list_filter = [
        'is_active', 'is_sandbox', 'supports_payments', 'supports_refunds',
        'supports_payouts', 'supports_webhooks', 'created_at'
    ]
    search_fields = ['name', 'code', 'description']
    readonly_fields = ['created_at', 'updated_at', 'transaction_count']
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'code', 'description', 'priority')
        }),
        ('Configuration', {
            'fields': ('api_endpoint', 'webhook_endpoint', 'public_key', 'private_key', 'merchant_id')
        }),
        ('Features', {
            'fields': (
                'supports_payments', 'supports_refunds', 'supports_payouts',
                'supports_webhooks', 'supports_recurring'
            )
        }),
        ('Supported Methods & Currencies', {
            'fields': ('supported_payment_methods', 'supported_currencies')
        }),
        ('Limits & Fees', {
            'fields': (
                'min_amount', 'max_amount', 'transaction_fee_percentage', 'transaction_fee_fixed'
            )
        }),
        ('Status', {
            'fields': ('is_active', 'is_sandbox')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def transaction_count(self, obj):
        """Display transaction count for this gateway"""
        count = obj.transactions.count()
        if count > 0:
            url = reverse('admin:transactions_transaction_changelist')
            return format_html('<a href="{}?gateway__id__exact={}">{}</a>', url, obj.id, count)
        return count
    transaction_count.short_description = 'Transactions'


class TransactionEventInline(admin.TabularInline):
    """Inline for transaction events"""
    model = TransactionEvent
    extra = 0
    readonly_fields = ['created_at']
    fields = ['event_type', 'old_status', 'new_status', 'description', 'source', 'user', 'created_at']


class WebhookInline(admin.TabularInline):
    """Inline for webhooks"""
    model = Webhook
    extra = 0
    readonly_fields = ['created_at', 'updated_at']
    fields = ['url', 'event_type', 'attempts', 'is_delivered', 'status_code', 'created_at']


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    """Admin interface for Transaction"""
    list_display = [
        'reference', 'merchant', 'customer_display', 'amount_display',
        'status_badge', 'payment_method', 'gateway', 'created_at'
    ]
    list_filter = [
        'status', 'transaction_type', 'payment_method', 'gateway',
        'is_settled', 'is_flagged', 'created_at', 'merchant'
    ]
    search_fields = [
        'reference', 'external_reference', 'customer__email',
        'customer_email', 'description'
    ]
    readonly_fields = [
        'id', 'reference', 'net_amount', 'created_at', 'updated_at',
        'processed_at', 'completed_at', 'failed_at', 'transaction_hash'
    ]
    inlines = [TransactionEventInline, WebhookInline]
    
    fieldsets = (
        ('Identification', {
            'fields': ('id', 'reference', 'external_reference')
        }),
        ('Parties', {
            'fields': (
                'merchant', 'customer', 'customer_email', 'customer_phone'
            )
        }),
        ('Transaction Details', {
            'fields': (
                'transaction_type', 'status', 'payment_method', 'gateway',
                'description', 'metadata'
            )
        }),
        ('Amount Information', {
            'fields': (
                'currency', 'amount', 'fee_amount', 'net_amount',
                'original_currency', 'original_amount', 'exchange_rate'
            )
        }),
        ('Payment Details', {
            'fields': ('payment_details',),
            'classes': ('collapse',)
        }),
        ('Status Tracking', {
            'fields': (
                'processed_at', 'completed_at', 'failed_at', 'expires_at'
            )
        }),
        ('Failure Information', {
            'fields': ('failure_reason', 'failure_code'),
            'classes': ('collapse',)
        }),
        ('Settlement', {
            'fields': (
                'settlement_date', 'settlement_reference', 'is_settled'
            )
        }),
        ('Relationships', {
            'fields': ('parent_transaction',),
            'classes': ('collapse',)
        }),
        ('Security & Fraud', {
            'fields': (
                'ip_address', 'user_agent', 'risk_score', 'is_flagged'
            ),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def customer_display(self, obj):
        """Display customer information"""
        if obj.customer:
            return f"{obj.customer.email}"
        elif obj.customer_email:
            return f"{obj.customer_email} (Guest)"
        return "Unknown"
    customer_display.short_description = 'Customer'

    def amount_display(self, obj):
        """Display amount with currency"""
        return f"{obj.amount} {obj.currency.code}"
    amount_display.short_description = 'Amount'

    def status_badge(self, obj):
        """Display status with color coding"""
        colors = {
            'pending': '#ffc107',
            'processing': '#17a2b8',
            'completed': '#28a745',
            'failed': '#dc3545',
            'cancelled': '#6c757d',
            'expired': '#fd7e14',
            'refunded': '#20c997',
            'partially_refunded': '#17a2b8',
            'disputed': '#e83e8c',
            'frozen': '#6f42c1'
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'

    def transaction_hash(self, obj):
        """Display transaction hash for verification"""
        return obj.get_transaction_hash()
    transaction_hash.short_description = 'Hash'

    actions = ['mark_as_completed', 'mark_as_failed', 'flag_for_review']

    def mark_as_completed(self, request, queryset):
        """Mark selected transactions as completed"""
        updated = 0
        for transaction in queryset:
            if transaction.status in ['pending', 'processing']:
                transaction.mark_as_completed()
                updated += 1
        self.message_user(request, f"{updated} transactions marked as completed.")
    mark_as_completed.short_description = "Mark selected transactions as completed"

    def mark_as_failed(self, request, queryset):
        """Mark selected transactions as failed"""
        updated = 0
        for transaction in queryset:
            if transaction.status in ['pending', 'processing']:
                transaction.mark_as_failed("Manually marked as failed by admin")
                updated += 1
        self.message_user(request, f"{updated} transactions marked as failed.")
    mark_as_failed.short_description = "Mark selected transactions as failed"

    def flag_for_review(self, request, queryset):
        """Flag selected transactions for manual review"""
        updated = queryset.update(is_flagged=True)
        self.message_user(request, f"{updated} transactions flagged for review.")
    flag_for_review.short_description = "Flag selected transactions for review"


@admin.register(PaymentLink)
class PaymentLinkAdmin(admin.ModelAdmin):
    """Admin interface for Payment Link"""
    list_display = [
        'title', 'merchant', 'amount_display', 'slug', 'is_active',
        'usage_display', 'expires_at', 'created_at'
    ]
    list_filter = [
        'is_active', 'is_amount_flexible', 'require_name', 'require_email',
        'require_phone', 'created_at', 'merchant'
    ]
    search_fields = ['title', 'description', 'slug']
    readonly_fields = [
        'id', 'slug', 'current_uses', 'created_at', 'updated_at',
        'link_url'
    ]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('merchant', 'title', 'description')
        }),
        ('Amount Settings', {
            'fields': (
                'currency', 'amount', 'is_amount_flexible',
                'min_amount', 'max_amount'
            )
        }),
        ('Link Configuration', {
            'fields': ('slug', 'is_active', 'expires_at', 'max_uses', 'current_uses')
        }),
        ('Customer Requirements', {
            'fields': (
                'require_name', 'require_email', 'require_phone', 'require_address'
            )
        }),
        ('Payment Settings', {
            'fields': ('allowed_payment_methods', 'success_url', 'cancel_url')
        }),
        ('Metadata', {
            'fields': ('metadata',),
            'classes': ('collapse',)
        }),
        ('URLs', {
            'fields': ('link_url',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def amount_display(self, obj):
        """Display amount with currency"""
        if obj.is_amount_flexible:
            return f"{obj.min_amount}-{obj.max_amount} {obj.currency.code} (flexible)"
        return f"{obj.amount} {obj.currency.code}"
    amount_display.short_description = 'Amount'

    def usage_display(self, obj):
        """Display usage information"""
        if obj.max_uses:
            return f"{obj.current_uses}/{obj.max_uses}"
        return f"{obj.current_uses}/∞"
    usage_display.short_description = 'Usage'

    def link_url(self, obj):
        """Display the payment link URL"""
        if obj.slug:
            url = obj.get_absolute_url()
            return format_html('<a href="{}" target="_blank">{}</a>', url, url)
        return "Not generated"
    link_url.short_description = 'Payment Link URL'


@admin.register(TransactionEvent)
class TransactionEventAdmin(admin.ModelAdmin):
    """Admin interface for Transaction Event"""
    list_display = [
        'transaction', 'event_type', 'old_status', 'new_status',
        'source', 'user', 'created_at'
    ]
    list_filter = [
        'event_type', 'old_status', 'new_status', 'source', 'created_at'
    ]
    search_fields = ['transaction__reference', 'description', 'event_type']
    readonly_fields = ['id', 'created_at']

    fieldsets = (
        ('Event Information', {
            'fields': ('transaction', 'event_type', 'description')
        }),
        ('Status Change', {
            'fields': ('old_status', 'new_status')
        }),
        ('Source', {
            'fields': ('source', 'user')
        }),
        ('Metadata', {
            'fields': ('metadata',),
            'classes': ('collapse',)
        }),
        ('Timestamp', {
            'fields': ('created_at',)
        }),
    )


@admin.register(Webhook)
class WebhookAdmin(admin.ModelAdmin):
    """Admin interface for Webhook"""
    list_display = [
        'transaction', 'event_type', 'url', 'attempts', 'is_delivered',
        'status_code', 'response_time_ms', 'created_at'
    ]
    list_filter = [
        'event_type', 'is_delivered', 'status_code', 'created_at'
    ]
    search_fields = ['transaction__reference', 'url', 'event_type']
    readonly_fields = [
        'id', 'created_at', 'updated_at', 'delivered_at'
    ]

    fieldsets = (
        ('Webhook Information', {
            'fields': ('transaction', 'url', 'event_type')
        }),
        ('Request Details', {
            'fields': ('payload', 'headers')
        }),
        ('Response Details', {
            'fields': (
                'status_code', 'response_body', 'response_time_ms'
            )
        }),
        ('Delivery Tracking', {
            'fields': (
                'attempts', 'max_attempts', 'is_delivered',
                'delivered_at', 'next_attempt_at'
            )
        }),
        ('Error Information', {
            'fields': ('error_message',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    actions = ['retry_webhooks']

    def retry_webhooks(self, request, queryset):
        """Retry failed webhooks"""
        failed_webhooks = queryset.filter(is_delivered=False)
        for webhook in failed_webhooks:
            webhook.schedule_retry()
        self.message_user(
            request,
            f"{failed_webhooks.count()} webhooks scheduled for retry."
        )
    retry_webhooks.short_description = "Retry failed webhooks"


# Admin site customization
admin.site.site_header = "PexiLabs Transaction Admin"
admin.site.site_title = "Transaction Admin"
admin.site.index_title = "Transaction Management"
