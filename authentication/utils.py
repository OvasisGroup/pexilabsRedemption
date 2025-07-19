from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def send_otp_email(user, otp_instance, purpose='registration'):
    """Send OTP verification email to user"""
    try:
        context = {
            'user': user,
            'otp_code': otp_instance.otp_code,
            'purpose': purpose,
            'validity_minutes': 10,  # Default validity
            'current_year': datetime.now().year,
        }
        
        # Render email templates
        html_message = render_to_string('emails/verification_otp.html', context)
        plain_message = render_to_string('emails/verification_otp.txt', context)
        
        # Email subject based on purpose
        subject_map = {
            'registration': 'Welcome to PexiLabs - Verify Your Email',
            'password_reset': 'PexiLabs - Password Reset Verification',
            'email_change': 'PexiLabs - Email Change Verification',
        }
        subject = subject_map.get(purpose, 'PexiLabs - Email Verification')
        
        # Send email
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@pexilabs.com'),
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        logger.info(f"OTP email sent successfully to {user.email} for {purpose}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send OTP email to {user.email}: {str(e)}")
        return False


def send_merchant_creation_email(user, merchant):
    """Send merchant account creation confirmation email"""
    try:
        context = {
            'user': user,
            'merchant': merchant,
            'current_year': datetime.now().year,
        }
        
        # Render email templates
        html_message = render_to_string('emails/merchant_created.html', context)
        
        # Create plain text version
        plain_message = f"""
PexiLabs - Merchant Account Created Successfully

Hello {user.first_name},

Congratulations! Your merchant account has been successfully created with PexiLabs.

Account Details:
- Business Name: {merchant.business_name}
- Merchant ID: {merchant.id}
- Status: {merchant.get_status_display()}
- Created: {merchant.created_at.strftime('%B %d, %Y')}

What's Next?
- Complete your business verification documents
- Set up your payment methods and banking information
- Configure your merchant settings and preferences
- Start accepting payments once approved

Our team will review your merchant application within 2-3 business days. You will receive an email notification once your account status is updated.

If you have any questions or need assistance, please don't hesitate to contact our merchant support team.

Thank you for choosing PexiLabs!

---
This email was sent from PexiLabs. Please do not reply to this email.
© {datetime.now().year} PexiLabs. All rights reserved.
        """
        
        # Send email
        send_mail(
            subject='PexiLabs - Merchant Account Created Successfully',
            message=plain_message.strip(),
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@pexilabs.com'),
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        logger.info(f"Merchant creation email sent successfully to {user.email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send merchant creation email to {user.email}: {str(e)}")
        return False


def send_merchant_status_update_email(user, merchant, old_status, new_status):
    """Send email when merchant status is updated"""
    try:
        status_messages = {
            'approved': 'Your merchant account has been approved! You can now start accepting payments.',
            'rejected': 'Unfortunately, your merchant account application was not approved. Please contact support for more information.',
            'suspended': 'Your merchant account has been temporarily suspended. Please contact support immediately.',
            'active': 'Your merchant account is now active and ready for transactions.',
        }
        
        subject = f"PexiLabs - Merchant Account Status Update: {new_status.title()}"
        message = f"""
Hello {user.first_name},

Your merchant account status has been updated.

Business Name: {merchant.business_name}
Previous Status: {old_status.title()}
New Status: {new_status.title()}

{status_messages.get(new_status, 'Your merchant account status has been updated.')}

{merchant.verification_notes if merchant.verification_notes else ''}

If you have any questions, please contact our support team.

Best regards,
PexiLabs Team
        """
        
        send_mail(
            subject=subject,
            message=message.strip(),
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@pexilabs.com'),
            recipient_list=[user.email],
            fail_silently=False,
        )
        
        logger.info(f"Merchant status update email sent to {user.email}: {old_status} -> {new_status}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send merchant status email to {user.email}: {str(e)}")
        return False
