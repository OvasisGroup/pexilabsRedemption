from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from django import forms
from django.utils import timezone
from django.utils.html import format_html
from import_export import resources, fields
from import_export.admin import ImportExportModelAdmin, ExportActionMixin
from import_export.widgets import ForeignKeyWidget, ManyToManyWidget
from .models import (
    CustomUser, Country, PreferredCurrency, UserSession, RoleGroup,
    EmailOTP, Merchant, MerchantCategory, MerchantDocument, DocumentTypeModel,
    WhitelabelPartner, AppKey, AppKeyUsageLog, Notification
)


# ============ RESOURCES FOR IMPORT/EXPORT ============

class CountryResource(resources.ModelResource):
    """Resource for importing/exporting countries"""
    class Meta:
        model = Country
        fields = ('id', 'name', 'code', 'phone_code', 'created_at', 'updated_at')
        export_order = ('name', 'code', 'phone_code', 'created_at', 'updated_at')


class PreferredCurrencyResource(resources.ModelResource):
    """Resource for importing/exporting currencies"""
    class Meta:
        model = PreferredCurrency
        fields = ('id', 'name', 'code', 'symbol', 'is_active', 'created_at', 'updated_at')
        export_order = ('name', 'code', 'symbol', 'is_active', 'created_at', 'updated_at')


class CustomUserResource(resources.ModelResource):
    """Resource for importing/exporting users"""
    country = fields.Field(
        column_name='country',
        attribute='country',
        widget=ForeignKeyWidget(Country, 'name')
    )
    preferred_currency = fields.Field(
        column_name='preferred_currency',
        attribute='preferred_currency',
        widget=ForeignKeyWidget(PreferredCurrency, 'code')
    )
    groups = fields.Field(
        column_name='groups',
        attribute='groups',
        widget=ManyToManyWidget(model='auth.Group', field='name')
    )
    
    class Meta:
        model = CustomUser
        fields = (
            'id', 'email', 'first_name', 'last_name', 'phone_number', 
            'role', 'is_verified', 'is_active', 'is_staff', 'is_superuser',
            'country', 'preferred_currency', 'groups', 'created_at', 'updated_at'
        )
        export_order = (
            'email', 'first_name', 'last_name', 'phone_number', 
            'role', 'is_verified', 'is_active', 'country', 'preferred_currency',
            'created_at', 'updated_at'
        )
        # Exclude sensitive fields from import/export
        exclude = ('password', 'refresh_token', 'user_permissions')

    def dehydrate_password(self, user):
        """Don't export passwords"""
        return "[HIDDEN]"


class UserSessionResource(resources.ModelResource):
    """Resource for importing/exporting user sessions"""
    user = fields.Field(
        column_name='user',
        attribute='user',
        widget=ForeignKeyWidget(CustomUser, 'email')
    )
    
    class Meta:
        model = UserSession
        fields = ('id', 'user', 'session_key', 'ip_address', 'user_agent', 'is_active', 'created_at', 'expires_at')
        export_order = ('user', 'ip_address', 'is_active', 'created_at', 'expires_at')


class MerchantCategoryResource(resources.ModelResource):
    """Resource for importing/exporting merchant categories"""
    class Meta:
        model = MerchantCategory
        fields = ('id', 'name', 'code', 'description', 'is_active', 'created_at', 'updated_at')
        export_order = ('name', 'code', 'description', 'is_active', 'created_at')


class DocumentTypeResource(resources.ModelResource):
    """Resource for importing/exporting document types"""
    class Meta:
        model = DocumentTypeModel
        fields = (
            'id', 'name', 'code', 'description', 'is_required', 'is_active',
            'display_order', 'max_file_size_mb', 'allowed_extensions',
            'icon', 'created_at', 'updated_at'
        )
        export_order = (
            'name', 'code', 'description', 'is_required', 'is_active',
            'display_order', 'max_file_size_mb', 'allowed_extensions'
        )


class MerchantResource(resources.ModelResource):
    """Resource for importing/exporting merchants"""
    user = fields.Field(
        column_name='user',
        attribute='user',
        widget=ForeignKeyWidget(CustomUser, 'email')
    )
    category = fields.Field(
        column_name='category',
        attribute='category',
        widget=ForeignKeyWidget(MerchantCategory, 'name')
    )
    verified_by = fields.Field(
        column_name='verified_by',
        attribute='verified_by',
        widget=ForeignKeyWidget(CustomUser, 'email')
    )
    
    class Meta:
        model = Merchant
        fields = (
            'id', 'user', 'business_name', 'category', 'description',
            'business_registration_number', 'business_address', 'business_phone',
            'business_email', 'website_url', 'status', 'is_verified',
            'verification_notes', 'verified_by', 'verified_at',
            'created_at', 'updated_at'
        )
        export_order = (
            'business_name', 'user', 'category', 'business_email',
            'business_phone', 'status', 'is_verified', 'created_at'
        )
        # Exclude sensitive financial information
        exclude = ('bank_account_number', 'bank_routing_number')


