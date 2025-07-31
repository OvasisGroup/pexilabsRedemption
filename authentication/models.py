from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin, Group
from django.db import models
from django.utils import timezone
import uuid
import random
import string
import os
import hashlib
import secrets
from django.core.exceptions import ValidationError


def merchant_document_upload_path(instance, filename):
    """Generate upload path for merchant documents"""
    # Create path: merchant_documents/merchant_id/document_type/filename
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join('merchant_documents', str(instance.merchant.id), instance.document_type, filename)


class Country(models.Model):
    """Model for countries"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=3, unique=True)  # ISO country code
    phone_code = models.CharField(max_length=10, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Countries"
        ordering = ['name']

    def __str__(self):
        return self.name


class PreferredCurrency(models.Model):
    """Model for currencies"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=100, unique=True)  # ISO currency code
    symbol = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Preferred Currencies"
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.code})"


class UserRole(models.TextChoices):
    """User role choices"""
    ADMIN = 'admin', 'Admin'
    USER = 'user', 'User'
    MODERATOR = 'moderator', 'Moderator'
    STAFF = 'staff', 'Staff'


class CustomUserManager(BaseUserManager):
    """Custom user manager for email-based authentication"""
    
    def create_user(self, email, password=None, **extra_fields):
        """Create and return a regular user with an email and password"""
        if not email:
            raise ValueError('The Email field must be set')
        
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        """Create and return a superuser with an email and password"""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('is_verified', True)
        extra_fields.setdefault('role', UserRole.ADMIN)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        return self.create_user(email, password, **extra_fields)


