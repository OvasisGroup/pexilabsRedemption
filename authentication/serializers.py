from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.models import Group, Permission
from django.utils import timezone
from .models import (
    CustomUser, Country, PreferredCurrency, UserSession, RoleGroup, 
    EmailOTP, Merchant, MerchantCategory, MerchantStatus, MerchantDocument,
    WhitelabelPartner, AppKey, AppKeyUsageLog
)
from .utils import send_otp_email, send_merchant_creation_email


class GroupSerializer(serializers.ModelSerializer):
    """Serializer for Django groups"""
    
    class Meta:
        model = Group
        fields = ['id', 'name']


class PermissionSerializer(serializers.ModelSerializer):
    """Serializer for Django permissions"""
    
    class Meta:
        model = Permission
        fields = ['id', 'name', 'codename', 'content_type']


class RoleGroupSerializer(serializers.ModelSerializer):
    """Serializer for role group mappings"""
    groups = GroupSerializer(many=True, read_only=True)
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    
    class Meta:
        model = RoleGroup
        fields = ['id', 'role', 'role_display', 'groups', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class CountrySerializer(serializers.ModelSerializer):
    """Serializer for Country model"""
    
    class Meta:
        model = Country
        fields = ['id', 'name', 'code', 'phone_code', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class PreferredCurrencySerializer(serializers.ModelSerializer):
    """Serializer for PreferredCurrency model"""
    
    class Meta:
        model = PreferredCurrency
        fields = ['id', 'name', 'code', 'symbol', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration"""
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)
    business_name = serializers.CharField(max_length=255, required=False, allow_blank=True, help_text="Optional business name for merchant account creation")
    country = CountrySerializer(read_only=True)
    preferred_currency = PreferredCurrencySerializer(read_only=True)
    country_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    preferred_currency_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    
    class Meta:
        model = CustomUser
        fields = [
            'id', 'email', 'first_name', 'last_name', 'phone_number', 
            'password', 'password_confirm', 'business_name', 'role', 'country', 'preferred_currency',
            'country_id', 'preferred_currency_id', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def validate(self, attrs):
        """Validate password confirmation"""
        if attrs.get('password') != attrs.get('password_confirm'):
            raise serializers.ValidationError("Passwords don't match")
        
        # Remove password_confirm from attrs as it's not needed for user creation
        attrs.pop('password_confirm', None)
        return attrs
    
    def validate_email(self, value):
        """Validate email uniqueness"""
        if CustomUser.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value
    
    def create(self, validated_data):
        """Create user with encrypted password"""
        country_id = validated_data.pop('country_id', None)
        preferred_currency_id = validated_data.pop('preferred_currency_id', None)
        business_name = validated_data.pop('business_name', None)
        password = validated_data.pop('password')
        
        user = CustomUser.objects.create_user(password=password, **validated_data)
        
        # Set relationships if provided
        if country_id:
            try:
                country = Country.objects.get(id=country_id)
                user.country = country
            except Country.DoesNotExist:
                pass
        
        if preferred_currency_id:
            try:
                currency = PreferredCurrency.objects.get(id=preferred_currency_id)
                user.preferred_currency = currency
            except PreferredCurrency.DoesNotExist:
                pass
        
        # Store business_name for potential merchant account creation
        if business_name:
            user._business_name = business_name
        
        user.save()
        return user


class UserLoginSerializer(serializers.Serializer):
    """Serializer for user login"""
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    
    def validate(self, attrs):
        """Validate user credentials"""
        email = attrs.get('email')
        password = attrs.get('password')
        
        if email and password:
            user = authenticate(email=email, password=password)
            if not user:
                raise serializers.ValidationError('Invalid email or password.')
            if not user.is_active:
                raise serializers.ValidationError('User account is disabled.')
            
            attrs['user'] = user
            return attrs
        else:
            raise serializers.ValidationError('Must include "email" and "password".')


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for user profile"""
    country = CountrySerializer(read_only=True)
    preferred_currency = PreferredCurrencySerializer(read_only=True)
    country_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    preferred_currency_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    full_name = serializers.SerializerMethodField()
    groups = GroupSerializer(many=True, read_only=True)
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    
    class Meta:
        model = CustomUser
        fields = [
            'id', 'email', 'first_name', 'last_name', 'full_name', 'phone_number',
            'role', 'role_display', 'is_verified', 'is_active', 'last_login_at', 
            'country', 'preferred_currency', 'country_id', 'preferred_currency_id',
            'groups', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'email', 'role', 'is_verified', 'is_active', 'last_login_at',
            'created_at', 'updated_at', 'groups'
        ]
    
    def get_full_name(self, obj):
        """Return user's full name"""
        return obj.get_full_name()
    
    def update(self, instance, validated_data):
        """Update user profile"""
        country_id = validated_data.pop('country_id', None)
        preferred_currency_id = validated_data.pop('preferred_currency_id', None)
        
        # Update relationships if provided
        if country_id is not None:
            if country_id:
                try:
                    country = Country.objects.get(id=country_id)
                    instance.country = country
                except Country.DoesNotExist:
                    pass
            else:
                instance.country = None
        
        if preferred_currency_id is not None:
            if preferred_currency_id:
                try:
                    currency = PreferredCurrency.objects.get(id=preferred_currency_id)
                    instance.preferred_currency = currency
                except PreferredCurrency.DoesNotExist:
                    pass
            else:
                instance.preferred_currency = None
        
        # Update other fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        instance.save()
        return instance


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for changing password"""
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, validators=[validate_password])
    new_password_confirm = serializers.CharField(write_only=True)
    
    def validate(self, attrs):
        """Validate password change"""
        if attrs.get('new_password') != attrs.get('new_password_confirm'):
            raise serializers.ValidationError("New passwords don't match")
        return attrs
    
    def validate_old_password(self, value):
        """Validate old password"""
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect.")
        return value


class UserSessionSerializer(serializers.ModelSerializer):
    """Serializer for user sessions"""
    user_email = serializers.CharField(source='user.email', read_only=True)
    is_expired = serializers.SerializerMethodField()
    
    class Meta:
        model = UserSession
        fields = [
            'id', 'user_email', 'session_key', 'ip_address', 'user_agent',
            'is_active', 'is_expired', 'created_at', 'expires_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_is_expired(self, obj):
        """Check if session is expired"""
        return obj.is_expired()


class UserListSerializer(serializers.ModelSerializer):
    """Serializer for listing users (admin only)"""
    country_name = serializers.CharField(source='country.name', read_only=True)
    currency_name = serializers.CharField(source='preferred_currency.name', read_only=True)
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = CustomUser
        fields = [
            'id', 'email', 'first_name', 'last_name', 'full_name', 'phone_number',
            'role', 'is_verified', 'is_active', 'last_login_at', 'country_name',
            'currency_name', 'created_at'
        ]
    
    def get_full_name(self, obj):
        """Return user's full name"""
        return obj.get_full_name()


class UserRoleManagementSerializer(serializers.ModelSerializer):
    """Serializer for managing user roles (admin only)"""
    groups = GroupSerializer(many=True, read_only=True)
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = CustomUser
        fields = [
            'id', 'email', 'first_name', 'last_name', 'full_name', 'phone_number',
            'role', 'role_display', 'is_verified', 'is_active', 'is_staff', 
            'groups', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'email', 'first_name', 'last_name', 'phone_number',
            'is_verified', 'created_at', 'updated_at', 'groups'
        ]
    
    def get_full_name(self, obj):
        """Return user's full name"""
        return obj.get_full_name()
    
    def update(self, instance, validated_data):
        """Update user role and trigger group reassignment"""
        old_role = instance.role
        instance = super().update(instance, validated_data)
        
        # If role changed, reassign groups
        if old_role != instance.role:
            instance.assign_role_groups()
        
        return instance


class EmailOTPSerializer(serializers.ModelSerializer):
    """Serializer for Email OTP"""
    class Meta:
        model = EmailOTP
        fields = ['id', 'purpose', 'created_at', 'expires_at', 'is_used']
        read_only_fields = ['id', 'created_at', 'expires_at', 'is_used']


class OTPVerificationSerializer(serializers.Serializer):
    """Serializer for OTP verification"""
    email = serializers.EmailField()
    otp_code = serializers.CharField(max_length=6, min_length=6)
    purpose = serializers.CharField(default='registration')
    
    def validate(self, attrs):
        """Validate OTP code"""
        email = attrs.get('email')
        otp_code = attrs.get('otp_code')
        purpose = attrs.get('purpose', 'registration')
        
        try:
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            raise serializers.ValidationError("User with this email does not exist.")
        
        # Find valid OTP
        otp_instance = EmailOTP.objects.filter(
            user=user,
            purpose=purpose,
            is_used=False,
            expires_at__gt=timezone.now()
        ).order_by('-created_at').first()
        
        if not otp_instance:
            raise serializers.ValidationError("No valid OTP found. Please request a new one.")
        
        if not otp_instance.verify(otp_code):
            raise serializers.ValidationError("Invalid or expired OTP code.")
        
        attrs['user'] = user
        attrs['otp_instance'] = otp_instance
        return attrs


class ResendOTPSerializer(serializers.Serializer):
    """Serializer for resending OTP"""
    email = serializers.EmailField()
    purpose = serializers.CharField(default='registration')
    
    def validate_email(self, value):
        """Validate user exists"""
        try:
            user = CustomUser.objects.get(email=value)
            self.user = user
            return value
        except CustomUser.DoesNotExist:
            raise serializers.ValidationError("User with this email does not exist.")


class MerchantCategorySerializer(serializers.ModelSerializer):
    """Serializer for merchant categories"""
    class Meta:
        model = MerchantCategory
        fields = ['id', 'name', 'code', 'description', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class MerchantSerializer(serializers.ModelSerializer):
    """Serializer for merchant accounts"""
    user = UserProfileSerializer(read_only=True)
    category = MerchantCategorySerializer(read_only=True)
    category_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    
    class Meta:
        model = Merchant
        fields = [
            'id', 'user', 'business_name', 'business_registration_number',
            'category', 'category_id', 'business_address', 'business_phone',
            'business_email', 'website_url', 'description', 'status',
            'is_verified', 'verification_notes', 'verified_at', 'verified_by',
            'bank_account_name', 'bank_account_number', 'bank_name',
            'bank_routing_number', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'user', 'status', 'is_verified', 'verification_notes',
            'verified_at', 'verified_by', 'created_at', 'updated_at'
        ]
    
    def create(self, validated_data):
        """Create merchant account"""
        category_id = validated_data.pop('category_id', None)
        user = self.context['request'].user
        
        # Check if user already has a merchant account
        if hasattr(user, 'merchant_account'):
            raise serializers.ValidationError("User already has a merchant account.")
        
        merchant = Merchant.objects.create(user=user, **validated_data)
        
        # Set category if provided
        if category_id:
            try:
                category = MerchantCategory.objects.get(id=category_id)
                merchant.category = category
                merchant.save()
            except MerchantCategory.DoesNotExist:
                pass
        
        return merchant


class MerchantOnboardingSerializer(serializers.ModelSerializer):
    """Serializer for merchant onboarding during registration"""
    class Meta:
        model = Merchant
        fields = [
            'business_name', 'business_registration_number', 'business_address',
            'business_phone', 'business_email', 'website_url', 'description', 'category'
        ]
    
    def validate_business_email(self, value):
        """Validate business email"""
        if not value:
            raise serializers.ValidationError("Business email is required.")
        return value


class MerchantStatusUpdateSerializer(serializers.Serializer):
    """Serializer for updating merchant status"""
    status = serializers.ChoiceField(choices=MerchantStatus.choices)
    verification_notes = serializers.CharField(required=False, allow_blank=True)
    
    def update(self, instance, validated_data):
        """Update merchant status"""
        old_status = instance.status
        new_status = validated_data.get('status')
        verification_notes = validated_data.get('verification_notes', '')
        
        instance.status = new_status
        instance.verification_notes = verification_notes
        
        if new_status == MerchantStatus.APPROVED:
            instance.approve(verified_by=self.context['request'].user)
        elif new_status == MerchantStatus.REJECTED:
            instance.reject(notes=verification_notes, verified_by=self.context['request'].user)
        else:
            if self.context['request'].user:
                instance.verified_by = self.context['request'].user
            instance.save()
        
        # Send status update email
        from .utils import send_merchant_status_update_email
        send_merchant_status_update_email(instance.user, instance, old_status, new_status)
        
        return instance


# Update UserRegistrationSerializer to include merchant onboarding
class UserRegistrationWithMerchantSerializer(UserRegistrationSerializer):
    """Enhanced registration serializer with merchant onboarding"""
    merchant_data = MerchantOnboardingSerializer(required=False, allow_null=True)
    create_merchant_account = serializers.BooleanField(default=False)
    
    class Meta(UserRegistrationSerializer.Meta):
        fields = UserRegistrationSerializer.Meta.fields + ['merchant_data', 'create_merchant_account']
    
    def create(self, validated_data):
        """Create user and optionally create merchant account"""
        merchant_data = validated_data.pop('merchant_data', None)
        create_merchant_account = validated_data.pop('create_merchant_account', False)
        
        # Create user first
        user = super().create(validated_data)
        
        # Generate and send OTP
        otp_instance = EmailOTP.generate_otp(user, purpose='registration')
        send_otp_email(user, otp_instance, purpose='registration')
        
        # Create merchant account if requested
        if create_merchant_account:
            # Use provided merchant_data or create basic merchant account from business_name
            if merchant_data:
                merchant = Merchant.objects.create(
                    user=user,
                    **merchant_data
                )
            elif hasattr(user, '_business_name') and user._business_name:
                # Create basic merchant account using business_name from registration
                merchant = Merchant.objects.create(
                    user=user,
                    business_name=user._business_name,
                    business_email=user.email,
                    business_phone=user.phone_number or '',
                    description=f"Merchant account for {user._business_name}"
                )
            else:
                # Create minimal merchant account
                merchant = Merchant.objects.create(
                    user=user,
                    business_name=f"{user.first_name} {user.last_name}",
                    business_email=user.email,
                    business_phone=user.phone_number or '',
                    description=f"Merchant account for {user.first_name} {user.last_name}"
                )
            
            # Send merchant creation email
            send_merchant_creation_email(user, merchant)
            
            # Add merchant info to response
            user._merchant_created = True
            user._merchant_id = merchant.id
        
        return user


class MerchantDocumentSerializer(serializers.ModelSerializer):
    """Serializer for merchant document uploads"""
    original_filename = serializers.CharField(read_only=True)
    file_size_display = serializers.CharField(source='get_file_size_display', read_only=True)
    file_type = serializers.CharField(read_only=True)
    verification_status_badge = serializers.CharField(source='get_verification_status_badge', read_only=True)
    is_expired = serializers.BooleanField(read_only=True)
    can_download = serializers.BooleanField(read_only=True)
    merchant_name = serializers.CharField(source='merchant.business_name', read_only=True)
    verified_by_name = serializers.CharField(source='verified_by.get_full_name', read_only=True)
    
    class Meta:
        model = MerchantDocument
        fields = [
            'id', 'merchant', 'merchant_name', 'document_type', 'document_file',
            'original_filename', 'title', 'description', 'status', 'is_required',
            'expiry_date', 'verification_notes', 'verified_by', 'verified_by_name',
            'verified_at', 'file_size', 'file_size_display', 'file_type',
            'verification_status_badge', 'is_expired', 'can_download',
            'uploaded_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'original_filename', 'file_size', 'file_type', 'verified_at',
            'uploaded_at', 'updated_at'
        ]
    
    def validate_document_file(self, value):
        """Validate uploaded document file"""
        if not value:
            raise serializers.ValidationError("Document file is required.")
        
        # Check file size (10MB limit)
        max_size = 10 * 1024 * 1024  # 10MB
        if value.size > max_size:
            raise serializers.ValidationError(
                f"File size ({value.size} bytes) exceeds maximum allowed size (10MB)."
            )
        
        # Check file extension
        allowed_extensions = ['.pdf', '.jpg', '.jpeg', '.png', '.doc', '.docx']
        file_extension = value.name.lower().split('.')[-1]
        if f".{file_extension}" not in allowed_extensions:
            raise serializers.ValidationError(
                f"File type .{file_extension} is not allowed. "
                f"Allowed types: {', '.join(allowed_extensions)}"
            )
        
        return value
    
    def validate_expiry_date(self, value):
        """Validate expiry date"""
        if value and value <= timezone.now().date():
            raise serializers.ValidationError("Expiry date must be in the future.")
        return value
    
    def validate(self, attrs):
        """Additional validation"""
        merchant = attrs.get('merchant')
        document_type = attrs.get('document_type')
        title = attrs.get('title')
        
        # Check for duplicate documents of the same type and title for the merchant
        if self.instance:
            # Exclude current instance when updating
            existing = MerchantDocument.objects.filter(
                merchant=merchant,
                document_type=document_type,
                title=title
            ).exclude(id=self.instance.id)
        else:
            existing = MerchantDocument.objects.filter(
                merchant=merchant,
                document_type=document_type,
                title=title
            )
        
        if existing.exists():
            raise serializers.ValidationError(
                f"A document of type '{document_type}' with title '{title}' "
                "already exists for this merchant."
            )
        
        return attrs


class MerchantDocumentListSerializer(serializers.ModelSerializer):
    """Simplified serializer for merchant document listings"""
    file_size_display = serializers.CharField(source='get_file_size_display', read_only=True)
    document_type_display = serializers.CharField(source='get_document_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    is_expired = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = MerchantDocument
        fields = [
            'id', 'document_type', 'document_type_display', 'title',
            'status', 'status_display', 'is_required', 'expiry_date',
            'is_expired', 'file_size_display', 'uploaded_at'
        ]


class MerchantWithDocumentsSerializer(serializers.ModelSerializer):
    """Extended merchant serializer that includes documents"""
    documents = MerchantDocumentListSerializer(many=True, read_only=True)
    document_count = serializers.IntegerField(source='documents.count', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    user_full_name = serializers.CharField(source='user.get_full_name', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    verification_progress = serializers.SerializerMethodField()
    
    class Meta:
        model = Merchant
        fields = [
            'id', 'user', 'user_email', 'user_full_name', 'business_name',
            'business_registration_number', 'category', 'category_name',
            'business_address', 'business_phone', 'business_email', 'website_url',
            'description', 'status', 'is_verified', 'verification_notes',
            'verified_at', 'documents', 'document_count', 'verification_progress',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']
    
    def get_verification_progress(self, obj):
        """Get document verification progress"""
        return MerchantDocument.merchant_verification_progress(obj)


class DocumentUploadSerializer(serializers.Serializer):
    """Serializer for document upload endpoint"""
    document_type = serializers.ChoiceField(choices=MerchantDocument._meta.get_field('document_type').choices)
    title = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True)
    document_file = serializers.FileField()
    is_required = serializers.BooleanField(default=False)
    expiry_date = serializers.DateField(required=False, allow_null=True)
    
    def validate_document_file(self, value):
        """Validate uploaded document file"""
        if not value:
            raise serializers.ValidationError("Document file is required.")
        
        # Check file size (10MB limit)
        max_size = 10 * 1024 * 1024  # 10MB
        if value.size > max_size:
            raise serializers.ValidationError(
                f"File size exceeds maximum allowed size (10MB)."
            )
        
        # Check file extension
        allowed_extensions = ['.pdf', '.jpg', '.jpeg', '.png', '.doc', '.docx']
        file_extension = value.name.lower().split('.')[-1]
        if f".{file_extension}" not in allowed_extensions:
            raise serializers.ValidationError(
                f"File type .{file_extension} is not allowed. "
                f"Allowed types: {', '.join(allowed_extensions)}"
            )
        
        return value


# === App Key Generation Module Serializers ===

class WhitelabelPartnerSerializer(serializers.ModelSerializer):
    """Serializer for whitelabel partners"""
    app_keys_count = serializers.SerializerMethodField()
    allowed_domains_list = serializers.SerializerMethodField()
    
    class Meta:
        model = WhitelabelPartner
        fields = [
            'id', 'name', 'code', 'contact_email', 'contact_phone', 'website_url',
            'business_address', 'business_registration_number', 'tax_id',
            'allowed_domains', 'allowed_domains_list', 'webhook_url',
            'daily_api_limit', 'monthly_api_limit', 'concurrent_connections_limit',
            'is_active', 'is_verified', 'verification_notes', 'verified_at',
            'app_keys_count', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'is_verified', 'verified_at', 'app_keys_count', 
            'created_at', 'updated_at'
        ]
    
    def get_app_keys_count(self, obj):
        """Get count of active app keys"""
        return obj.get_active_app_keys_count()
    
    def get_allowed_domains_list(self, obj):
        """Get list of allowed domains"""
        return obj.get_allowed_domains_list()
    
    def validate_code(self, value):
        """Validate partner code"""
        if not value.replace('_', '').replace('-', '').isalnum():
            raise serializers.ValidationError(
                'Partner code must contain only letters, numbers, hyphens, and underscores.'
            )
        return value.lower()


class WhitelabelPartnerCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating whitelabel partners"""
    
    class Meta:
        model = WhitelabelPartner
        fields = [
            'name', 'code', 'contact_email', 'contact_phone', 'website_url',
            'business_address', 'business_registration_number', 'tax_id',
            'allowed_domains', 'webhook_url', 'daily_api_limit', 
            'monthly_api_limit', 'concurrent_connections_limit'
        ]
    
    def validate_code(self, value):
        """Validate partner code"""
        if not value.replace('_', '').replace('-', '').isalnum():
            raise serializers.ValidationError(
                'Partner code must contain only letters, numbers, hyphens, and underscores.'
            )
        return value.lower()


class AppKeySerializer(serializers.ModelSerializer):
    """Serializer for app keys"""
    partner_name = serializers.SerializerMethodField()
    scopes_list = serializers.SerializerMethodField()
    allowed_ips_list = serializers.SerializerMethodField()
    is_active = serializers.SerializerMethodField()
    is_expired = serializers.SerializerMethodField()
    masked_secret = serializers.SerializerMethodField()
    effective_daily_limit = serializers.SerializerMethodField()
    effective_monthly_limit = serializers.SerializerMethodField()
    
    class Meta:
        model = AppKey
        fields = [
            'id', 'partner', 'partner_name', 'name', 'key_type', 'public_key',
            'masked_secret', 'scopes', 'scopes_list', 'allowed_ips', 'allowed_ips_list',
            'daily_request_limit', 'monthly_request_limit', 'effective_daily_limit',
            'effective_monthly_limit', 'status', 'expires_at', 'last_used_at',
            'total_requests', 'is_active', 'is_expired', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'public_key', 'masked_secret', 'total_requests', 'last_used_at',
            'created_at', 'updated_at', 'revoked_at'
        ]
    
    def get_partner_name(self, obj):
        """Get partner name"""
        return obj.partner.name
    
    def get_scopes_list(self, obj):
        """Get list of scopes"""
        return obj.get_scopes_list()
    
    def get_allowed_ips_list(self, obj):
        """Get list of allowed IPs"""
        return obj.get_allowed_ips_list()
    
    def get_is_active(self, obj):
        """Check if key is active"""
        return obj.is_active()
    
    def get_is_expired(self, obj):
        """Check if key is expired"""
        return obj.is_expired()
    
    def get_masked_secret(self, obj):
        """Get masked secret"""
        return obj.masked_secret
    
    def get_effective_daily_limit(self, obj):
        """Get effective daily limit"""
        return obj.get_daily_request_limit()
    
    def get_effective_monthly_limit(self, obj):
        """Get effective monthly limit"""
        return obj.get_monthly_request_limit()


class AppKeyCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating app keys"""
    raw_secret = serializers.CharField(read_only=True)
    
    class Meta:
        model = AppKey
        fields = [
            'partner', 'name', 'key_type', 'scopes', 'allowed_ips',
            'daily_request_limit', 'monthly_request_limit', 'expires_at',
            'public_key', 'raw_secret'
        ]
        read_only_fields = ['public_key', 'raw_secret']
    
    def create(self, validated_data):
        """Create app key and return raw secret"""
        app_key = super().create(validated_data)
        
        # Access the raw secret generated during save
        if hasattr(app_key, '_raw_secret'):
            validated_data['raw_secret'] = app_key._raw_secret
        
        return app_key
    
    def to_representation(self, instance):
        """Include raw secret in response only during creation"""
        data = super().to_representation(instance)
        if hasattr(instance, '_raw_secret'):
            data['raw_secret'] = instance._raw_secret
        return data


class AppKeyUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating app keys"""
    
    class Meta:
        model = AppKey
        fields = [
            'name', 'scopes', 'allowed_ips', 'daily_request_limit',
            'monthly_request_limit', 'expires_at', 'status'
        ]
    
    def validate_status(self, value):
        """Validate status transitions"""
        if self.instance and self.instance.status == 'revoked':
            if value != 'revoked':
                raise serializers.ValidationError('Cannot change status of revoked key.')
        return value


class AppKeyUsageLogSerializer(serializers.ModelSerializer):
    """Serializer for app key usage logs"""
    app_key_name = serializers.SerializerMethodField()
    partner_name = serializers.SerializerMethodField()
    
    class Meta:
        model = AppKeyUsageLog
        fields = [
            'id', 'app_key', 'app_key_name', 'partner_name', 'endpoint', 'method',
            'ip_address', 'user_agent', 'status_code', 'response_time_ms',
            'request_size_bytes', 'response_size_bytes', 'request_id',
            'error_message', 'created_at'
        ]
        read_only_fields = '__all__'
    
    def get_app_key_name(self, obj):
        """Get app key name"""
        return obj.app_key.name
    
    def get_partner_name(self, obj):
        """Get partner name"""
        return obj.app_key.partner.name


class AppKeyStatsSerializer(serializers.Serializer):
    """Serializer for app key usage statistics"""
    total_requests = serializers.IntegerField()
    successful_requests = serializers.IntegerField()
    error_requests = serializers.IntegerField()
    success_rate = serializers.FloatField()
    avg_response_time_ms = serializers.FloatField()
    start_date = serializers.DateField()
    end_date = serializers.DateField()


class AppKeyRegenerateSerializer(serializers.Serializer):
    """Serializer for regenerating app key secrets"""
    confirm = serializers.BooleanField(required=True)
    new_secret = serializers.CharField(read_only=True)
    
    def validate_confirm(self, value):
        """Validate confirmation"""
        if not value:
            raise serializers.ValidationError('You must confirm secret regeneration.')
        return value


class WebhookSecretRegenerateSerializer(serializers.Serializer):
    """Serializer for regenerating webhook secrets"""
    confirm = serializers.BooleanField(required=True)
    new_webhook_secret = serializers.CharField(read_only=True)
    
    def validate_confirm(self, value):
        """Validate confirmation"""
        if not value:
            raise serializers.ValidationError('You must confirm webhook secret regeneration.')
        return value