class MerchantDocumentResource(resources.ModelResource):
    """Resource for importing/exporting merchant documents"""
    merchant = fields.Field(
        column_name='merchant',
        attribute='merchant',
        widget=ForeignKeyWidget(Merchant, 'business_name')
    )
    document_type = fields.Field(
        column_name='document_type',
        attribute='document_type',
        widget=ForeignKeyWidget(DocumentTypeModel, 'name')
    )
    verified_by = fields.Field(
        column_name='verified_by',
        attribute='verified_by',
        widget=ForeignKeyWidget(CustomUser, 'email')
    )
    
    class Meta:
        model = MerchantDocument
        fields = (
            'id', 'merchant', 'document_type', 'title', 'description',
            'status', 'is_required', 'expiry_date', 'verification_notes',
            'verified_by', 'verified_at', 'file_size', 'file_type',
            'original_filename', 'uploaded_at', 'updated_at'
        )
        export_order = (
            'merchant', 'document_type', 'title', 'status',
            'is_required', 'verified_at', 'uploaded_at'
        )
        # Exclude actual file path for security
        exclude = ('document_file',)


class WhitelabelPartnerResource(resources.ModelResource):
    """Resource for importing/exporting whitelabel partners"""
    verified_by = fields.Field(
        column_name='verified_by',
        attribute='verified_by',
        widget=ForeignKeyWidget(CustomUser, 'email')
    )
    
    class Meta:
        model = WhitelabelPartner
        fields = (
            'id', 'name', 'code', 'contact_email', 'contact_phone',
            'website_url', 'business_address', 'business_registration_number',
            'tax_id', 'allowed_domains', 'webhook_url', 'daily_api_limit',
            'monthly_api_limit', 'concurrent_connections_limit',
            'is_active', 'is_verified', 'verification_notes',
            'verified_by', 'verified_at', 'created_at', 'updated_at'
        )
        export_order = (
            'name', 'code', 'contact_email', 'website_url',
            'is_active', 'is_verified', 'daily_api_limit', 'created_at'
        )
        # Exclude sensitive webhook secret
        exclude = ('webhook_secret',)


class AppKeyResource(resources.ModelResource):
    """Resource for importing/exporting app keys"""
    partner = fields.Field(
        column_name='partner',
        attribute='partner',
        widget=ForeignKeyWidget(WhitelabelPartner, 'name')
    )
    revoked_by = fields.Field(
        column_name='revoked_by',
        attribute='revoked_by',
        widget=ForeignKeyWidget(CustomUser, 'email')
    )
    
    class Meta:
        model = AppKey
        fields = (
            'id', 'partner', 'name', 'key_type', 'public_key',
            'scopes', 'allowed_ips', 'status', 'daily_request_limit',
            'monthly_request_limit', 'total_requests', 'expires_at',
            'last_used_at', 'revoked_at', 'revoked_by',
            'created_at', 'updated_at'
        )
        export_order = (
            'partner', 'name', 'key_type', 'public_key', 'status',
            'total_requests', 'last_used_at', 'created_at'
        )
        # Exclude sensitive secret key
        exclude = ('secret_key',)


class AppKeyUsageLogResource(resources.ModelResource):
    """Resource for importing/exporting app key usage logs"""
    app_key = fields.Field(
        column_name='app_key',
        attribute='app_key',
        widget=ForeignKeyWidget(AppKey, 'name')
    )
    
    class Meta:
        model = AppKeyUsageLog
        fields = (
            'id', 'app_key', 'endpoint', 'method', 'ip_address',
            'user_agent', 'status_code', 'response_time_ms',
            'request_size_bytes', 'response_size_bytes',
            'request_id', 'error_message', 'created_at'
        )
        export_order = (
            'app_key', 'endpoint', 'method', 'status_code',
            'response_time_ms', 'created_at'
        )