class CustomUser(AbstractBaseUser, PermissionsMixin):
    """Custom User model with email as the unique identifier"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, max_length=255)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.USER
    )
    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_api_user = models.BooleanField(
        default=False,
        help_text='Whether this user was created for API key authentication'
    )
    last_login_at = models.DateTimeField(blank=True, null=True)
    refresh_token = models.TextField(blank=True, null=True)
    
    # Foreign key relationships
    country = models.ForeignKey(
        Country,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='users'
    )
    preferred_currency = models.ForeignKey(
        PreferredCurrency,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='users'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    objects = CustomUserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']
    
    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"
    
    def get_full_name(self):
        """Return the full name of the user"""
        return f"{self.first_name} {self.last_name}".strip()
    
    def get_short_name(self):
        """Return the short name of the user"""
        return self.first_name
    
    def save(self, *args, **kwargs):
        """Override save to update last_login_at and assign role-based groups"""
        # Handle last login update
        if self.pk:
            try:
                old_user = self.__class__.objects.get(pk=self.pk)
                if self.last_login != old_user.last_login:
                    self.last_login_at = timezone.now()
                
                # Check if role changed
                role_changed = old_user.role != self.role
            except self.__class__.DoesNotExist:
                role_changed = True
        else:
            role_changed = True
        
        super().save(*args, **kwargs)
        
        # Assign role-based groups if role changed or user is new
        if role_changed:
            self.assign_role_groups()
    
    def assign_role_groups(self):
        """Assign groups based on user role"""
        from django.contrib.auth.models import Group
        
        try:
            role_group = RoleGroup.objects.get(role=self.role)
            # Clear existing groups and assign new ones based on role
            self.groups.clear()
            for group in role_group.groups.all():
                self.groups.add(group)
        except RoleGroup.DoesNotExist:
            # If no role mapping exists, assign default groups based on role
            self._assign_default_role_groups()
    
    def _assign_default_role_groups(self):
        """Assign default groups based on role when no RoleGroup mapping exists"""
        from django.contrib.auth.models import Group
        
        # Clear existing groups
        self.groups.clear()
        
        # Default group assignments
        role_group_mappings = {
            UserRole.ADMIN: ['Administrators', 'Staff', 'Moderators', 'Users'],
            UserRole.STAFF: ['Staff', 'Moderators', 'Users'],
            UserRole.MODERATOR: ['Moderators', 'Users'],
            UserRole.USER: ['Users'],
        }
        
        group_names = role_group_mappings.get(self.role, ['Users'])
        
        for group_name in group_names:
            group, created = Group.objects.get_or_create(name=group_name)
            self.groups.add(group)
    
    def has_role_permission(self, permission_codename):
        """Check if user has permission through their role"""
        return self.user_permissions.filter(codename=permission_codename).exists() or \
               self.groups.filter(permissions__codename=permission_codename).exists()
    
    def get_role_permissions(self):
        """Get all permissions available to this user through their role and groups"""
        from django.contrib.auth.models import Permission
        
        # Get direct user permissions
        user_perms = self.user_permissions.all()
        
        # Get permissions through groups
        group_perms = Permission.objects.filter(group__user=self)
        
        # Combine and return unique permissions
        return (user_perms | group_perms).distinct()
    
    def can_manage_role(self, target_role):
        """Check if user can manage users with the target role"""
        role_hierarchy = {
            UserRole.ADMIN: [UserRole.ADMIN, UserRole.STAFF, UserRole.MODERATOR, UserRole.USER],
            UserRole.STAFF: [UserRole.MODERATOR, UserRole.USER],
            UserRole.MODERATOR: [UserRole.USER],
            UserRole.USER: [],
        }
        
        return target_role in role_hierarchy.get(self.role, [])


class UserSession(models.Model):
    """Model to track user sessions"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='sessions')
    session_key = models.CharField(max_length=255, unique=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Session for {self.user.email}"
    
    def is_expired(self):
        """Check if the session is expired"""
        return timezone.now() > self.expires_at


class RoleGroup(models.Model):
    """Model to map roles to groups for automatic assignment"""
    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        unique=True
    )
    groups = models.ManyToManyField(
        Group,
        related_name='role_mappings',
        blank=True,
        help_text='Groups that users with this role will automatically inherit'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Role Group Mapping'
        verbose_name_plural = 'Role Group Mappings'
        ordering = ['role']
    
    def __str__(self):
        return f"{self.get_role_display()} -> {', '.join([g.name for g in self.groups.all()])}"


class EmailOTP(models.Model):
    """Model for email OTP verification"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        'CustomUser',
        on_delete=models.CASCADE,
        related_name='email_otps'
    )
    otp_code = models.CharField(max_length=6)
    purpose = models.CharField(
        max_length=20,
        choices=[
            ('registration', 'Registration'),
            ('password_reset', 'Password Reset'),
            ('email_change', 'Email Change'),
        ],
        default='registration'
    )
    is_used = models.BooleanField(default=False)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    used_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Email OTP'
        verbose_name_plural = 'Email OTPs'

    def __str__(self):
        return f"OTP for {self.user.email} - {self.purpose}"

    @classmethod
    def generate_otp(cls, user, purpose='registration', validity_minutes=10):
        """Generate a new OTP for the user"""
        # Invalidate existing OTPs for the same purpose
        cls.objects.filter(
            user=user,
            purpose=purpose,
            is_used=False
        ).update(is_used=True)
        
        # Generate 6-digit OTP
        otp_code = ''.join(random.choices(string.digits, k=6))
        
        # Set expiration time
        expires_at = timezone.now() + timezone.timedelta(minutes=validity_minutes)
        
        return cls.objects.create(
            user=user,
            otp_code=otp_code,
            purpose=purpose,
            expires_at=expires_at
        )

    def is_valid(self):
        """Check if OTP is valid (not used and not expired)"""
        return not self.is_used and timezone.now() < self.expires_at

    def verify(self, code):
        """Verify the OTP code"""
        if self.otp_code == code and self.is_valid():
            self.is_used = True
            self.used_at = timezone.now()
            self.save()
            return True
        return False


class MerchantCategory(models.Model):
    """Model for merchant categories"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Merchant Categories"
        ordering = ['name']

    def __str__(self):
        return self.name


class MerchantStatus(models.TextChoices):
    """Merchant status choices"""
    PENDING = 'pending', 'Pending'
    APPROVED = 'approved', 'Approved'
    REJECTED = 'rejected', 'Rejected'
    SUSPENDED = 'suspended', 'Suspended'
    ACTIVE = 'active', 'Active'


class Merchant(models.Model):
    """Model for merchant accounts"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        'CustomUser',
        on_delete=models.CASCADE,
        related_name='merchant_account'
    )
    business_name = models.CharField(max_length=255)
    business_registration_number = models.CharField(max_length=100, blank=True, null=True)
    category = models.ForeignKey(
        MerchantCategory,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='merchants'
    )
    business_address = models.TextField()
    business_phone = models.CharField(max_length=20)
    business_email = models.EmailField()
    website_url = models.URLField(blank=True, null=True)
    description = models.TextField(blank=True)
    
    # Status and verification
    status = models.CharField(
        max_length=20,
        choices=MerchantStatus.choices,
        default=MerchantStatus.PENDING
    )
    is_verified = models.BooleanField(default=False)
    verification_notes = models.TextField(blank=True)
    verified_at = models.DateTimeField(blank=True, null=True)
    verified_by = models.ForeignKey(
        'CustomUser',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='verified_merchants'
    )
    
    # Financial information
    bank_account_name = models.CharField(max_length=255, blank=True)
    bank_account_number = models.CharField(max_length=50, blank=True)
    bank_name = models.CharField(max_length=255, blank=True)
    bank_routing_number = models.CharField(max_length=20, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.business_name} - {self.user.email}"

    def approve(self, verified_by=None):
        """Approve the merchant account"""
        self.status = MerchantStatus.APPROVED
        self.is_verified = True
        self.verified_at = timezone.now()
        if verified_by:
            self.verified_by = verified_by
        self.save()

    def reject(self, notes="", verified_by=None):
        """Reject the merchant account"""
        self.status = MerchantStatus.REJECTED
        self.is_verified = False
        self.verification_notes = notes
        if verified_by:
            self.verified_by = verified_by
        self.save()
    
    def is_information_complete(self):
        """Check if all required merchant information is complete"""
        # Define required fields that must be filled
        required_fields = [
            'business_name',
            'business_address',
            'business_phone',
            'business_email',
        ]
        
        # Check if any required field is empty
        for field in required_fields:
            value = getattr(self, field, None)
            if not value or (isinstance(value, str) and value.strip() == ''):
                return False
        
        # Check if bank details are provided (at least account details)
        bank_fields_complete = (
            self.bank_account_name and 
            self.bank_account_number and 
            self.bank_name
        )
        
        return bank_fields_complete
    
    def get_missing_information(self):
        """Get a list of missing required information"""
        missing = []
        
        # Check required business fields
        if not self.business_name or self.business_name.strip() == '':
            missing.append('Business Name')
        
        if not self.business_address or self.business_address.strip() == '':
            missing.append('Business Address')
        
        if not self.business_phone or self.business_phone.strip() == '':
            missing.append('Business Phone')
        
        if not self.business_email or self.business_email.strip() == '':
            missing.append('Business Email')
        
        # Check bank details
        if not (self.bank_account_name and self.bank_account_number and self.bank_name):
            missing.append('Bank Account Details')
        
        # Check category
        if not self.category:
            missing.append('Business Category')
            
        # Check business registration number
        if not self.business_registration_number or self.business_registration_number.strip() == '':
            missing.append('Business Registration Number')
        
        return missing


class DocumentTypeModel(models.Model):
    """Model for document types - allows dynamic management of document types"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True, help_text='Display name for the document type')
    code = models.CharField(max_length=50, unique=True, help_text='Internal code for the document type')
    description = models.TextField(blank=True, help_text='Description of what this document type is for')
    is_required = models.BooleanField(
        default=False, 
        help_text='Whether this document type is required for merchant verification'
    )
    is_active = models.BooleanField(default=True, help_text='Whether this document type is available for upload')
    display_order = models.PositiveIntegerField(
        default=0, 
        help_text='Order in which to display this document type (lower numbers first)'
    )
    icon = models.CharField(
        max_length=50, 
        blank=True, 
        help_text='CSS icon class for displaying this document type'
    )
    
    # File validation settings
    max_file_size_mb = models.PositiveIntegerField(
        default=10,
        help_text='Maximum file size allowed in MB'
    )
    allowed_extensions = models.CharField(
        max_length=200,
        default='.pdf,.jpg,.jpeg,.png,.doc,.docx',
        help_text='Comma-separated list of allowed file extensions'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Document Type'
        verbose_name_plural = 'Document Types'
        ordering = ['display_order', 'name']
    
    def __str__(self):
        return self.name
    
    def get_allowed_extensions_list(self):
        """Return list of allowed extensions"""
        return [ext.strip() for ext in self.allowed_extensions.split(',') if ext.strip()]
    
    def get_max_file_size_bytes(self):
        """Return max file size in bytes"""
        return self.max_file_size_mb * 1024 * 1024


class DocumentType(models.TextChoices):
    """Document type choices for merchant verification"""
    BUSINESS_LICENSE = 'business_license', 'Business License'
    TAX_CERTIFICATE = 'tax_certificate', 'Tax Certificate'
    BANK_STATEMENT = 'bank_statement', 'Bank Statement'
    IDENTITY_DOCUMENT = 'identity_document', 'Identity Document'
    BUSINESS_REGISTRATION = 'business_registration', 'Business Registration'
    UTILITY_BILL = 'utility_bill', 'Utility Bill'
    INSURANCE_CERTIFICATE = 'insurance_certificate', 'Insurance Certificate'
    FINANCIAL_STATEMENT = 'financial_statement', 'Financial Statement'
    OTHER = 'other', 'Other'


class DocumentStatus(models.TextChoices):
    """Document verification status choices"""
    PENDING = 'pending', 'Pending Review'
    APPROVED = 'approved', 'Approved'
    REJECTED = 'rejected', 'Rejected'
    EXPIRED = 'expired', 'Expired'


class MerchantDocument(models.Model):
    """Model for merchant document uploads"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    merchant = models.ForeignKey(
        Merchant,
        on_delete=models.CASCADE,
        related_name='documents'
    )
    document_type = models.CharField(
        max_length=50,
        choices=DocumentType.choices,
        help_text='Type of document being uploaded'
    )
    document_file = models.FileField(
        upload_to=merchant_document_upload_path,
        help_text='Upload the document file (PDF, JPG, PNG supported)'
    )
    original_filename = models.CharField(
        max_length=255,
        help_text='Original name of the uploaded file'
    )
    title = models.CharField(
        max_length=255,
        help_text='Document title or description'
    )
    description = models.TextField(
        blank=True,
        help_text='Additional description or notes about the document'
    )
    
    # Verification fields
    status = models.CharField(
        max_length=20,
        choices=DocumentStatus.choices,
        default=DocumentStatus.PENDING
    )
    is_required = models.BooleanField(
        default=False,
        help_text='Whether this document is required for merchant verification'
    )
    expiry_date = models.DateField(
        blank=True,
        null=True,
        help_text='Document expiry date (if applicable)'
    )
    verification_notes = models.TextField(
        blank=True,
        help_text='Notes from the verification process'
    )
    verified_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='verified_documents',
        help_text='Admin user who verified this document'
    )
    verified_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text='When the document was verified'
    )
    
    # File metadata
    file_size = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text='File size in bytes'
    )
    file_type = models.CharField(
        max_length=20,
        blank=True,
        help_text='File MIME type'
    )
    
    # Timestamps
    uploaded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Merchant Document'
        verbose_name_plural = 'Merchant Documents'
        ordering = ['-uploaded_at']
        unique_together = ['merchant', 'document_type', 'title']
    
    def __str__(self):
        return f"{self.merchant.business_name} - {self.get_document_type_display()}"
    
    def save(self, *args, **kwargs):
        """Override save to set file metadata"""
        if self.document_file:
            # Set original filename if not set
            if not self.original_filename:
                self.original_filename = self.document_file.name
            
            # Set file size
            if hasattr(self.document_file, 'size'):
                self.file_size = self.document_file.size
            
            # Set file type based on extension
            if self.document_file.name:
                ext = self.document_file.name.split('.')[-1].lower()
                file_type_mapping = {
                    'pdf': 'application/pdf',
                    'jpg': 'image/jpeg',
                    'jpeg': 'image/jpeg',
                    'png': 'image/png',
                    'doc': 'application/msword',
                    'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                }
                self.file_type = file_type_mapping.get(ext, 'application/octet-stream')
        
        super().save(*args, **kwargs)
    
    def approve(self, verified_by=None, notes=""):
        """Approve the document"""
        self.status = DocumentStatus.APPROVED
        self.verification_notes = notes
        self.verified_at = timezone.now()
        if verified_by:
            self.verified_by = verified_by
        self.save()
    
    def reject(self, verified_by=None, notes=""):
        """Reject the document"""
        self.status = DocumentStatus.REJECTED
        self.verification_notes = notes
        self.verified_at = timezone.now()
        if verified_by:
            self.verified_by = verified_by
        self.save()
    
    def is_expired(self):
        """Check if document is expired"""
        if self.expiry_date:
            return timezone.now().date() > self.expiry_date
        return False
    
    def get_file_size_display(self):
        """Return human-readable file size"""
        if not self.file_size:
            return "Unknown"
        
        for unit in ['B', 'KB', 'MB', 'GB']:
            if self.file_size < 1024.0:
                return f"{self.file_size:.1f} {unit}"
            self.file_size /= 1024.0
        return f"{self.file_size:.1f} TB"
    
    def get_verification_status_badge(self):
        """Return HTML badge for verification status"""
        status_badges = {
            DocumentStatus.PENDING: '<span class="badge badge-warning">Pending</span>',
            DocumentStatus.APPROVED: '<span class="badge badge-success">Approved</span>',
            DocumentStatus.REJECTED: '<span class="badge badge-danger">Rejected</span>',
            DocumentStatus.EXPIRED: '<span class="badge badge-secondary">Expired</span>',
        }
        return status_badges.get(self.status, '<span class="badge badge-light">Unknown</span>')
    
    @property
    def can_download(self):
        """Check if document can be downloaded"""
        return self.document_file and os.path.exists(self.document_file.path)
    
    @classmethod
    def get_required_documents_for_merchant(cls, merchant):
        """Get list of required documents for merchant verification"""
        required_docs = [
            DocumentType.BUSINESS_LICENSE,
            DocumentType.BUSINESS_REGISTRATION,
            DocumentType.TAX_CERTIFICATE,
            DocumentType.IDENTITY_DOCUMENT,
        ]
        
        existing_docs = cls.objects.filter(
            merchant=merchant,
            document_type__in=required_docs,
            status=DocumentStatus.APPROVED
        ).values_list('document_type', flat=True)
        
        missing_docs = [doc for doc in required_docs if doc not in existing_docs]
        return missing_docs
    
    @classmethod
    def merchant_verification_progress(cls, merchant):
        """Calculate merchant verification progress based on documents"""
        required_docs = [
            DocumentType.BUSINESS_LICENSE,
            DocumentType.BUSINESS_REGISTRATION,
            DocumentType.TAX_CERTIFICATE,
            DocumentType.IDENTITY_DOCUMENT,
        ]
        
        approved_docs = cls.objects.filter(
            merchant=merchant,
            document_type__in=required_docs,
            status=DocumentStatus.APPROVED
        ).count()
        
        progress_percentage = (approved_docs / len(required_docs)) * 100
        return {
            'approved_documents': approved_docs,
            'total_required': len(required_docs),
            'progress_percentage': round(progress_percentage, 1),
            'is_complete': approved_docs == len(required_docs)
        }


class AppKeyType(models.TextChoices):
    """App key types for different access levels"""
    PRODUCTION = 'production', 'Production'
    SANDBOX = 'sandbox', 'Sandbox'
    DEVELOPMENT = 'development', 'Development'


class AppKeyStatus(models.TextChoices):
    """App key status choices"""
    ACTIVE = 'active', 'Active'
    INACTIVE = 'inactive', 'Inactive'
    SUSPENDED = 'suspended', 'Suspended'
    REVOKED = 'revoked', 'Revoked'


class WhitelabelPartner(models.Model):
    """Model for whitelabel partners"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, help_text='Partner company name')
    code = models.CharField(
        max_length=50, 
        unique=True, 
        help_text='Unique partner code (alphanumeric, no spaces)'
    )
    contact_email = models.EmailField(help_text='Primary contact email')
    contact_phone = models.CharField(max_length=20, blank=True)
    website_url = models.URLField(blank=True, help_text='Partner website URL')
    
    # Business details
    business_address = models.TextField(blank=True)
    business_registration_number = models.CharField(max_length=100, blank=True)
    tax_id = models.CharField(max_length=50, blank=True)
    
    # Integration settings
    allowed_domains = models.TextField(
        blank=True,
        help_text='Comma-separated list of allowed domains for CORS (leave empty for no restrictions)'
    )
    webhook_url = models.URLField(
        blank=True,
        help_text='URL for receiving webhook notifications'
    )
    webhook_secret = models.CharField(
        max_length=255,
        blank=True,
        help_text='Secret key for webhook signature verification'
    )
    
    # Limits and quotas
    daily_api_limit = models.PositiveIntegerField(
        default=10000,
        help_text='Daily API request limit'
    )
    monthly_api_limit = models.PositiveIntegerField(
        default=300000,
        help_text='Monthly API request limit'
    )
    concurrent_connections_limit = models.PositiveIntegerField(
        default=100,
        help_text='Maximum concurrent connections allowed'
    )
    
    # Status and verification
    is_active = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)
    verification_notes = models.TextField(blank=True)
    verified_at = models.DateTimeField(blank=True, null=True)
    verified_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='verified_partners'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Whitelabel Partner'
        verbose_name_plural = 'Whitelabel Partners'
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.code})"
    
    def clean(self):
        """Validate partner data"""
        if self.code:
            # Ensure code is alphanumeric and no spaces
            if not self.code.replace('_', '').replace('-', '').isalnum():
                raise ValidationError({
                    'code': 'Partner code must contain only letters, numbers, hyphens, and underscores.'
                })
    
    def get_allowed_domains_list(self):
        """Return list of allowed domains"""
        if not self.allowed_domains:
            return []
        return [domain.strip() for domain in self.allowed_domains.split(',') if domain.strip()]
    
    def is_domain_allowed(self, domain):
        """Check if a domain is allowed for this partner"""
        allowed_domains = self.get_allowed_domains_list()
        if not allowed_domains:  # No restrictions
            return True
        return domain in allowed_domains
    
    def get_active_app_keys_count(self):
        """Get count of active app keys"""
        return self.app_keys.filter(status=AppKeyStatus.ACTIVE).count()
    
    def generate_webhook_secret(self):
        """Generate a new webhook secret"""
        self.webhook_secret = secrets.token_urlsafe(32)
        self.save(update_fields=['webhook_secret'])
        return self.webhook_secret


