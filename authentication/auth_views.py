from django.shortcuts import render, redirect
from django.contrib import messages
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods
from django.contrib.auth import login, logout
from django.http import JsonResponse
from django.urls import reverse
from .models import CustomUser, Merchant, MerchantCategory, Country, PreferredCurrency
from .utils import send_otp_email, send_merchant_creation_email
import json

@csrf_protect
@require_http_methods(["GET", "POST"])
def register_page(request):
    """Web-based registration page"""
    
    # Check if user is already logged in
    if request.user.is_authenticated:
        # Use the comprehensive dashboard redirect logic
        return redirect('dashboard:dashboard_redirect')
    
    if request.method == 'GET':
        # Get reference data for the form
        countries = Country.objects.all()
        currencies = PreferredCurrency.objects.all()
        merchant_categories = MerchantCategory.objects.all()
        
        context = {
            'page_title': 'Create Account - PexiLabs',
            'countries': countries,
            'currencies': currencies,
            'merchant_categories': merchant_categories,
        }
        return render(request, 'auth/register.html', context)
    
    elif request.method == 'POST':
        try:
            # Get form data
            first_name = request.POST.get('first_name', '').strip()
            last_name = request.POST.get('last_name', '').strip()
            email = request.POST.get('email', '').strip().lower()
            password = request.POST.get('password', '')
            confirm_password = request.POST.get('confirm_password', '')
            phone = request.POST.get('phone', '').strip()
            country_id = request.POST.get('country')
            currency_id = request.POST.get('currency')
            business_name = request.POST.get('business_name', '').strip()
            merchant_category_id = request.POST.get('merchant_category')
            
            # Basic validation
            errors = []
            
            if not first_name:
                errors.append("First name is required")
            if not last_name:
                errors.append("Last name is required")
            if not email:
                errors.append("Email is required")
            if not password:
                errors.append("Password is required")
            if len(password) < 8:
                errors.append("Password must be at least 8 characters long")
            if password != confirm_password:
                errors.append("Passwords do not match")
            
            # Check if email already exists
            if CustomUser.objects.filter(email=email).exists():
                errors.append("An account with this email already exists")
            
            if errors:
                for error in errors:
                    messages.error(request, error)
                return redirect('auth:register_page')
            
            # Create user
            user = CustomUser.objects.create_user(
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                phone_number=phone,
            )
            
            # Set country and currency if provided
            if country_id:
                try:
                    country = Country.objects.get(id=country_id)
                    user.country = country
                except Country.DoesNotExist:
                    pass
            
            if currency_id:
                try:
                    currency = PreferredCurrency.objects.get(id=currency_id)
                    user.preferred_currency = currency
                except PreferredCurrency.DoesNotExist:
                    pass
            
            user.save()
            
            # Create merchant account if business name provided
            merchant = None
            if business_name and merchant_category_id:
                try:
                    category = MerchantCategory.objects.get(id=merchant_category_id)
                    merchant = Merchant.objects.create(
                        user=user,
                        business_name=business_name,
                        category=category,
                        status='pending_verification'
                    )
                except MerchantCategory.DoesNotExist:
                    pass
            
            # Generate and send OTP email
            try:
                from .models import EmailOTP
                otp_instance = EmailOTP.generate_otp(user, purpose='registration', validity_minutes=15)
                
                # Try to send email in background, but don't block on it
                try:
                    from django.core.mail import send_mail
                    from django.conf import settings
                    
                    # Simple OTP email without template rendering to avoid hanging
                    send_mail(
                        subject='PexiLabs - Email Verification Code',
                        message=f'Your verification code is: {otp_instance.otp_code}\n\nThis code will expire in 15 minutes.',
                        from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@pexilabs.com'),
                        recipient_list=[user.email],
                        fail_silently=True,  # Don't fail if email doesn't work
                    )
                except Exception as email_error:
                    # Log the email error but continue
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f"Failed to send OTP email to {user.email}: {str(email_error)}")
                    # Continue anyway - user can still use the OTP
                    
            except Exception as otp_error:
                # Log the OTP creation error
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to create OTP for {user.email}: {str(otp_error)}")
                # This is more serious but still continue
                pass
            
            # Send merchant creation email if merchant was created
            if merchant:
                try:
                    # Simple merchant email without template rendering
                    from django.core.mail import send_mail
                    from django.conf import settings
                    
                    send_mail(
                        subject='PexiLabs - Merchant Account Created',
                        message=f'Congratulations! Your merchant account "{business_name}" has been created and is pending verification.',
                        from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@pexilabs.com'),
                        recipient_list=[user.email],
                        fail_silently=True,  # Don't fail if email doesn't work
                    )
                except Exception as e:
                    # Log the error for debugging
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Failed to send merchant creation email to {user.email}: {str(e)}")
                    pass
            
            # Don't log in the user yet - they need to verify their email first
            
            messages.success(request, 
                f"Account created successfully! Please check your email to verify your account."
                + (f" Your merchant account '{business_name}' has been created and is pending verification." if merchant else "")
            )
            
            # Redirect to OTP verification page
            return redirect('auth:verify_otp', user_id=user.id)
            
        except Exception as e:
            # Log the specific error for debugging
            import logging
            import traceback
            logger = logging.getLogger(__name__)
            logger.error(f"Registration error for email {email}: {str(e)}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            
            messages.error(request, "An error occurred during registration. Please try again.")
            return redirect('auth:register_page')

@csrf_protect 
@require_http_methods(["GET", "POST"])
def login_page(request):
    """Web-based login page"""
    
    # Check if user is already logged in
    if request.user.is_authenticated:
        # Use the comprehensive dashboard redirect logic
        return redirect('dashboard:dashboard_redirect')
    
    if request.method == 'GET':
        context = {
            'page_title': 'Sign In - PexiLabs',
        }
        return render(request, 'auth/login.html', context)
    
    elif request.method == 'POST':
        from django.contrib.auth import authenticate, login
        
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')
        remember_me = request.POST.get('remember_me')
        
        if not email or not password:
            messages.error(request, "Please provide both email and password")
            return redirect('auth:login_page')
        
        # Authenticate user
        user = authenticate(request, username=email, password=password)
        
        if user is not None:
            if user.is_active:
                # Check if user is verified
                if not user.is_verified:
                    messages.warning(request, "Please verify your email address before logging in.")
                    return redirect('auth:verify_otp', user_id=user.id)
                
                login(request, user)
                
                # Set session expiry based on remember me
                if not remember_me:
                    request.session.set_expiry(0)  # Browser session
                else:
                    request.session.set_expiry(1209600)  # 2 weeks
                
                messages.success(request, f"Welcome back, {user.first_name}!")
                
                # Redirect to next URL or dashboard based on user role
                next_url = request.POST.get('next') or request.GET.get('next')
                if next_url:
                    return redirect(next_url)
                else:
                    # Use the comprehensive dashboard redirect logic
                    return redirect('dashboard:dashboard_redirect')
            else:
                messages.error(request, "Your account is not active. Please contact support.")
        else:
            messages.error(request, "Invalid email or password")
        
        return redirect('auth:login_page')

@require_http_methods(["POST", "GET"])
def logout_page(request):
    """Web-based logout"""
    if request.method == 'POST' or request.method == 'GET':
        logout(request)
        messages.success(request, "You have been successfully logged out.")
        return redirect('auth:login_page')

@csrf_protect
@require_http_methods(["GET", "POST"])
def verify_otp(request, user_id):
    """OTP verification page after registration"""
    try:
        user = CustomUser.objects.get(id=user_id)
    except CustomUser.DoesNotExist:
        messages.error(request, "Invalid verification link.")
        return redirect('auth:register_page')
    
    # Check if user is already verified
    if user.is_verified:
        messages.info(request, "Your account is already verified. You can now log in.")
        return redirect('auth:login_page')
    
    if request.method == 'GET':
        context = {
            'page_title': 'Verify Your Account - PexiLabs',
            'user': user,
            'user_email': user.email,
            'user_name': user.get_full_name(),
        }
        return render(request, 'auth/verify_otp.html', context)
    
    elif request.method == 'POST':
        from .models import EmailOTP
        from django.utils import timezone
        from datetime import timedelta
        
        otp_code = request.POST.get('otp_code', '').strip()
        
        if not otp_code:
            messages.error(request, "Please enter the verification code.")
            return redirect('auth:verify_otp', user_id=user_id)
        
        try:
            # Get the latest OTP for this user
            email_otp = EmailOTP.objects.filter(
                user=user,
                is_used=False
            ).order_by('-created_at').first()
            
            if not email_otp:
                messages.error(request, "No verification code found. Please request a new one.")
                return redirect('auth:verify_otp', user_id=user_id)
            
            # Check if OTP has expired (15 minutes)
            expiry_time = email_otp.created_at + timedelta(minutes=15)
            if timezone.now() > expiry_time:
                messages.error(request, "Verification code has expired. Please request a new one.")
                return redirect('auth:verify_otp', user_id=user_id)
            
            # Verify OTP code
            if email_otp.otp_code == otp_code:
                # Mark OTP as used
                email_otp.is_used = True
                email_otp.save()
                
                # Verify user
                user.is_verified = True
                user.save()
                
                # Log in the user
                login(request, user)
                
                # Debug logging
                import logging
                logger = logging.getLogger(__name__)
                logger.info(f"OTP verification successful for user {user.email}, redirecting to dashboard")
                
                messages.success(request, "Your account has been verified successfully! Welcome to PexiLabs.")
                
                # Use the comprehensive dashboard redirect logic
                return redirect('dashboard:dashboard_redirect')
                
            else:
                messages.error(request, "Invalid verification code. Please try again.")
                return redirect('auth:verify_otp', user_id=user_id)
                
        except Exception as e:
            # Log the specific error for debugging
            import logging
            import traceback
            logger = logging.getLogger(__name__)
            logger.error(f"OTP verification error for user {user_id}: {str(e)}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            
            messages.error(request, "An error occurred during verification. Please try again.")
            return redirect('auth:verify_otp', user_id=user_id)


@csrf_protect
@require_http_methods(["POST"])
def resend_otp(request, user_id):
    """Resend OTP verification code"""
    try:
        user = CustomUser.objects.get(id=user_id)
    except CustomUser.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Invalid user.'})
    
    # Check if user is already verified
    if user.is_verified:
        return JsonResponse({'success': False, 'message': 'Account is already verified.'})
    
    try:
        # Generate and send new OTP
        from .models import EmailOTP
        otp_instance = EmailOTP.generate_otp(user, purpose='registration', validity_minutes=15)
        send_otp_email(user, otp_instance, purpose='registration')
        return JsonResponse({'success': True, 'message': 'A new verification code has been sent to your email.'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': 'Failed to send verification code. Please try again later.'})


@csrf_protect
@require_http_methods(["GET"])
def verification_help(request):
    """Help page for email verification"""
    context = {
        'page_title': 'Email Verification Help - PexiLabs',
    }
    return render(request, 'auth/verification_help.html', context)