class NotificationResource(resources.ModelResource):
    """Resource for importing/exporting notifications"""
    user = fields.Field(
        column_name='user',
        attribute='user',
        widget=ForeignKeyWidget(CustomUser, 'email')
    )
    
    class Meta:
        model = Notification
        fields = (
            'id', 'user', 'title', 'message', 'type', 'priority',
            'action_url', 'action_text', 'is_read', 'is_dismissed',
            'read_at', 'expires_at', 'created_at', 'updated_at'
        )
        export_order = (
            'user', 'title', 'type', 'priority', 'is_read',
            'is_dismissed', 'created_at'
        )


# ============ FORM CLASSES ============

class UserCreationForm(forms.ModelForm):
    """A form for creating new users. Includes all the required fields, plus a repeated password."""
    password1 = forms.CharField(label='Password', widget=forms.PasswordInput)
    password2 = forms.CharField(label='Password confirmation', widget=forms.PasswordInput)

    class Meta:
        model = CustomUser
        fields = ('email', 'first_name', 'last_name', 'phone_number', 'role', 'country', 'preferred_currency')

    def clean_password2(self):
        # Check that the two password entries match
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords don't match")
        return password2

    def save(self, commit=True):
        # Save the provided password in hashed format
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class UserChangeForm(forms.ModelForm):
    """A form for updating users. Includes all the fields on the user, but replaces the password field with admin's password hash display field."""
    password = ReadOnlyPasswordHashField()

    class Meta:
        model = CustomUser
        fields = ('email', 'password', 'first_name', 'last_name', 'phone_number', 'role', 
                 'is_verified', 'is_active', 'is_staff', 'is_superuser', 'country', 
                 'preferred_currency', 'groups', 'user_permissions')

    def clean_password(self):
        # Regardless of what the user provides, return the initial value.
        # This is done here, rather than on the field, because the
        # field does not have access to the initial value
        return self.initial["password"]


# ============ ADMIN CLASSES WITH IMPORT/EXPORT ============

@admin.register(CustomUser)
class UserAdmin(ImportExportModelAdmin, BaseUserAdmin):
    # Import/Export configuration
    resource_class = CustomUserResource
    
    # The forms to add and change user instances
    form = UserChangeForm
    add_form = UserCreationForm

    # The fields to be used in displaying the User model.
    list_display = ('email', 'first_name', 'last_name', 'role', 'is_verified', 'is_active', 'is_staff', 'created_at')
    list_filter = ('role', 'is_verified', 'is_active', 'is_staff', 'is_superuser', 'country', 'preferred_currency')
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'phone_number')}),
        ('Permissions', {'fields': ('role', 'is_verified', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Relationships', {'fields': ('country', 'preferred_currency')}),
        ('Important dates', {'fields': ('last_login', 'last_login_at', 'created_at', 'updated_at')}),
        ('Tokens', {'fields': ('refresh_token',)}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'first_name', 'last_name', 'phone_number', 'role', 'country', 'preferred_currency', 'password1', 'password2'),
        }),
    )
    
    search_fields = ('email', 'first_name', 'last_name', 'phone_number')
    ordering = ('-created_at',)
    filter_horizontal = ('groups', 'user_permissions',)
    readonly_fields = ('created_at', 'updated_at', 'last_login_at')