class AppKey(models.Model):
    """Model for API keys for whitelabel partners"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    partner = models.ForeignKey(
        WhitelabelPartner,
        on_delete=models.CASCADE,
        related_name='app_keys'
    )
    name = models.CharField(
        max_length=255,
        help_text='Descriptive name for this API key'
    )
    key_type = models.CharField(
        max_length=20,
        choices=AppKeyType.choices,
        default=AppKeyType.SANDBOX
    )
    
    # API Key components
    public_key = models.CharField(
        max_length=100,
        unique=True,
        help_text='Public portion of the API key (visible to partner)'
    )
    secret_key = models.CharField(
        max_length=255,
        help_text='Secret portion of the API key (hashed for security)'
    )
    key_prefix = models.CharField(
        max_length=20,
        default='pk_',
        help_text='Key prefix for identification'
    )
    
    # Permissions and scopes
    scopes = models.TextField(
        default='read,write',
        help_text='Comma-separated list of API scopes (read, write, admin)'
    )
    allowed_ips = models.TextField(
        blank=True,
        help_text='Comma-separated list of allowed IP addresses (leave empty for no restrictions)'
    )
    
    # Usage limits
    daily_request_limit = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text='Daily request limit for this key (overrides partner limit if set)'
    )
    monthly_request_limit = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text='Monthly request limit for this key (overrides partner limit if set)'
    )
    
    # Status and lifecycle
    status = models.CharField(
        max_length=20,
        choices=AppKeyStatus.choices,
        default=AppKeyStatus.ACTIVE
    )
    expires_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text='When this API key expires (leave empty for no expiration)'
    )
    last_used_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text='When this API key was last used'
    )
    
    # Usage tracking
    total_requests = models.PositiveBigIntegerField(
        default=0,
        help_text='Total number of API requests made with this key'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    revoked_at = models.DateTimeField(blank=True, null=True)
    revoked_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='revoked_app_keys'
    )
    
    class Meta:
        verbose_name = 'App Key'
        verbose_name_plural = 'App Keys'
        ordering = ['-created_at']
        unique_together = ['partner', 'name']
    
    def __str__(self):
        return f"{self.partner.name} - {self.name} ({self.get_key_type_display()})"
    
    def save(self, *args, **kwargs):
        """Override save to generate keys"""
        if not self.public_key or not self.secret_key:
            self._generate_keys()
        super().save(*args, **kwargs)
    
    def _generate_keys(self):
        """Generate public and secret keys"""
        # Generate public key: prefix + partner_code + random_string
        random_suffix = secrets.token_urlsafe(16)[:16]
        self.public_key = f"{self.key_prefix}{self.partner.code}_{random_suffix}"
        
        # Generate secret key (will be hashed)
        raw_secret = secrets.token_urlsafe(32)
        self.secret_key = self._hash_secret(raw_secret)
        
        # Store the raw secret temporarily for returning to user
        self._raw_secret = raw_secret
    
    def _hash_secret(self, secret):
        """Hash the secret key for storage"""
        return hashlib.sha256(secret.encode()).hexdigest()
    
    def verify_secret(self, secret):
        """Verify a provided secret against the stored hash"""
        return self.secret_key == self._hash_secret(secret)
    
    def get_scopes_list(self):
        """Return list of scopes"""
        return [scope.strip() for scope in self.scopes.split(',') if scope.strip()]
    
    def has_scope(self, scope):
        """Check if key has a specific scope"""
        return scope in self.get_scopes_list()
    
    def get_allowed_ips_list(self):
        """Return list of allowed IP addresses"""
        if not self.allowed_ips:
            return []
        return [ip.strip() for ip in self.allowed_ips.split(',') if ip.strip()]
    
    def is_ip_allowed(self, ip_address):
        """Check if an IP address is allowed for this key"""
        allowed_ips = self.get_allowed_ips_list()
        if not allowed_ips:  # No restrictions
            return True
        return ip_address in allowed_ips
    
    def is_active(self):
        """Check if the API key is active and valid"""
        if self.status != AppKeyStatus.ACTIVE:
            return False
        
        if self.expires_at and timezone.now() > self.expires_at:
            return False
        
        return True
    
    def is_expired(self):
        """Check if the API key is expired"""
        return self.expires_at and timezone.now() > self.expires_at
    
    def revoke(self, revoked_by=None, reason=""):
        """Revoke the API key"""
        self.status = AppKeyStatus.REVOKED
        self.revoked_at = timezone.now()
        if revoked_by:
            self.revoked_by = revoked_by
        self.save()
    
    def suspend(self, reason=""):
        """Suspend the API key"""
        self.status = AppKeyStatus.SUSPENDED
        self.save()
    
    def activate(self):
        """Activate the API key"""
        self.status = AppKeyStatus.ACTIVE
        self.save()
    
    def record_usage(self):
        """Record API key usage"""
        self.total_requests += 1
        self.last_used_at = timezone.now()
        self.save(update_fields=['total_requests', 'last_used_at'])
    
    def get_daily_request_limit(self):
        """Get effective daily request limit"""
        return self.daily_request_limit or self.partner.daily_api_limit
    
    def get_monthly_request_limit(self):
        """Get effective monthly request limit"""
        return self.monthly_request_limit or self.partner.monthly_api_limit
    
    @property
    def masked_secret(self):
        """Return masked version of secret for display"""
        if len(self.secret_key) > 8:
            return f"{self.secret_key[:4]}...{self.secret_key[-4:]}"
        return "****"


class AppKeyUsageLog(models.Model):
    """Model to track API key usage for analytics and rate limiting"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    app_key = models.ForeignKey(
        AppKey,
        on_delete=models.CASCADE,
        related_name='usage_logs'
    )
    
    # Request details
    endpoint = models.CharField(max_length=255, help_text='API endpoint accessed')
    method = models.CharField(max_length=10, help_text='HTTP method (GET, POST, etc.)')
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    
    # Response details
    status_code = models.PositiveIntegerField()
    response_time_ms = models.PositiveIntegerField(help_text='Response time in milliseconds')
    request_size_bytes = models.PositiveIntegerField(default=0)
    response_size_bytes = models.PositiveIntegerField(default=0)
    
    # Additional metadata
    request_id = models.CharField(max_length=50, blank=True)
    error_message = models.TextField(blank=True)
    
    # Timestamp
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'App Key Usage Log'
        verbose_name_plural = 'App Key Usage Logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['app_key', 'created_at']),
            models.Index(fields=['created_at']),
            models.Index(fields=['status_code']),
        ]
    
    def __str__(self):
        return f"{self.app_key.partner.name} - {self.method} {self.endpoint} ({self.status_code})"
    
    @classmethod
    def get_usage_stats(cls, app_key, start_date, end_date):
        """Get usage statistics for an app key within a date range"""
        logs = cls.objects.filter(
            app_key=app_key,
            created_at__range=[start_date, end_date]
        )
        
        total_requests = logs.count()
        successful_requests = logs.filter(status_code__lt=400).count()
        error_requests = logs.filter(status_code__gte=400).count()
        
        avg_response_time = logs.aggregate(
            models.Avg('response_time_ms')
        )['response_time_ms__avg'] or 0
        
        return {
            'total_requests': total_requests,
            'successful_requests': successful_requests,
            'error_requests': error_requests,
            'success_rate': (successful_requests / total_requests * 100) if total_requests > 0 else 0,
            'avg_response_time_ms': round(avg_response_time, 2)
        }


