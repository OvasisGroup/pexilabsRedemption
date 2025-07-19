"""
Django signals for authentication app

This module contains signals that handle automatic actions when user verification
and other authentication events occur.
"""

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.conf import settings
from django.utils import timezone
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
import logging

from .models import CustomUser, Merchant, MerchantCategory

logger = logging.getLogger(__name__)


@receiver(pre_save, sender=CustomUser)
def track_verification_change(sender, instance, **kwargs):
    """Track when a user's verification status changes"""
    if instance.pk:
        try:
            old_instance = CustomUser.objects.get(pk=instance.pk)
            # Store the old verification status for comparison in post_save
            instance._verification_changed = old_instance.is_verified != instance.is_verified
            instance._was_verified = old_instance.is_verified
        except CustomUser.DoesNotExist:
            instance._verification_changed = False
            instance._was_verified = False
    else:
        # New user
        instance._verification_changed = instance.is_verified
        instance._was_verified = False


@receiver(post_save, sender=CustomUser)
def auto_create_merchant_on_verification(sender, instance, created, **kwargs):
    """
    Automatically create a merchant account when a user becomes verified.
    
    This signal is triggered when:
    1. A user's is_verified field changes from False to True
    2. A new user is created with is_verified=True (e.g., superuser)
    
    The merchant account will be created with:
    - Basic information from the user profile
    - Default category (if available)
    - Pending status (requires manual approval)
    """
    
    # Only proceed if user is verified
    if not instance.is_verified:
        return
    
    # Check if merchant account already exists
    if hasattr(instance, 'merchant_account'):
        logger.info(f"Merchant account already exists for user {instance.email}")
        return
    
    # For new users created as verified, always create merchant account
    if created:
        should_create_merchant = True
        logger.info(f"Creating merchant account for new verified user: {instance.email}")
    else:
        # For existing users, check if verification status changed
        verification_changed = getattr(instance, '_verification_changed', False)
        was_verified = getattr(instance, '_was_verified', False)
        
        should_create_merchant = verification_changed and not was_verified
        
        if verification_changed and not was_verified:
            logger.info(f"Creating merchant account for newly verified user: {instance.email}")
        
    if not should_create_merchant:
        return
    
    try:
        # Get default merchant category
        default_category = None
        try:
            # Try to get a default category (you can customize this logic)
            default_category = MerchantCategory.objects.filter(
                code__in=['general', 'default', 'other']
            ).first()
            
            if not default_category:
                default_category = MerchantCategory.objects.filter(is_active=True).first()
        except Exception as e:
            logger.warning(f"Could not determine default merchant category: {e}")
        
        # Create merchant account
        merchant = Merchant.objects.create(
            user=instance,
            business_name=f"{instance.get_full_name()}'s Business",
            business_email=instance.email,
            business_phone=instance.phone_number or '',
            business_address='',  # Will need to be filled by user
            category=default_category,
            description=f"Automatically created merchant account for {instance.get_full_name()}",
            status='pending',  # Requires manual approval
            is_verified=False,  # Merchant verification is separate from user verification
        )
        
        logger.info(f"✅ Auto-created merchant account for verified user: {instance.email} (Merchant ID: {merchant.id})")
        
        # Send welcome email about merchant account creation
        try:
            send_merchant_welcome_email(merchant)
        except Exception as email_error:
            logger.error(f"❌ Failed to send welcome email to {merchant.user.email}: {email_error}")
        
    except Exception as e:
        logger.error(f"❌ Failed to auto-create merchant account for user {instance.email}: {e}")


@receiver(post_save, sender=Merchant)
def log_merchant_status_changes(sender, instance, created, **kwargs):
    """Log merchant status changes for auditing purposes"""
    
    if created:
        logger.info(f"📝 New merchant account created: {instance.business_name} (ID: {instance.id}) for user {instance.user.email}")
        return
    
    # For existing merchants, log status changes
    if instance.pk:
        try:
            # Get the old instance from database to compare
            old_instance = Merchant.objects.get(pk=instance.pk)
            
            # Track status changes
            if hasattr(instance, '_state') and instance._state.db:
                # Only log if this is an update, not a fresh fetch from DB
                if old_instance.status != instance.status:
                    logger.info(f"🔄 Merchant status changed for {instance.business_name}: {old_instance.status} → {instance.status}")
                
                if old_instance.is_verified != instance.is_verified:
                    verification_status = "verified" if instance.is_verified else "unverified"
                    logger.info(f"✅ Merchant verification changed for {instance.business_name}: now {verification_status}")
                    
        except Merchant.DoesNotExist:
            pass