@admin.register(Country)
class CountryAdmin(ImportExportModelAdmin):
    resource_class = CountryResource
    
    list_display = ('name', 'code', 'phone_code', 'created_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('name', 'code')
    ordering = ('name',)
    readonly_fields = ('id', 'created_at', 'updated_at')


@admin.register(PreferredCurrency)
class PreferredCurrencyAdmin(ImportExportModelAdmin):
    resource_class = PreferredCurrencyResource
    
    list_display = ('name', 'code', 'symbol', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at', 'updated_at')
    search_fields = ('name', 'code', 'symbol')
    ordering = ('name',)
    readonly_fields = ('id', 'created_at', 'updated_at')


@admin.register(UserSession)
class UserSessionAdmin(ImportExportModelAdmin):
    resource_class = UserSessionResource
    
    list_display = ('user', 'ip_address', 'is_active', 'created_at', 'expires_at')
    list_filter = ('is_active', 'created_at', 'expires_at')
    search_fields = ('user__email', 'ip_address', 'session_key')
    ordering = ('-created_at',)
    readonly_fields = ('id', 'created_at')
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')


@admin.register(RoleGroup)
class RoleGroupAdmin(ExportActionMixin, admin.ModelAdmin):
    list_display = ('role', 'get_groups_display', 'created_at')
    list_filter = ('role', 'created_at')
    filter_horizontal = ('groups',)
    readonly_fields = ('created_at', 'updated_at')
    
    def get_groups_display(self, obj):
        """Display comma-separated list of groups"""
        return ', '.join([group.name for group in obj.groups.all()]) or 'No groups'
    get_groups_display.short_description = 'Groups'
    
    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('groups')


@admin.register(EmailOTP)
class EmailOTPAdmin(ExportActionMixin, admin.ModelAdmin):
    """Admin for Email OTP"""
    list_display = ['user', 'purpose', 'otp_code', 'is_used', 'expires_at', 'created_at']
    list_filter = ['purpose', 'is_used', 'created_at']
    search_fields = ['user__email', 'user__first_name', 'user__last_name']
    readonly_fields = ['otp_code', 'expires_at', 'created_at', 'used_at']
    
    def has_add_permission(self, request):
        return False  # Don't allow manual creation
    
    def has_change_permission(self, request, obj=None):
        return False  # Don't allow editing


@admin.register(MerchantCategory)
class MerchantCategoryAdmin(ImportExportModelAdmin):
    """Admin for Merchant Categories"""
    resource_class = MerchantCategoryResource
    
    list_display = ['name', 'code', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'code', 'description']
    prepopulated_fields = {'code': ('name',)}


@admin.register(DocumentTypeModel)
class DocumentTypeAdmin(ImportExportModelAdmin):
    """Admin interface for document types"""
    resource_class = DocumentTypeResource
    
    list_display = [
        'name', 'code', 'is_required', 'is_active', 'display_order', 
        'max_file_size_mb', 'created_at'
    ]
    list_filter = [
        'is_required', 'is_active', 'created_at', 'updated_at'
    ]
    search_fields = ['name', 'code', 'description']
    list_editable = ['is_required', 'is_active', 'display_order']
    prepopulated_fields = {'code': ('name',)}
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'code', 'description', 'icon')
        }),
        ('Settings', {
            'fields': ('is_required', 'is_active', 'display_order')
        }),
        ('File Validation', {
            'fields': ('max_file_size_mb', 'allowed_extensions'),
            'description': 'Configure file upload restrictions for this document type'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    actions = ['make_required', 'make_optional', 'activate_types', 'deactivate_types']
    
    def make_required(self, request, queryset):
        """Mark selected document types as required"""
        count = queryset.update(is_required=True)
        self.message_user(request, f'{count} document types marked as required.')
    make_required.short_description = "Mark as required"
    
    def make_optional(self, request, queryset):
        """Mark selected document types as optional"""
        count = queryset.update(is_required=False)
        self.message_user(request, f'{count} document types marked as optional.')
    make_optional.short_description = "Mark as optional"
    
    def activate_types(self, request, queryset):
        """Activate selected document types"""
        count = queryset.update(is_active=True)
        self.message_user(request, f'{count} document types activated.')
    activate_types.short_description = "Activate selected types"
    
    def deactivate_types(self, request, queryset):
        """Deactivate selected document types"""
        count = queryset.update(is_active=False)
        self.message_user(request, f'{count} document types deactivated.')
    deactivate_types.short_description = "Deactivate selected types"


class MerchantDocumentInline(admin.TabularInline):
    """Inline admin for merchant documents"""
    model = MerchantDocument
    extra = 0
    readonly_fields = ('uploaded_at', 'verified_at', 'file_size', 'file_type', 'original_filename')
    fields = (
        'document_type', 'title', 'document_file', 'status', 'is_required',
        'expiry_date', 'verification_notes', 'verified_by', 'file_size', 'uploaded_at'
    )


@admin.register(MerchantDocument)
class MerchantDocumentAdmin(ImportExportModelAdmin):
    """Admin interface for merchant documents"""
    resource_class = MerchantDocumentResource
    
    list_display = [
        'merchant_business_name', 'document_type', 'title', 'status', 
        'is_required', 'expiry_date', 'file_size_display', 'uploaded_at'
    ]
    list_filter = [
        'document_type', 'status', 'is_required', 'uploaded_at', 
        'expiry_date', 'verified_at'
    ]
    search_fields = [
        'merchant__business_name', 'merchant__user__email', 'title', 
        'description', 'original_filename'
    ]
    readonly_fields = [
        'uploaded_at', 'updated_at', 'verified_at', 'file_size', 
        'file_type', 'original_filename', 'can_download'
    ]
    raw_id_fields = ['merchant', 'verified_by']
    
    fieldsets = (
        ('Document Information', {
            'fields': ('merchant', 'document_type', 'title', 'description', 'document_file')
        }),
        ('Status & Requirements', {
            'fields': ('status', 'is_required', 'expiry_date')
        }),
        ('Verification', {
            'fields': ('verification_notes', 'verified_by', 'verified_at')
        }),
        ('File Metadata', {
            'fields': ('original_filename', 'file_size', 'file_type', 'can_download'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('uploaded_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    actions = ['approve_documents', 'reject_documents', 'mark_as_expired']
    
    def merchant_business_name(self, obj):
        """Display merchant business name"""
        return obj.merchant.business_name
    merchant_business_name.short_description = 'Business Name'
    merchant_business_name.admin_order_field = 'merchant__business_name'
    
    def file_size_display(self, obj):
        """Display file size in human readable format"""
        return obj.get_file_size_display()
    file_size_display.short_description = 'File Size'
    
    def approve_documents(self, request, queryset):
        """Approve selected documents"""
        count = 0
        for document in queryset:
            if document.status != 'approved':
                document.approve(verified_by=request.user, notes="Approved via admin")
                count += 1
        
        self.message_user(request, f'{count} documents approved successfully.')
    approve_documents.short_description = "Approve selected documents"
    
    def reject_documents(self, request, queryset):
        """Reject selected documents"""
        count = 0
        for document in queryset:
            if document.status not in ['rejected', 'approved']:
                document.reject(verified_by=request.user, notes="Rejected via admin")
                count += 1
        
        self.message_user(request, f'{count} documents rejected.')
    reject_documents.short_description = "Reject selected documents"
    
    def mark_as_expired(self, request, queryset):
        """Mark selected documents as expired"""
        count = queryset.update(status='expired')
        self.message_user(request, f'{count} documents marked as expired.')
    mark_as_expired.short_description = "Mark as expired"


@admin.register(Merchant)
class MerchantAdmin(ImportExportModelAdmin):
    """Enhanced admin interface for merchants with document management"""
    resource_class = MerchantResource
    
    list_display = [
        'business_name', 'user_email', 'status', 'category', 
        'is_verified', 'document_count', 'verification_progress', 'created_at'
    ]
    list_filter = [
        'status', 'is_verified', 'category', 'created_at', 
        'verified_at', 'updated_at'
    ]
    search_fields = [
        'business_name', 'user__email', 'business_registration_number',
        'business_phone', 'business_email', 'description'
    ]
    readonly_fields = [
        'created_at', 'updated_at', 'verified_at', 
        'document_count', 'verification_progress'
    ]
    raw_id_fields = ['user', 'verified_by']
    
    inlines = [MerchantDocumentInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'business_name', 'category', 'description')
        }),
        ('Business Details', {
            'fields': (
                'business_registration_number', 'business_address', 
                'business_phone', 'business_email', 'website_url'
            )
        }),
        ('Status & Verification', {
            'fields': (
                'status', 'is_verified', 'verification_notes', 
                'verified_by', 'verified_at'
            )
        }),
        ('Financial Information', {
            'fields': (
                'bank_account_name', 'bank_account_number', 
                'bank_name', 'bank_routing_number'
            ),
            'classes': ('collapse',)
        }),
        ('Document Status', {
            'fields': ('document_count', 'verification_progress'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    actions = ['approve_merchants', 'reject_merchants', 'suspend_merchants']
    
    def user_email(self, obj):
        """Display user email"""
        return obj.user.email
    user_email.short_description = 'User Email'
    user_email.admin_order_field = 'user__email'
    
    def document_count(self, obj):
        """Display number of uploaded documents"""
        return obj.documents.count()
    document_count.short_description = 'Documents'
    
    def verification_progress(self, obj):
        """Display verification progress based on documents"""
        from .models import MerchantDocument
        progress = MerchantDocument.merchant_verification_progress(obj)
        return f"{progress['approved_documents']}/{progress['total_required']} ({progress['progress_percentage']}%)"
    verification_progress.short_description = 'Document Progress'
    
    def approve_merchants(self, request, queryset):
        """Approve selected merchants"""
        count = 0
        for merchant in queryset:
            if merchant.status != 'approved':
                merchant.approve(verified_by=request.user)
                count += 1
        
        self.message_user(request, f'{count} merchants approved successfully.')
    approve_merchants.short_description = "Approve selected merchants"
    
    def reject_merchants(self, request, queryset):
        """Reject selected merchants"""
        count = 0
        for merchant in queryset:
            if merchant.status not in ['rejected', 'approved']:
                merchant.reject(notes="Rejected via admin", verified_by=request.user)
                count += 1
        
        self.message_user(request, f'{count} merchants rejected.')
    reject_merchants.short_description = "Reject selected merchants"
    
    def suspend_merchants(self, request, queryset):
        """Suspend selected merchants"""
        count = queryset.update(status='suspended')
        self.message_user(request, f'{count} merchants suspended.')
    suspend_merchants.short_description = "Suspend selected merchants"


# === App Key Generation Module Admin ===

class AppKeyInline(admin.TabularInline):
    """Inline admin for app keys"""
    model = AppKey
    extra = 0
    readonly_fields = ('public_key', 'masked_secret', 'total_requests', 'last_used_at', 'created_at', 'usage_today')
    fields = (
        'name', 'key_type', 'public_key', 'masked_secret', 'status', 
        'scopes', 'expires_at', 'total_requests', 'usage_today', 'last_used_at'
    )

    def masked_secret(self, obj):
        """Display masked secret key"""
        return obj.masked_secret
    masked_secret.short_description = 'Secret Key'
    
    def usage_today(self, obj):
        """Display today's usage for this key"""
        if obj.pk:
            from django.utils import timezone
            today = timezone.now().date()
            count = obj.usage_logs.filter(created_at__date=today).count()
            return count
        return 0
    usage_today.short_description = 'Today'


@admin.register(WhitelabelPartner)
class WhitelabelPartnerAdmin(ImportExportModelAdmin):
    """Admin interface for whitelabel partners"""
    resource_class = WhitelabelPartnerResource
    
    list_display = [
        'name', 'code', 'contact_email', 'is_active', 'is_verified', 
        'app_keys_count', 'daily_api_limit', 'api_usage_today', 'created_at'
    ]
    list_filter = [
        'is_active', 'is_verified', 'created_at', 'verified_at'
    ]
    search_fields = [
        'name', 'code', 'contact_email', 'business_registration_number'
    ]
    readonly_fields = [
        'created_at', 'updated_at', 'verified_at', 'app_keys_count', 'api_usage_today', 'formatted_webhook_url'
    ]
    raw_id_fields = ['verified_by']
    
    inlines = [AppKeyInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'code', 'contact_email', 'contact_phone', 'website_url')
        }),
        ('Business Details', {
            'fields': (
                'business_address', 'business_registration_number', 'tax_id'
            ),
            'classes': ('collapse',)
        }),
        ('Integration Settings', {
            'fields': (
                'allowed_domains', 'webhook_url', 'formatted_webhook_url', 'webhook_secret'
            )
        }),
        ('API Limits & Quotas', {
            'fields': (
                'daily_api_limit', 'monthly_api_limit', 'concurrent_connections_limit'
            )
        }),
        ('Status & Verification', {
            'fields': (
                'is_active', 'is_verified', 'verification_notes', 
                'verified_by', 'verified_at'
            )
        }),
        ('Statistics', {
            'fields': ('app_keys_count', 'api_usage_today'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    actions = ['verify_partners', 'activate_partners', 'deactivate_partners', 'generate_webhook_secrets', 'view_api_statistics']
    
    def app_keys_count(self, obj):
        """Display number of app keys"""
        return obj.get_active_app_keys_count()
    app_keys_count.short_description = 'Active Keys'
    
    def api_usage_today(self, obj):
        """Display today's API usage"""
        from django.utils import timezone
        today = timezone.now().date()
        
        # Count API calls today across all app keys
        total_calls = 0
        for app_key in obj.app_keys.filter(status='active'):
            usage_logs = app_key.usage_logs.filter(created_at__date=today)
            total_calls += usage_logs.count()
        
        # Show usage vs limit
        if obj.daily_api_limit:
            percentage = (total_calls / obj.daily_api_limit) * 100
            return format_html(
                '<span style="color: {};">{}/{} ({}%)</span>',
                'red' if percentage > 80 else 'orange' if percentage > 60 else 'green',
                total_calls,
                obj.daily_api_limit,
                round(percentage, 1)
            )
        return total_calls
    api_usage_today.short_description = 'Today\'s Usage'
    
    def formatted_webhook_url(self, obj):
        """Display formatted webhook URL"""
        if obj.webhook_url:
            return format_html(
                '<a href="{}" target="_blank">{}</a>',
                obj.webhook_url,
                obj.webhook_url
            )
        return "Not configured"
    formatted_webhook_url.short_description = 'Webhook URL'
    
    def view_api_statistics(self, request, queryset):
        """View API statistics for selected partners"""
        from django.http import JsonResponse
        from django.utils import timezone
        
        stats = []
        for partner in queryset:
            partner_stats = {
                'partner': partner.name,
                'active_keys': partner.get_active_app_keys_count(),
                'daily_limit': partner.daily_api_limit,
                'monthly_limit': partner.monthly_api_limit,
                'total_usage_today': 0,
                'total_usage_this_month': 0
            }
            
            # Calculate usage statistics
            today = timezone.now().date()
            first_day_of_month = today.replace(day=1)
            
            for app_key in partner.app_keys.filter(status='active'):
                today_usage = app_key.usage_logs.filter(created_at__date=today).count()
                month_usage = app_key.usage_logs.filter(created_at__date__gte=first_day_of_month).count()
                
                partner_stats['total_usage_today'] += today_usage
                partner_stats['total_usage_this_month'] += month_usage
            
            stats.append(partner_stats)
        
        # For now, just show a success message with basic stats
        total_partners = len(stats)
        total_active_keys = sum(s['active_keys'] for s in stats)
        total_usage_today = sum(s['total_usage_today'] for s in stats)
        
        self.message_user(request, 
            f'Statistics for {total_partners} partners: '
            f'{total_active_keys} active keys, '
            f'{total_usage_today} API calls today.')
    view_api_statistics.short_description = "View API statistics"


@admin.register(AppKey)
class AppKeyAdmin(ImportExportModelAdmin):
    """Admin interface for app keys"""
    resource_class = AppKeyResource
    
    list_display = [
        'partner_name', 'name', 'key_type', 'public_key', 'status', 
        'scopes_display', 'total_requests', 'last_used_at', 'expires_at'
    ]
    list_filter = [
        'key_type', 'status', 'created_at', 'expires_at', 'last_used_at'
    ]
    search_fields = [
        'partner__name', 'partner__code', 'name', 'public_key'
    ]
    readonly_fields = [
        'public_key', 'secret_key', 'total_requests', 'last_used_at', 
        'created_at', 'updated_at', 'revoked_at', 'masked_secret'
    ]
    raw_id_fields = ['partner', 'revoked_by']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('partner', 'name', 'key_type')
        }),
        ('API Key Details', {
            'fields': (
                'key_prefix', 'public_key', 'masked_secret', 'secret_key'
            ),
            'description': 'The secret key is hashed for security. Only the public key should be shared.'
        }),
        ('Permissions & Access', {
            'fields': ('scopes', 'allowed_ips')
        }),
        ('Usage Limits', {
            'fields': ('daily_request_limit', 'monthly_request_limit')
        }),
        ('Status & Lifecycle', {
            'fields': (
                'status', 'expires_at', 'revoked_at', 'revoked_by'
            )
        }),
        ('Usage Statistics', {
            'fields': ('total_requests', 'last_used_at'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    actions = ['revoke_keys', 'suspend_keys', 'activate_keys', 'extend_expiry']
    
    def partner_name(self, obj):
        """Display partner name"""
        return obj.partner.name
    partner_name.short_description = 'Partner'
    partner_name.admin_order_field = 'partner__name'
    
    def scopes_display(self, obj):
        """Display scopes as comma-separated list"""
        return ', '.join(obj.get_scopes_list())
    scopes_display.short_description = 'Scopes'
    
    def masked_secret(self, obj):
        """Display masked secret key"""
        return obj.masked_secret
    masked_secret.short_description = 'Secret Key (Masked)'
    
    def revoke_keys(self, request, queryset):
        """Revoke selected API keys"""
        count = 0
        for key in queryset:
            if key.status != 'revoked':
                key.revoke(revoked_by=request.user)
                count += 1
        
        self.message_user(request, f'{count} API keys revoked.')
    revoke_keys.short_description = "Revoke selected keys"
    
    def suspend_keys(self, request, queryset):
        """Suspend selected API keys"""
        count = 0
        for key in queryset:
            if key.status == 'active':
                key.suspend()
                count += 1
        
        self.message_user(request, f'{count} API keys suspended.')
    suspend_keys.short_description = "Suspend selected keys"
    
    def activate_keys(self, request, queryset):
        """Activate selected API keys"""
        count = 0
        for key in queryset:
            if key.status in ['inactive', 'suspended']:
                key.activate()
                count += 1
        
        self.message_user(request, f'{count} API keys activated.')
    activate_keys.short_description = "Activate selected keys"
    
    def extend_expiry(self, request, queryset):
        """Extend expiry date by 1 year for selected keys"""
        from django.utils import timezone
        from datetime import timedelta
        
        count = 0
        for key in queryset:
            if key.expires_at:
                key.expires_at = key.expires_at + timedelta(days=365)
            else:
                key.expires_at = timezone.now() + timedelta(days=365)
            key.save()
            count += 1
        
        self.message_user(request, f'Extended expiry for {count} API keys by 1 year.')
    extend_expiry.short_description = "Extend expiry by 1 year"


@admin.register(AppKeyUsageLog)
class AppKeyUsageLogAdmin(ImportExportModelAdmin):
    """Admin interface for app key usage logs"""
    resource_class = AppKeyUsageLogResource
    
    list_display = [
        'app_key_name', 'partner_name', 'method', 'endpoint', 
        'status_code', 'response_time_ms', 'ip_address', 'created_at'
    ]
    list_filter = [
        'method', 'status_code', 'created_at', 
        'app_key__partner', 'app_key__key_type'
    ]
    search_fields = [
        'app_key__name', 'app_key__partner__name', 'endpoint', 
        'ip_address', 'request_id'
    ]
    readonly_fields = [
        'app_key', 'endpoint', 'method', 'ip_address', 'user_agent',
        'status_code', 'response_time_ms', 'request_size_bytes', 
        'response_size_bytes', 'request_id', 'error_message', 'created_at'
    ]
    
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Request Information', {
            'fields': (
                'app_key', 'endpoint', 'method', 'ip_address', 
                'user_agent', 'request_id'
            )
        }),
        ('Response Information', {
            'fields': (
                'status_code', 'response_time_ms', 'request_size_bytes', 
                'response_size_bytes', 'error_message'
            )
        }),
        ('Timestamp', {
            'fields': ('created_at',)
        })
    )
    
    def has_add_permission(self, request):
        """Disable manual creation of usage logs"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Make usage logs read-only"""
        return False
    
    def app_key_name(self, obj):
        """Display app key name"""
        return obj.app_key.name
    app_key_name.short_description = 'App Key'
    app_key_name.admin_order_field = 'app_key__name'
    
    def partner_name(self, obj):
        """Display partner name"""
        return obj.app_key.partner.name
    partner_name.short_description = 'Partner'
    partner_name.admin_order_field = 'app_key__partner__name'


@admin.register(Notification)
class NotificationAdmin(ImportExportModelAdmin):
    """Admin interface for notifications"""
    resource_class = NotificationResource
    
    list_display = [
        'title', 'user_email', 'type', 'priority', 'is_read', 
        'is_dismissed', 'created_at'
    ]
    list_filter = [
        'type', 'priority', 'is_read', 'is_dismissed', 'created_at'
    ]
    search_fields = [
        'title', 'message', 'user__email', 'user__first_name', 'user__last_name'
    ]
    readonly_fields = ['created_at', 'updated_at', 'read_at']
    raw_id_fields = ['user']
    
    fieldsets = (
        ('Notification Content', {
            'fields': ('user', 'title', 'message', 'type', 'priority')
        }),
        ('Action', {
            'fields': ('action_url', 'action_text')
        }),
        ('Status', {
            'fields': ('is_read', 'is_dismissed', 'read_at', 'expires_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    actions = ['mark_as_read', 'mark_as_dismissed', 'delete_read_notifications']
    
    def user_email(self, obj):
        """Display user email"""
        return obj.user.email
    user_email.short_description = 'User Email'
    user_email.admin_order_field = 'user__email'
    
    def mark_as_read(self, request, queryset):
        """Mark selected notifications as read"""
        count = 0
        for notification in queryset:
            if not notification.is_read:
                notification.mark_as_read()
                count += 1
        
        self.message_user(request, f'{count} notifications marked as read.')
    mark_as_read.short_description = 'Mark selected notifications as read'
    
    def mark_as_dismissed(self, request, queryset):
        """Dismiss selected notifications"""
        count = queryset.update(is_dismissed=True)
        self.message_user(request, f'{count} notifications dismissed.')
    mark_as_dismissed.short_description = 'Dismiss selected notifications'
    
    def delete_read_notifications(self, request, queryset):
        """Delete read notifications"""
        count = queryset.filter(is_read=True).delete()[0]
        self.message_user(request, f'{count} read notifications deleted.')
    delete_read_notifications.short_description = 'Delete read notifications'