class NotificationType(models.TextChoices):
    """Notification type choices"""
    INFO = 'info', 'Info'
    WARNING = 'warning', 'Warning'
    SUCCESS = 'success', 'Success'
    ERROR = 'error', 'Error'
    REMINDER = 'reminder', 'Reminder'


class NotificationPriority(models.TextChoices):
    """Notification priority choices"""
    LOW = 'low', 'Low'
    NORMAL = 'normal', 'Normal'
    HIGH = 'high', 'High'
    URGENT = 'urgent', 'Urgent'


class Notification(models.Model):
    """Model for user notifications"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        'CustomUser',
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    
    # Notification content
    title = models.CharField(max_length=200)
    message = models.TextField()
    type = models.CharField(
        max_length=20,
        choices=NotificationType.choices,
        default=NotificationType.INFO
    )
    priority = models.CharField(
        max_length=20,
        choices=NotificationPriority.choices,
        default=NotificationPriority.NORMAL
    )
    
    # Action details
    action_url = models.URLField(blank=True, help_text='URL to redirect when notification is clicked')
    action_text = models.CharField(max_length=100, blank=True, help_text='Text for action button')
    
    # Status
    is_read = models.BooleanField(default=False)
    is_dismissed = models.BooleanField(default=False)
    read_at = models.DateTimeField(blank=True, null=True)
    
    # Auto-deletion
    expires_at = models.DateTimeField(blank=True, null=True, help_text='Auto-delete notification after this date')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['user', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.user.email}"
    
    def mark_as_read(self):
        """Mark notification as read"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])
    
    def dismiss(self):
        """Dismiss notification"""
        self.is_dismissed = True
        self.save(update_fields=['is_dismissed'])
    
    @classmethod
    def create_reminder(cls, user, title, message, action_url=None, action_text=None, priority=NotificationPriority.NORMAL):
        """Create a reminder notification"""
        return cls.objects.create(
            user=user,
            title=title,
            message=message,
            type=NotificationType.REMINDER,
            priority=priority,
            action_url=action_url,
            action_text=action_text
        )
    
    @classmethod
    def create_info_completeness_reminder(cls, merchant):
        """Create a notification reminder for incomplete merchant information"""
        missing_info = merchant.get_missing_information()
        if not missing_info:
            return None
        
        # Check if a similar reminder already exists and is unread
        existing = cls.objects.filter(
            user=merchant.user,
            title__icontains='Complete Your Business Information',
            is_read=False,
            is_dismissed=False
        ).first()
        
        if existing:
            return existing
        
        title = "Complete Your Business Information"
        message = f"You have {len(missing_info)} missing items in your business profile: {', '.join(missing_info[:3])}{'...' if len(missing_info) > 3 else ''}. Complete your profile to improve verification chances."
        
        return cls.create_reminder(
            user=merchant.user,
            title=title,
            message=message,
            action_url='/dashboard/merchant/profile/',
            action_text='Complete Profile',
            priority=NotificationPriority.HIGH
        )