# Optional: Signal for cleanup when user is deleted
@receiver(post_save, sender=CustomUser)
def handle_user_deactivation(sender, instance, **kwargs):
    """Handle user deactivation - suspend related merchant accounts"""
    
    if not instance.is_active and hasattr(instance, 'merchant_account'):
        merchant = instance.merchant_account
        
        # Only suspend if not already suspended
        if merchant.status not in ['suspended', 'rejected']:
            old_status = merchant.status
            merchant.status = 'suspended'
            merchant.verification_notes = f"User account deactivated on {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}"
            merchant.save()
            
            logger.warning(f"⚠️ Merchant account suspended due to user deactivation: {merchant.business_name} (was {old_status})")


@receiver(post_save, sender=CustomUser)
def assign_user_to_merchants_group(sender, instance, created, **kwargs):
    """
    Automatically assign new users to the merchants group.
    
    This signal ensures that all newly registered users are automatically
    assigned to the 'merchants' group, which gives them basic merchant permissions.
    """
    from django.contrib.auth.models import Group
    from .models import UserRole
    
    # Only assign group for newly created users
    if not created:
        return
    
    try:
        # Get the merchants group
        merchants_group, group_created = Group.objects.get_or_create(name='merchants')
        
        # Only assign to merchants group if user doesn't have a specific role assigned
        # that would put them in a different group
        if instance.role == UserRole.USER or not instance.role:
            instance.groups.add(merchants_group)
            logger.info(f"Assigned user {instance.email} to merchants group")
        
        # Also check role group mappings for automatic assignment
        try:
            from .models import RoleGroup
            role_groups = RoleGroup.objects.filter(role=instance.role)
            for role_group in role_groups:
                for group in role_group.groups.all():
                    instance.groups.add(group)
                    logger.info(f"Assigned user {instance.email} to {group.name} group via role mapping")
        except Exception as e:
            logger.warning(f"Could not assign user {instance.email} to role groups: {e}")
            
    except Exception as e:
        logger.error(f"Failed to assign user {instance.email} to merchants group: {e}")


def send_merchant_welcome_email(merchant):
    """
    Send welcome email when merchant account is auto-created.
    
    This function sends a personalized welcome email to the user
    when their merchant account is automatically created after verification.
    
    Args:
        merchant: The newly created Merchant instance
    """
    try:
        user = merchant.user
        
        # Email context data
        context = {
            'user_name': user.get_full_name(),
            'user_first_name': user.first_name,
            'business_name': merchant.business_name,
            'merchant_id': str(merchant.id),
            'business_email': merchant.business_email,
            'business_phone': merchant.business_phone,
            'category': merchant.category.name if merchant.category else 'General Business',
            'status': merchant.get_status_display(),
            'created_at': merchant.created_at.strftime('%B %d, %Y at %I:%M %p'),
            'platform_name': 'PexiLabs',
            'support_email': getattr(settings, 'DEFAULT_FROM_EMAIL', 'support@pexilabs.com'),
            'dashboard_url': 'https://pexilabs.com/dashboard',  # Update with actual URL
            'docs_url': 'https://docs.pexilabs.com',  # Update with actual URL
        }
        
        # Render email templates
        html_message = render_to_string('emails/merchant_welcome.html', context)
        plain_message = render_to_string('emails/merchant_welcome.txt', context)
        
        # Send email
        send_mail(
            subject=f'Welcome to {context["platform_name"]} - Your Merchant Account is Ready!',
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        logger.info(f"📧 Welcome email sent to {user.email} for merchant account {merchant.id}")
        
    except Exception as e:
        logger.error(f"❌ Failed to send welcome email to {merchant.user.email}: {e}")
        # Don't raise the exception - we don't want email failures to break merchant creation
        

def send_merchant_account_created_notification(merchant):
    """
    Send notification email when merchant account is auto-created.
    
    This is a placeholder function that you can implement to send
    additional notifications like admin alerts, SMS, etc.
    
    Args:
        merchant: The newly created Merchant instance
    """
    # TODO: Implement additional notification logic
    # Examples:
    # - Send admin notification about new merchant signup
    # - Send SMS notification
    # - Create task in admin dashboard
    # - Post to Slack/Teams channel
    
    logger.info(f"📧 TODO: Send additional notifications for merchant account {merchant.id}")
