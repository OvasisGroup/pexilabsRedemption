from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Q, Sum
from django.utils import timezone
from datetime import timedelta
import json
from .models import CustomUser, Merchant, UserRole, MerchantStatus
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json

# Try to import optional models - check if apps are in settings first
INTEGRATIONS_AVAILABLE = False
TRANSACTIONS_AVAILABLE = False
API_KEYS_AVAILABLE = False

try:
    from django.conf import settings
    if 'integrations' in settings.INSTALLED_APPS:
        from integrations.models import Integration, MerchantIntegration, IntegrationAPICall
        INTEGRATIONS_AVAILABLE = True
except (ImportError, AttributeError):
    pass

try:
    from django.conf import settings
    if 'transactions' in settings.INSTALLED_APPS:
        from transactions.models import Transaction
        TRANSACTIONS_AVAILABLE = True
except (ImportError, AttributeError):
    pass

# Try to import API key models - check if they exist
try:
    from authentication.models import WhitelabelPartner, AppKey, AppKeyType, AppKeyStatus
    API_KEYS_AVAILABLE = True
except ImportError:
    API_KEYS_AVAILABLE = False

def get_or_create_merchant_partner(merchant):
    """Helper function to get or create a whitelabel partner for a merchant"""
    partner, created = WhitelabelPartner.objects.get_or_create(
        code=f"merchant_{merchant.id}",
        defaults={
            'name': merchant.business_name or f"Merchant {merchant.id}",
            'contact_email': merchant.business_email or merchant.user.email,
            'business_address': merchant.business_address or 'Not provided',
            'business_registration_number': merchant.business_registration_number or f"AUTO-{merchant.id}",
            'is_active': True,
            'is_verified': merchant.is_verified,
        }
    )
    return partner, created


def dashboard_redirect(request):
    """Redirect to appropriate dashboard based on user role and permissions"""
    # Check if user is authenticated first
    if not request.user.is_authenticated:
        return redirect('/auth/')  # Redirect to login page if not authenticated
    
    user = request.user
    
    # Check for superuser/admin first (highest priority)
    if user.is_superuser:
        return redirect('admin:index')  # Django admin for superusers
    
    # Check for staff users
    if user.is_staff:
        # Staff users can have different roles
        if user.role == UserRole.ADMIN:
            return redirect('dashboard:admin_dashboard')
        elif user.role == UserRole.MODERATOR:
            return redirect('dashboard:moderator_dashboard') 
        else:
            return redirect('dashboard:staff_dashboard')
    
    # Check for merchant account
    if hasattr(user, 'merchant_account') and user.merchant_account:
        return redirect('dashboard:merchant_dashboard')
    
    # Check specific user roles for non-staff users
    if user.role == UserRole.MODERATOR:
        return redirect('dashboard:moderator_dashboard')
    elif user.role == UserRole.ADMIN:
        return redirect('dashboard:admin_dashboard')
    
    # Default to user dashboard (user profile)
    return redirect('dashboard:user_dashboard')

@login_required
def admin_dashboard(request):
    """Admin dashboard with comprehensive system overview"""
    # Check for admin permissions (superuser or admin role)
    if not (request.user.is_superuser or 
            (request.user.is_staff and request.user.role == UserRole.ADMIN) or
            request.user.role == UserRole.ADMIN):
        messages.error(request, "Access denied. Admin privileges required.")
        return redirect('dashboard:dashboard_redirect')
    
    # Get current date ranges
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    
    # User statistics
    total_users = CustomUser.objects.count()
    new_users_week = CustomUser.objects.filter(created_at__date__gte=week_ago).count()
    new_users_month = CustomUser.objects.filter(created_at__date__gte=month_ago).count()
    active_users = CustomUser.objects.filter(is_active=True).count()
    verified_users = CustomUser.objects.filter(is_verified=True).count()
    
    # Merchant statistics
    total_merchants = Merchant.objects.count()
    pending_merchants = Merchant.objects.filter(status='pending_verification').count()
    approved_merchants = Merchant.objects.filter(status='approved').count()
    active_merchants = Merchant.objects.filter(status='approved').count()
    
    # Transaction statistics (if available)
    if TRANSACTIONS_AVAILABLE:
        total_transactions = Transaction.objects.count()
        completed_transactions = Transaction.objects.filter(status='completed').count()
        total_revenue = Transaction.objects.filter(
            status='completed'
        ).aggregate(Sum('amount'))['amount__sum'] or 0
    else:
        total_transactions = 0
        completed_transactions = 0
        total_revenue = 0
    
    # Integration statistics (if available)
    if INTEGRATIONS_AVAILABLE:
        active_integrations = Integration.objects.filter(status='active').count()
        total_integrations = Integration.objects.count()
    else:
        active_integrations = 3  # UBA, CyberSource, Corefy
        total_integrations = 3
    
    # Recent users
    recent_users = CustomUser.objects.order_by('-created_at')[:5]
    
    # Chart data for user growth (last 7 days)
    user_labels = []
    user_data = []
    
    for i in range(6, -1, -1):
        date = today - timedelta(days=i)
        user_labels.append(date.strftime('%b %d'))
        
        daily_users = CustomUser.objects.filter(
            created_at__date=date
        ).count()
        
        user_data.append(daily_users)
    
    context = {
        'page_title': 'Admin Dashboard - PexiLabs',
        'total_users': total_users,
        'verified_users': verified_users,
        'new_users_week': new_users_week,
        'total_merchants': total_merchants,
        'active_merchants': active_merchants,
        'pending_merchants': pending_merchants,
        'total_transactions': total_transactions,
        'completed_transactions': completed_transactions,
        'total_revenue': total_revenue,
        'active_integrations': active_integrations,
        'total_integrations': total_integrations,
        'recent_users': recent_users,
        'user_labels': json.dumps(user_labels),
        'user_data': json.dumps(user_data),
        'user_growth_percentage': round((new_users_week / max(total_users - new_users_week, 1)) * 100, 1),
    }
    
    return render(request, 'dashboard/admin_dashboard.html', context)

@login_required
def staff_dashboard(request):
    """Staff dashboard for managing merchants and integrations"""
    if not (request.user.is_staff or request.user.role in ['admin', 'staff']):
        messages.error(request, "Access denied. Staff privileges required.")
        return redirect('dashboard:dashboard_redirect')
    
    # Merchant management statistics
    pending_merchants = Merchant.objects.filter(status='pending').count()
    merchants_need_review = Merchant.objects.filter(
        Q(status='pending') | 
        Q(merchantdocument__status='pending')
    ).distinct().count()
    
    # Recent merchant applications
    recent_applications = Merchant.objects.filter(
        status='pending'
    ).order_by('-created_at')[:10]
    
    # Integration health
    if INTEGRATIONS_AVAILABLE:
        integrations_status = Integration.objects.values('name', 'is_enabled', 'status')
    else:
        integrations_status = [
            {'name': 'UBA', 'is_enabled': True, 'status': 'active'},
            {'name': 'CyberSource', 'is_enabled': True, 'status': 'active'},
            {'name': 'Corefy', 'is_enabled': True, 'status': 'active'},
        ]
    
    context = {
        'page_title': 'Staff Dashboard - PexiLabs',
        'pending_merchants': pending_merchants,
        'merchants_need_review': merchants_need_review,
        'recent_applications': recent_applications,
        'integrations_status': integrations_status,
    }
    
    return render(request, 'dashboard/staff_dashboard.html', context)

@login_required
def moderator_dashboard(request):
    """Moderator dashboard for content moderation and user management"""
    if not (request.user.is_staff or request.user.role in ['admin', 'staff', 'moderator']):
        messages.error(request, "Access denied. Moderator privileges required.")
        return redirect('dashboard:dashboard_redirect')
    
    # User moderation statistics
    unverified_users = CustomUser.objects.filter(is_verified=False).count()
    recent_registrations = CustomUser.objects.filter(
        created_at__date__gte=timezone.now().date() - timedelta(days=7)
    ).order_by('-created_at')[:10]
    
    context = {
        'page_title': 'Moderator Dashboard - PexiLabs',
        'unverified_users': unverified_users,
        'recent_registrations': recent_registrations,
    }
    
    return render(request, 'dashboard/moderator_dashboard.html', context)

@login_required
def merchant_dashboard(request):
    """Merchant dashboard for business account management"""
    if not hasattr(request.user, 'merchant_account'):
        messages.error(request, "No merchant account found. Please create one first.")
        return redirect('auth:user_dashboard')
    
    merchant = request.user.merchant_account
    
    # Transaction statistics (if transactions app is available)
    try:
        from transactions.models import Transaction
        total_transactions = Transaction.objects.filter(merchant=merchant).count()
        successful_transactions = Transaction.objects.filter(
            merchant=merchant, 
            status='completed'
        ).count()
        total_volume = Transaction.objects.filter(
            merchant=merchant,
            status='completed'
        ).aggregate(total=Sum('amount'))['total'] or 0
    except ImportError:
        total_transactions = 0
        successful_transactions = 0
        total_volume = 0
    
    # Integration status
    if INTEGRATIONS_AVAILABLE:
        merchant_integrations = MerchantIntegration.objects.filter(merchant=merchant)
        # Recent API calls - filter by merchant_integration's merchant
        recent_api_calls = IntegrationAPICall.objects.filter(
            merchant_integration__merchant=merchant
        ).order_by('-created_at')[:10]
    else:
        merchant_integrations = []
        recent_api_calls = []
    
    # Get available currencies for transaction forms
    from authentication.models import PreferredCurrency
    currencies = PreferredCurrency.objects.filter(is_active=True).order_by('code')
    
    # Document statistics
    from authentication.models import MerchantDocument, DocumentStatus
    documents = {
        'all': merchant.documents.all().order_by('-uploaded_at'),
        'approved': merchant.documents.filter(status=DocumentStatus.APPROVED),
        'pending': merchant.documents.filter(status=DocumentStatus.PENDING),
        'rejected': merchant.documents.filter(status=DocumentStatus.REJECTED),
    }
    
    # Checkout pages statistics (if checkout app is available)
    checkout_pages_count = 0
    try:
        from checkout.models import CheckoutPage
        checkout_pages_count = CheckoutPage.objects.filter(merchant=merchant).count()
    except ImportError:
        checkout_pages_count = 0
    
    # Check merchant information completeness
    is_info_complete = merchant.is_information_complete()
    missing_info = merchant.get_missing_information() if not is_info_complete else []
    
    # Create notification for incomplete information
    if not is_info_complete:
        from authentication.models import Notification
        Notification.create_info_completeness_reminder(merchant)
    
    # Get unread notifications for the user
    unread_notifications = request.user.notifications.filter(
        is_read=False,
        is_dismissed=False
    ).order_by('-created_at')[:10]
    
    # Get API keys for the merchant (for Test Integration section)
    api_keys = []
    if API_KEYS_AVAILABLE:
        try:
            partner, created = get_or_create_merchant_partner(merchant)
            api_keys = AppKey.objects.filter(
                partner=partner,
                status=AppKeyStatus.ACTIVE
            ).order_by('-created_at')
        except Exception:
            api_keys = []

    # Generate dynamic base URL from request
    scheme = 'https' if request.is_secure() else 'http'
    host = request.get_host()
    base_url = f"{scheme}://{host}"

    context = {
        'page_title': f'{merchant.business_name} - Merchant Dashboard',
        'merchant': merchant,
        'transaction_stats': {
            'total': total_transactions,
            'successful': successful_transactions,
            'success_rate': (successful_transactions / total_transactions * 100) if total_transactions > 0 else 0,
            'total_volume': total_volume,
        },
        'merchant_integrations': merchant_integrations,
        'recent_api_calls': recent_api_calls,
        'currencies': currencies,
        'documents': documents,
        'checkout_pages_count': checkout_pages_count,
        'is_info_complete': is_info_complete,
        'missing_info': missing_info,
        'notifications': unread_notifications,
        'api_keys': api_keys,
        'base_url': base_url,
    }
    
    return render(request, 'dashboard/merchant_dashboard.html', context)

@login_required
def user_dashboard(request):
    """Regular user dashboard"""
    user = request.user
    
    # Check if user can create merchant account
    can_create_merchant = not hasattr(user, 'merchant_account')
    
    # User activity
    recent_activity = []  # Can be expanded with user activity tracking
    
    context = {
        'page_title': f'Welcome {user.first_name} - User Dashboard',
        'can_create_merchant': can_create_merchant,
        'recent_activity': recent_activity,
    }
    
    return render(request, 'dashboard/user_dashboard.html', context)

@login_required
def merchant_verifier_dashboard(request):
    """Dashboard for staff to verify merchant applications"""
    # Check permissions - only staff/admin can access
    if not (request.user.is_staff or request.user.role in [UserRole.ADMIN, UserRole.STAFF]):
        messages.error(request, "Access denied. Staff privileges required.")
        return redirect('dashboard:dashboard_redirect')
    
    # Get filter parameters
    status_filter = request.GET.get('status', 'pending')
    search_query = request.GET.get('search', '')
    
    # Base queryset
    merchants = Merchant.objects.select_related('user', 'category', 'verified_by').all()
    
    # Apply status filter
    if status_filter != 'all':
        merchants = merchants.filter(status=status_filter)
    
    # Apply search filter
    if search_query:
        merchants = merchants.filter(
            Q(business_name__icontains=search_query) |
            Q(user__email__icontains=search_query) |
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(business_registration_number__icontains=search_query)
        )
    
    # Order by creation date (newest first for pending, oldest first for others)
    if status_filter == 'pending':
        merchants = merchants.order_by('created_at')  # Oldest pending first
    else:
        merchants = merchants.order_by('-updated_at')  # Most recently updated first
    
    # Pagination
    paginator = Paginator(merchants, 10)  # Show 10 merchants per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Statistics
    total_merchants = Merchant.objects.count()
    pending_count = Merchant.objects.filter(status='pending').count()
    approved_count = Merchant.objects.filter(status='approved').count()
    rejected_count = Merchant.objects.filter(status='rejected').count()
    
    # Recent activity (last 7 days)
    from datetime import timedelta
    week_ago = timezone.now() - timedelta(days=7)
    recent_approvals = Merchant.objects.filter(
        status='approved',
        verified_at__gte=week_ago
    ).count()
    recent_rejections = Merchant.objects.filter(
        status='rejected',
        updated_at__gte=week_ago
    ).count()
    
    context = {
        'page_title': 'Merchant Verifier Dashboard - PexiLabs',
        'merchants': page_obj,
        'status_filter': status_filter,
        'search_query': search_query,
        'stats': {
            'total': total_merchants,
            'pending': pending_count,
            'approved': approved_count,
            'rejected': rejected_count,
            'recent_approvals': recent_approvals,
            'recent_rejections': recent_rejections,
        },
        'status_choices': MerchantStatus.choices,
    }
    
    return render(request, 'dashboard/merchant_verifier.html', context)

@login_required
def merchant_verification_detail(request, merchant_id):
    """Detailed view for merchant verification"""
    # Check permissions
    if not (request.user.is_staff or request.user.role in [UserRole.ADMIN, UserRole.STAFF]):
        messages.error(request, "Access denied. Staff privileges required.")
        return redirect('dashboard:dashboard_redirect')
    
    try:
        merchant = Merchant.objects.select_related('user', 'category', 'verified_by').get(id=merchant_id)
    except Merchant.DoesNotExist:
        messages.error(request, "Merchant not found.")
        return redirect('dashboard:merchant_verifier_dashboard')
    
    # Get merchant documents if available
    documents = []
    try:
        from authentication.models import MerchantDocument
        documents = MerchantDocument.objects.filter(merchant=merchant).order_by('document_type')
    except:
        pass
    
    # Handle POST requests (approval/rejection)
    if request.method == 'POST':
        action = request.POST.get('action')
        notes = request.POST.get('verification_notes', '').strip()
        
        if action == 'approve':
            merchant.approve(verified_by=request.user)
            messages.success(request, f"Merchant '{merchant.business_name}' has been approved.")
            
            # Send approval email
            try:
                from .utils import send_merchant_status_update_email
                send_merchant_status_update_email(
                    merchant.user, 
                    merchant, 
                    'pending', 
                    'approved'
                )
            except Exception as e:
                messages.warning(request, "Merchant approved but email notification failed to send.")
            
        elif action == 'reject':
            if not notes:
                messages.error(request, "Rejection reason is required.")
                return redirect('dashboard:merchant_verification_detail', merchant_id=merchant_id)
            
            merchant.reject(notes=notes, verified_by=request.user)
            messages.success(request, f"Merchant '{merchant.business_name}' has been rejected.")
            
            # Send rejection email
            try:
                from .utils import send_merchant_status_update_email
                send_merchant_status_update_email(
                    merchant.user, 
                    merchant, 
                    'pending', 
                    'rejected'
                )
            except Exception as e:
                messages.warning(request, "Merchant rejected but email notification failed to send.")
        
        elif action == 'suspend':
            merchant.status = MerchantStatus.SUSPENDED
            merchant.verification_notes = notes
            merchant.verified_by = request.user
            merchant.save()
            messages.success(request, f"Merchant '{merchant.business_name}' has been suspended.")
            
        elif action == 'reactivate':
            merchant.status = MerchantStatus.APPROVED
            merchant.verification_notes = notes
            merchant.verified_by = request.user
            merchant.save()
            messages.success(request, f"Merchant '{merchant.business_name}' has been reactivated.")
        
        return redirect('dashboard:merchant_verifier_dashboard')
    
    context = {
        'page_title': f'Verify {merchant.business_name} - PexiLabs',
        'merchant': merchant,
        'documents': documents,
        'status_choices': MerchantStatus.choices,
    }
    
    return render(request, 'dashboard/merchant_verification_detail.html', context)

@login_required
def merchant_transactions_view(request):
    """Merchant transaction management view"""
    # Check if user has merchant account
    if not hasattr(request.user, 'merchant_account') or not request.user.merchant_account:
        messages.error(request, 'You need a merchant account to access this page.')
        return redirect('dashboard:user_dashboard')
    
    merchant = request.user.merchant_account
    
    if not TRANSACTIONS_AVAILABLE:
        messages.error(request, 'Transaction module is not available.')
        return redirect('dashboard:merchant_dashboard')
    
    # Import here to avoid import errors if transactions app is not available
    from transactions.models import Transaction, TransactionStatus, PaymentMethod
    from authentication.models import PreferredCurrency
    
    # Get filter parameters
    status_filter = request.GET.get('status')
    date_filter = request.GET.get('date')
    search_query = request.GET.get('q')
    
    # Base queryset - transactions for this merchant
    transactions_qs = Transaction.objects.filter(merchant=merchant).select_related(
        'customer', 'currency', 'gateway'
    ).order_by('-created_at')
    
    # Apply filters
    if status_filter:
        transactions_qs = transactions_qs.filter(status=status_filter)
    
    if date_filter:
        from datetime import datetime
        try:
            filter_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
            transactions_qs = transactions_qs.filter(created_at__date=filter_date)
        except ValueError:
            pass
    
    if search_query:
        transactions_qs = transactions_qs.filter(
            Q(reference__icontains=search_query) |
            Q(customer_email__icontains=search_query) |
            Q(external_reference__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(transactions_qs, 25)  # 25 transactions per page
    page_number = request.GET.get('page')
    transactions = paginator.get_page(page_number)
    
    # Calculate statistics
    today = timezone.now().date()
    
    # Today's stats
    today_transactions = Transaction.objects.filter(
        merchant=merchant,
        created_at__date=today
    )
    
    # All-time stats for this merchant
    all_transactions = Transaction.objects.filter(merchant=merchant)
    
    stats = {
        'today_count': today_transactions.count(),
        'today_volume': today_transactions.filter(
            status=TransactionStatus.COMPLETED
        ).aggregate(total=Sum('amount'))['total'] or 0,
        
        'total_count': all_transactions.count(),
        'total_volume': all_transactions.filter(
            status=TransactionStatus.COMPLETED
        ).aggregate(total=Sum('amount'))['total'] or 0,
        
        'pending_count': all_transactions.filter(
            status=TransactionStatus.PENDING
        ).count(),
        
        'completed_count': all_transactions.filter(
            status=TransactionStatus.COMPLETED
        ).count(),
    }
    
    # Calculate success rate
    if stats['total_count'] > 0:
        stats['success_rate'] = (stats['completed_count'] / stats['total_count']) * 100
    else:
        stats['success_rate'] = 0
    
    # Get available currencies
    currencies = PreferredCurrency.objects.filter(is_active=True).order_by('code')
    
    context = {
        'merchant': merchant,
        'transactions': transactions,
        'stats': stats,
        'currencies': currencies,
        'status_choices': TransactionStatus.choices,
        'payment_method_choices': PaymentMethod.choices,
        'current_filters': {
            'status': status_filter,
            'date': date_filter,
            'search': search_query,
        }
    }
    
    return render(request, 'dashboard/merchant_transactions.html', context)


@login_required
@require_http_methods(["POST"])
def create_transaction_api(request):
    """API endpoint to create a new transaction"""
    if not hasattr(request.user, 'merchant_account') or not request.user.merchant_account:
        return JsonResponse({'error': 'Merchant account required'}, status=403)
    
    if not TRANSACTIONS_AVAILABLE:
        return JsonResponse({'error': 'Transaction module not available'}, status=400)
    
    try:
        from transactions.models import Transaction, TransactionType, PaymentMethod, TransactionStatus
        from authentication.models import PreferredCurrency
        import uuid
        
        # Parse request data
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            data = request.POST
        
        # Validate required fields
        required_fields = ['transaction_type', 'payment_method', 'amount', 'currency', 'customer_email']
        for field in required_fields:
            if not data.get(field):
                return JsonResponse({'error': f'{field} is required'}, status=400)
        
        # Get currency object
        try:
            currency = PreferredCurrency.objects.get(id=data['currency'])
        except PreferredCurrency.DoesNotExist:
            return JsonResponse({'error': 'Invalid currency'}, status=400)
        
        # Generate unique reference
        reference = f"TXN_{uuid.uuid4().hex[:12].upper()}"
        
        # Create transaction
        transaction = Transaction.objects.create(
            merchant=request.user.merchant_account,
            reference=reference,
            transaction_type=data['transaction_type'],
            payment_method=data['payment_method'],
            amount=data['amount'],
            currency=currency,
            customer_email=data['customer_email'],
            customer_phone=data.get('customer_phone', ''),
            description=data.get('description', ''),
            external_reference=data.get('external_reference', ''),
            status=TransactionStatus.PENDING,
            net_amount=data['amount'],  # Will be calculated with fees later
        )
        
        return JsonResponse({
            'success': True,
            'transaction_id': str(transaction.id),
            'reference': transaction.reference,
            'message': 'Transaction created successfully'
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def create_payment_link_api(request):
    """API endpoint to create a payment link"""
    if not hasattr(request.user, 'merchant_account') or not request.user.merchant_account:
        return JsonResponse({'error': 'Merchant account required'}, status=403)
    
    if not TRANSACTIONS_AVAILABLE:
        return JsonResponse({'error': 'Transaction module not available'}, status=400)
    
    try:
        from transactions.models import PaymentLink
        from authentication.models import PreferredCurrency
        import uuid
        from datetime import datetime
        
        # Parse request data
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            data = request.POST
        
        # Validate required fields
        required_fields = ['amount', 'currency', 'description']
        for field in required_fields:
            if not data.get(field):
                return JsonResponse({'error': f'{field} is required'}, status=400)
        
        # Get currency object
        try:
            currency = PreferredCurrency.objects.get(id=data['currency'])
        except PreferredCurrency.DoesNotExist:
            return JsonResponse({'error': 'Invalid currency'}, status=400)
        
        # Parse expiry date if provided
        expires_at = None
        if data.get('expires_at'):
            try:
                expires_at = datetime.fromisoformat(data['expires_at'].replace('T', ' '))
            except ValueError:
                return JsonResponse({'error': 'Invalid expiry date format'}, status=400)
        
        # Generate unique slug
        slug = uuid.uuid4().hex
        
        # Create payment link
        payment_link = PaymentLink.objects.create(
            merchant=request.user.merchant_account,
            title=data['description'],
            description=data.get('long_description', data['description']),
            amount=data['amount'],
            currency=currency,
            slug=slug,
            expires_at=expires_at,
            is_active=True,
        )
        
        # Generate payment URL (you can customize this based on your URL structure)
        payment_url = f"{request.scheme}://{request.get_host()}/pay/{slug}/"
        
        return JsonResponse({
            'success': True,
            'payment_link_id': str(payment_link.id),
            'payment_url': payment_url,
            'slug': slug,
            'link_url': payment_url,
            'message': 'Payment link created successfully'
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def transaction_detail_api(request, transaction_id):
    """API endpoint to get transaction details"""
    if not hasattr(request.user, 'merchant_account') or not request.user.merchant_account:
        return JsonResponse({'error': 'Merchant account required'}, status=403)
    
    if not TRANSACTIONS_AVAILABLE:
        return JsonResponse({'error': 'Transaction module not available'}, status=400)
    
    try:
        from transactions.models import Transaction
        
        transaction = Transaction.objects.select_related(
            'customer', 'currency', 'gateway'
        ).get(
            id=transaction_id,
            merchant=request.user.merchant_account
        )
        
        return JsonResponse({
            'id': str(transaction.id),
            'reference': transaction.reference,
            'external_reference': transaction.external_reference,
            'status': transaction.status,
            'transaction_type': transaction.transaction_type,
            'payment_method': transaction.payment_method,
            'amount': str(transaction.amount),
            'fee_amount': str(transaction.fee_amount),
            'net_amount': str(transaction.net_amount),
            'currency': transaction.currency.code,
            'customer_email': transaction.customer_email,
            'customer_phone': transaction.customer_phone,
            'description': transaction.description,
            'created_at': transaction.created_at.isoformat(),
            'processed_at': transaction.processed_at.isoformat() if transaction.processed_at else None,
            'completed_at': transaction.completed_at.isoformat() if transaction.completed_at else None,
            'failure_reason': transaction.failure_reason,
        })
        
    except Transaction.DoesNotExist:
        return JsonResponse({'error': 'Transaction not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def refund_transaction_api(request, transaction_id):
    """API endpoint to initiate a refund"""
    if not hasattr(request.user, 'merchant_account') or not request.user.merchant_account:
        return JsonResponse({'error': 'Merchant account required'}, status=403)
    
    if not TRANSACTIONS_AVAILABLE:
        return JsonResponse({'error': 'Transaction module not available'}, status=400)
    
    try:
        from transactions.models import Transaction, TransactionType, TransactionStatus
        import uuid
        
        # Get the original transaction
        original_transaction = Transaction.objects.get(
            id=transaction_id,
            merchant=request.user.merchant_account,
            transaction_type=TransactionType.PAYMENT,
            status=TransactionStatus.COMPLETED
        )
        
        # Check if already refunded
        existing_refund = Transaction.objects.filter(
            parent_transaction=original_transaction,
            transaction_type=TransactionType.REFUND
        ).first()
        
        if existing_refund:
            return JsonResponse({'error': 'Transaction already refunded'}, status=400)
        
        # Create refund transaction
        refund_transaction = Transaction.objects.create(
            merchant=original_transaction.merchant,
            reference=f"REF_{uuid.uuid4().hex[:12].upper()}",
            transaction_type=TransactionType.REFUND,
            payment_method=original_transaction.payment_method,
            amount=original_transaction.amount,
            currency=original_transaction.currency,
            customer_email=original_transaction.customer_email,
            customer_phone=original_transaction.customer_phone,
            description=f"Refund for {original_transaction.reference}",
            status=TransactionStatus.PENDING,
            net_amount=original_transaction.amount,
            parent_transaction=original_transaction,
            gateway=original_transaction.gateway,
        )
        
        # Update original transaction status
        original_transaction.status = TransactionStatus.REFUNDED
        original_transaction.save()
        
        return JsonResponse({
            'success': True,
            'refund_id': str(refund_transaction.id),
            'refund_reference': refund_transaction.reference,
            'message': 'Refund initiated successfully'
        })
        
    except Transaction.DoesNotExist:
        return JsonResponse({'error': 'Transaction not found or cannot be refunded'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def upload_document_api(request):
    """API endpoint to upload a merchant document"""
    if not hasattr(request.user, 'merchant_account') or not request.user.merchant_account:
        return JsonResponse({'error': 'Merchant account required'}, status=403)
    
    try:
        from authentication.models import MerchantDocument, DocumentType, DocumentStatus
        import uuid
        from datetime import datetime
        
        # Validate required fields
        required_fields = ['document_type', 'title', 'document_file']
        for field in required_fields:
            if field not in request.FILES and field not in request.POST:
                return JsonResponse({'error': f'{field} is required'}, status=400)
        
        # Validate document type
        document_type = request.POST.get('document_type')
        if document_type not in dict(DocumentType.choices):
            return JsonResponse({'error': 'Invalid document type'}, status=400)
        
        # Get uploaded file
        document_file = request.FILES.get('document_file')
        if not document_file:
            return JsonResponse({'error': 'No file uploaded'}, status=400)
        
        # Validate file size (10MB limit)
        if document_file.size > 10 * 1024 * 1024:
            return JsonResponse({'error': 'File size too large. Maximum 10MB allowed.'}, status=400)
        
        # Validate file type
        allowed_extensions = ['.pdf', '.jpg', '.jpeg', '.png']
        file_extension = '.' + document_file.name.split('.')[-1].lower()
        if file_extension not in allowed_extensions:
            return JsonResponse({'error': 'Invalid file type. Only PDF, JPG, and PNG files are allowed.'}, status=400)
        
        # Parse expiry date if provided
        expiry_date = None
        if request.POST.get('expiry_date'):
            try:
                expiry_date = datetime.strptime(request.POST.get('expiry_date'), '%Y-%m-%d').date()
            except ValueError:
                return JsonResponse({'error': 'Invalid expiry date format'}, status=400)
        
        # Create document
        document = MerchantDocument.objects.create(
            merchant=request.user.merchant_account,
            document_type=document_type,
            document_file=document_file,
            original_filename=document_file.name,
            title=request.POST.get('title'),
            description=request.POST.get('description', ''),
            expiry_date=expiry_date,
            status=DocumentStatus.PENDING
        )
        
        return JsonResponse({
            'success': True,
            'document_id': str(document.id),
            'message': 'Document uploaded successfully'
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["DELETE"])
def delete_document_api(request, document_id):
    """API endpoint to delete a merchant document"""
    if not hasattr(request.user, 'merchant_account') or not request.user.merchant_account:
        return JsonResponse({'error': 'Merchant account required'}, status=403)
    
    try:
        from authentication.models import MerchantDocument
        
        document = MerchantDocument.objects.get(
            id=document_id,
            merchant=request.user.merchant_account
        )
        
        # Delete the file from storage
        if document.document_file:
            document.document_file.delete()
        
        # Delete the document record
        document.delete()
        
        return JsonResponse({
            'success': True,
            'message': 'Document deleted successfully'
        })
        
    except MerchantDocument.DoesNotExist:
        return JsonResponse({'error': 'Document not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def merchant_api_keys_view(request):
    """View for managing merchant API keys"""
    if not hasattr(request.user, 'merchant_account') or not request.user.merchant_account:
        messages.error(request, 'Merchant account required to access this page.')
        return redirect('dashboard:merchant_dashboard')
    
    if not API_KEYS_AVAILABLE:
        messages.error(request, 'API key functionality is not available.')
        return redirect('dashboard:merchant_dashboard')
    
    merchant = request.user.merchant_account
    
    # Get or create whitelabel partner for this merchant
    partner, created = get_or_create_merchant_partner(merchant)
    
    # Get API keys for this partner
    api_keys = AppKey.objects.filter(partner=partner).order_by('-created_at')
    
    context = {
        'merchant': merchant,
        'partner': partner,
        'api_keys': api_keys,
        'page_title': 'API Keys Management',
    }
    
    return render(request, 'dashboard/merchant_api_keys.html', context)


@login_required
@require_http_methods(["POST"])
@csrf_exempt
def create_api_key_api(request):
    """API endpoint to create a new API key for merchant"""
    if not hasattr(request.user, 'merchant_account') or not request.user.merchant_account:
        return JsonResponse({'error': 'Merchant account required'}, status=403)
    
    if not API_KEYS_AVAILABLE:
        return JsonResponse({'error': 'API key functionality is not available'}, status=503)
    
    try:
        import json
        data = json.loads(request.body)
        
        merchant = request.user.merchant_account
        
        # Get or create whitelabel partner for this merchant
        partner, created = get_or_create_merchant_partner(merchant)
        
        # Validate input data
        key_name = data.get('name', '').strip()
        if not key_name:
            return JsonResponse({'error': 'API key name is required'}, status=400)
        
        key_type = data.get('key_type', 'sandbox')
        if key_type not in ['production', 'sandbox', 'development']:
            key_type = 'sandbox'
        
        scopes = data.get('scopes', 'read,write')
        
        # Check if key name already exists for this partner
        if AppKey.objects.filter(partner=partner, name=key_name).exists():
            return JsonResponse({'error': 'API key with this name already exists'}, status=400)
        
        # Create the API key
        api_key = AppKey.objects.create(
            partner=partner,
            name=key_name,
            key_type=getattr(AppKeyType, key_type.upper()),
            scopes=scopes,
            status=AppKeyStatus.ACTIVE
        )
        
        # Get the raw secret (only available during creation)
        raw_secret = getattr(api_key, '_raw_secret', None)
        
        return JsonResponse({
            'success': True,
            'api_key': {
                'id': str(api_key.id),
                'name': api_key.name,
                'public_key': api_key.public_key,
                'secret_key': raw_secret,
                'key_type': api_key.key_type,
                'scopes': api_key.scopes,
                'status': api_key.status,
                'created_at': api_key.created_at.isoformat(),
            },
            'full_key': f"{api_key.public_key}:{raw_secret}" if raw_secret else None,
            'warning': 'The secret key will not be shown again. Please store it securely.'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'error': f'Unexpected error: {str(e)}'
        }, status=500)
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def list_api_keys_api(request):
    """API endpoint to list merchant's API keys"""
    if not hasattr(request.user, 'merchant_account') or not request.user.merchant_account:
        return JsonResponse({'error': 'Merchant account required'}, status=403)
    
    if not API_KEYS_AVAILABLE:
        return JsonResponse({'error': 'API key functionality is not available'}, status=503)
    
    try:
        merchant = request.user.merchant_account
        
        # Try to find the partner for this merchant
        try:
            partner = WhitelabelPartner.objects.get(code=f"merchant_{merchant.id}")
        except WhitelabelPartner.DoesNotExist:
            return JsonResponse({
                'success': True,
                'api_keys': [],
                'count': 0
            })
        
        # Get API keys for this partner
        api_keys = AppKey.objects.filter(partner=partner).order_by('-created_at')
        
        keys_data = []
        for key in api_keys:
            keys_data.append({
                'id': str(key.id),
                'name': key.name,
                'public_key': key.public_key,
                'key_type': key.key_type,
                'scopes': key.scopes,
                'status': key.status,
                'total_requests': key.total_requests,
                'last_used_at': key.last_used_at.isoformat() if key.last_used_at else None,
                'created_at': key.created_at.isoformat(),
                'expires_at': key.expires_at.isoformat() if key.expires_at else None,
                'is_active': key.is_active(),
                'masked_secret': key.masked_secret
            })
        
        return JsonResponse({
            'success': True,
            'api_keys': keys_data,
            'count': len(keys_data)
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["DELETE"])
def revoke_api_key_api(request, key_id):
    """API endpoint to revoke an API key"""
    if not hasattr(request.user, 'merchant_account') or not request.user.merchant_account:
        return JsonResponse({'error': 'Merchant account required'}, status=403)
    
    if not API_KEYS_AVAILABLE:
        return JsonResponse({'error': 'API key functionality is not available'}, status=503)
    
    try:
        merchant = request.user.merchant_account
        
        # Try to find the partner for this merchant
        try:
            partner = WhitelabelPartner.objects.get(code=f"merchant_{merchant.id}")
        except WhitelabelPartner.DoesNotExist:
            return JsonResponse({'error': 'Partner not found'}, status=404)
        
        # Get the API key
        try:
            api_key = AppKey.objects.get(id=key_id, partner=partner)
        except AppKey.DoesNotExist:
            return JsonResponse({'error': 'API key not found'}, status=404)
        
        # Revoke the key
        api_key.revoke(revoked_by=request.user, reason="Revoked by merchant")
        
        return JsonResponse({
            'success': True,
            'message': 'API key revoked successfully'
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required  
@require_http_methods(["POST"])
@csrf_exempt
def regenerate_api_key_api(request, key_id):
    """API endpoint to regenerate an API key secret"""
    if not hasattr(request.user, 'merchant_account') or not request.user.merchant_account:
        return JsonResponse({'error': 'Merchant account required'}, status=403)
    
    if not API_KEYS_AVAILABLE:
        return JsonResponse({'error': 'API key functionality is not available'}, status=503)
    
    try:
        merchant = request.user.merchant_account
        
        # Try to find the partner for this merchant
        try:
            partner = WhitelabelPartner.objects.get(code=f"merchant_{merchant.id}")
        except WhitelabelPartner.DoesNotExist:
            return JsonResponse({'error': 'Partner not found'}, status=404)
        
        # Get the API key
        try:
            api_key = AppKey.objects.get(id=key_id, partner=partner)
        except AppKey.DoesNotExist:
            return JsonResponse({'error': 'API key not found'}, status=404)
        
        # Generate new secret
        import secrets
        import hashlib
        
        raw_secret = secrets.token_urlsafe(32)
        api_key.secret_key = hashlib.sha256(raw_secret.encode()).hexdigest()
        api_key.save()
        
        return JsonResponse({
            'success': True,
            'public_key': api_key.public_key,
            'secret_key': raw_secret,
            'full_key': f"{api_key.public_key}:{raw_secret}",
            'message': 'API key secret regenerated successfully',
            'warning': 'The secret key will not be shown again. Please store it securely.'
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def merchant_profile_view(request):
    """View for merchant profile management"""
    if not hasattr(request.user, 'merchant_account') or not request.user.merchant_account:
        messages.error(request, 'Merchant account required to access this page.')
        return redirect('dashboard:merchant_dashboard')
    
    merchant = request.user.merchant_account
    
    context = {
        'merchant': merchant,
        'user': request.user,
        'page_title': 'Profile Settings',
    }
    
    return render(request, 'dashboard/merchant_profile.html', context)


@login_required
@require_http_methods(["POST"])
@csrf_exempt
def update_personal_info_api(request):
    """API endpoint to update personal information"""
    if not hasattr(request.user, 'merchant_account') or not request.user.merchant_account:
        return JsonResponse({'error': 'Merchant account required'}, status=403)
    
    try:
        user = request.user
        
        # Update user fields
        user.first_name = request.POST.get('first_name', '').strip()
        user.last_name = request.POST.get('last_name', '').strip()
        user.phone_number = request.POST.get('phone_number', '').strip()
        
        user.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Personal information updated successfully'
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
@csrf_exempt
def update_business_info_api(request):
    """API endpoint to update business information"""
    if not hasattr(request.user, 'merchant_account') or not request.user.merchant_account:
        return JsonResponse({'error': 'Merchant account required'}, status=403)
    
    try:
        merchant = request.user.merchant_account
        
        # Update merchant fields
        merchant.business_name = request.POST.get('business_name', '').strip()
        merchant.business_email = request.POST.get('business_email', '').strip()
        merchant.business_phone = request.POST.get('business_phone', '').strip()
        merchant.business_address = request.POST.get('business_address', '').strip()
        merchant.business_registration_number = request.POST.get('business_registration_number', '').strip()
        
        merchant.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Business information updated successfully'
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
@csrf_exempt
def change_password_api(request):
    """API endpoint to change user password"""
    if not hasattr(request.user, 'merchant_account') or not request.user.merchant_account:
        return JsonResponse({'error': 'Merchant account required'}, status=403)
    
    try:
        from django.contrib.auth import authenticate
        
        user = request.user
        current_password = request.POST.get('current_password', '')
        new_password = request.POST.get('new_password', '')
        
        # Verify current password
        if not authenticate(username=user.email, password=current_password):
            return JsonResponse({'error': 'Current password is incorrect'}, status=400)
        
        # Validate new password
        if len(new_password) < 8:
            return JsonResponse({'error': 'New password must be at least 8 characters long'}, status=400)
        
        # Change password
        user.set_password(new_password)
        user.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Password changed successfully'
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def merchant_documents_view(request):
    """Dedicated page for merchant document management"""
    if not hasattr(request.user, 'merchant_account'):
        messages.error(request, "No merchant account found. Please create one first.")
        return redirect('auth:user_dashboard')
    
    merchant = request.user.merchant_account
    
    # Document statistics
    from authentication.models import MerchantDocument, DocumentStatus
    documents = {
        'all': merchant.documents.all().order_by('-uploaded_at'),
        'approved': merchant.documents.filter(status=DocumentStatus.APPROVED),
        'pending': merchant.documents.filter(status=DocumentStatus.PENDING),
        'rejected': merchant.documents.filter(status=DocumentStatus.REJECTED),
    }
    
    context = {
        'page_title': f'{merchant.business_name} - Documents',
        'merchant': merchant,
        'documents': documents,
    }
    
    return render(request, 'dashboard/merchant_documents.html', context)


def merchant_bank_details_view(request):
    """Dedicated page for merchant bank details management"""
    if not hasattr(request.user, 'merchant_account'):
        messages.error(request, "No merchant account found. Please create one first.")
        return redirect('auth:user_dashboard')
    
    merchant = request.user.merchant_account
    
    context = {
        'page_title': f'{merchant.business_name} - Bank Details',
        'merchant': merchant,
    }
    
    return render(request, 'dashboard/merchant_bank_details.html', context)


@csrf_exempt
def update_bank_details_api(request):
    """API endpoint to update merchant bank details"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    if not hasattr(request.user, 'merchant_account'):
        return JsonResponse({'error': 'Merchant account required'}, status=403)
    
    merchant = request.user.merchant_account
    
    try:
        # Get form data
        bank_account_name = request.POST.get('bank_account_name', '').strip()
        bank_name = request.POST.get('bank_name', '').strip()
        bank_account_number = request.POST.get('bank_account_number', '').strip()
        bank_routing_number = request.POST.get('bank_routing_number', '').strip()
        
        # Validation
        if not bank_account_name:
            return JsonResponse({'error': 'Account holder name is required'}, status=400)
        
        if not bank_name:
            return JsonResponse({'error': 'Bank name is required'}, status=400)
        
        if not bank_account_number:
            return JsonResponse({'error': 'Account number is required'}, status=400)
        
        # Validate account number format (basic check)
        if not bank_account_number.isdigit():
            return JsonResponse({'error': 'Account number must contain only numbers'}, status=400)
        
        if len(bank_account_number) < 4:
            return JsonResponse({'error': 'Account number must be at least 4 digits'}, status=400)
        
        # Validate routing number if provided
        if bank_routing_number and not bank_routing_number.isdigit():
            return JsonResponse({'error': 'Routing number must contain only numbers'}, status=400)
        
        # Update merchant bank details
        merchant.bank_account_name = bank_account_name
        merchant.bank_name = bank_name
        merchant.bank_account_number = bank_account_number
        merchant.bank_routing_number = bank_routing_number
        merchant.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Bank details updated successfully'
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def get_notifications_api(request):
    """API endpoint to get user notifications"""
    notifications = request.user.notifications.filter(
        is_dismissed=False
    ).order_by('-created_at')[:20]
    
    notification_data = []
    for notif in notifications:
        notification_data.append({
            'id': str(notif.id),
            'title': notif.title,
            'message': notif.message,
            'type': notif.type,
            'priority': notif.priority,
            'is_read': notif.is_read,
            'action_url': notif.action_url,
            'action_text': notif.action_text,
            'created_at': notif.created_at.isoformat(),
        })
    
    return JsonResponse({
        'notifications': notification_data,
        'unread_count': request.user.notifications.filter(is_read=False, is_dismissed=False).count()
    })

@login_required
@require_http_methods(["POST"])
def mark_notification_read_api(request, notification_id):
    """API endpoint to mark a notification as read"""
    try:
        notification = request.user.notifications.get(id=notification_id)
        notification.mark_as_read()
        return JsonResponse({'success': True})
    except:
        return JsonResponse({'success': False, 'error': 'Notification not found'}, status=404)

@login_required
@require_http_methods(["POST"])
def dismiss_notification_api(request, notification_id):
    """API endpoint to dismiss a notification"""
    try:
        notification = request.user.notifications.get(id=notification_id)
        notification.dismiss()
        return JsonResponse({'success': True})
    except:
        return JsonResponse({'success': False, 'error': 'Notification not found'}, status=404)

@login_required
@require_http_methods(["POST"])
def mark_all_notifications_read_api(request):
    """API endpoint to mark all notifications as read"""
    count = request.user.notifications.filter(is_read=False).update(
        is_read=True,
        read_at=timezone.now()
    )
    return JsonResponse({'success': True, 'marked_count': count})


@login_required
@require_http_methods(["POST"])
@csrf_exempt
def create_test_checkout_api(request):
    """API endpoint to create a test checkout page for integration testing"""
    if not hasattr(request.user, 'merchant_account') or not request.user.merchant_account:
        return JsonResponse({'error': 'Merchant account required'}, status=403)
    
    try:
        data = json.loads(request.body)
        integration_type = data.get('integration_type', 'uba_bank')
        amount = data.get('amount', 100.00)
        currency = data.get('currency', 'USD')
        
        merchant = request.user.merchant_account
        
        # Import checkout models
        try:
            from checkout.models import CheckoutPage, PaymentMethodConfig
            from authentication.models import PreferredCurrency
            
            # Get or create currency
            currency_obj, created = PreferredCurrency.objects.get_or_create(
                code=currency,
                defaults={'name': currency, 'symbol': '$', 'is_active': True}
            )
            
            # Generate unique slug
            import time
            slug_base = f'test-{integration_type}-{int(time.time())}'
            
            # Create test checkout page
            checkout_page = CheckoutPage.objects.create(
                merchant=merchant,
                name=f'Test Checkout - {integration_type.upper()}',
                slug=slug_base,
                title=f'Test Payment - {merchant.business_name}',
                description='This is a test payment page for integration testing. No real charges will be made.',
                currency=currency_obj,
                min_amount=amount,
                max_amount=amount,
                primary_color='#3B82F6',
                secondary_color='#1E40AF',
                background_color='#F8FAFC',
                success_url=request.build_absolute_uri('/test-success'),
                cancel_url=request.build_absolute_uri('/test-cancel'),
                require_customer_info=True,
                is_active=True
            )
            
            # Add payment method configuration for UBA
            if integration_type in ['uba_bank', 'bank']:
                PaymentMethodConfig.objects.create(
                    checkout_page=checkout_page,
                    payment_method='bank_transfer',
                    display_name='UBA Bank Payment',
                    is_enabled=True,
                    display_order=1,
                    gateway_config={'integration_type': integration_type}
                )
            
            checkout_url = request.build_absolute_uri(checkout_page.get_absolute_url())
            
            return JsonResponse({
                'success': True,
                'message': f'Test checkout page created successfully for {integration_type}',
                'data': {
                    'checkout_page_id': str(checkout_page.id),
                    'checkout_url': checkout_url,
                    'slug': checkout_page.slug,
                    'amount': str(amount),
                    'currency': currency,
                    'test_mode': True
                }
            })
            
        except ImportError:
            return JsonResponse({
                'success': False,
                'error': 'Checkout functionality not available'
            }, status=500)
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Failed to create test checkout: {str(e)}'
        }, status=500)


@login_required
@require_http_methods(["POST"])
@csrf_exempt
def test_integration_api(request):
    """API endpoint to test merchant integrations"""
    if not hasattr(request.user, 'merchant_account') or not request.user.merchant_account:
        return JsonResponse({'error': 'Merchant account required'}, status=403)
    
    try:
        data = json.loads(request.body)
        integration_type = data.get('integration_type')
        test_type = data.get('test_type', 'checkout')
        
        if not integration_type:
            return JsonResponse({'error': 'Integration type is required'}, status=400)
        
        merchant = request.user.merchant_account
        
        # Import integration services
        if INTEGRATIONS_AVAILABLE:
            from integrations.services import UBABankService, CyberSourceService, CorefyService
            from integrations.models import MerchantIntegration
            
            # Get merchant integration
            try:
                # Handle both 'uba_bank' and 'bank' integration types for UBA
                if integration_type in ['uba_bank', 'bank']:
                    merchant_integration = MerchantIntegration.objects.get(
                        merchant=merchant,
                        integration__integration_type__in=['uba_bank', 'bank'],
                        is_enabled=True
                    )
                else:
                    merchant_integration = MerchantIntegration.objects.get(
                        merchant=merchant,
                        integration__integration_type=integration_type,
                        is_enabled=True
                    )
            except MerchantIntegration.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'error': f'No active {integration_type} integration found'
                }, status=404)
            
            # Test based on integration type
            if integration_type in ['uba_bank', 'bank']:
                service = UBABankService(merchant=merchant)
                
                if test_type == 'checkout':
                    # Test checkout intent creation
                    test_payload = {
                        'amount': 100.00,
                        'currency': 'USD',
                        'customer_email': 'test@example.com',
                        'description': 'Integration Test Payment',
                        'callback_url': request.build_absolute_uri('/test-callback'),
                        'cancel_url': request.build_absolute_uri('/test-cancel')
                    }
                    
                    try:
                        result = service.create_payment_page(
                            amount=test_payload['amount'],
                            currency=test_payload['currency'],
                            customer_email=test_payload['customer_email'],
                            description=test_payload['description'],
                            callback_url=test_payload['callback_url']
                        )
                        
                        # Handle PayDock API response structure
                        if result.get('resource') and result['resource'].get('data'):
                            # PayDock API successful response
                            checkout_data = result['resource']['data']
                            
                            # Create Transaction record if transactions app is available
                            transaction_id = None
                            if TRANSACTIONS_AVAILABLE:
                                try:
                                    from transactions.models import (
                                        Transaction, TransactionType, PaymentMethod, 
                                        TransactionStatus, PaymentGateway
                                    )
                                    from authentication.models import PreferredCurrency
                                    import uuid
                                    
                                    # Get or create UBA payment gateway
                                    gateway, _ = PaymentGateway.objects.get_or_create(
                                        code='uba_kenya',
                                        defaults={
                                            'name': 'UBA Kenya Pay',
                                            'api_endpoint': 'https://api-sandbox.paydock.com/v1',
                                            'is_sandbox': True,
                                            'supported_currencies': 'USD,KES,EUR,GBP',
                                            'supported_payment_methods': 'bank_transfer,card'
                                        }
                                    )
                                    
                                    # Get currency (default to USD if not found)
                                    try:
                                        currency = PreferredCurrency.objects.get(code='USD')
                                    except PreferredCurrency.DoesNotExist:
                                        # Create USD currency if it doesn't exist
                                        currency = PreferredCurrency.objects.create(
                                            code='USD',
                                            name='US Dollar',
                                            symbol='$'
                                        )
                                    
                                    # Create transaction record
                                    transaction = Transaction.objects.create(
                                        merchant=merchant,
                                        reference=checkout_data.get('reference', f'UBA-TEST-{uuid.uuid4().hex[:8].upper()}'),
                                        external_reference=checkout_data.get('_id'),
                                        transaction_type=TransactionType.PAYMENT,
                                        payment_method=PaymentMethod.BANK_TRANSFER,
                                        gateway=gateway,
                                        currency=currency,
                                        amount=checkout_data.get('amount', 100.00),
                                        net_amount=checkout_data.get('amount', 100.00),
                                        customer_email=test_payload['customer_email'],
                                        description=test_payload['description'],
                                        status=TransactionStatus.PENDING,
                                        metadata={
                                            'test_payment': True,
                                            'integration_type': 'uba_bank',
                                            'paydock_checkout_id': checkout_data.get('_id'),
                                            'paydock_token': checkout_data.get('token')
                                        }
                                    )
                                    transaction_id = str(transaction.id)
                                    
                                except Exception as e:
                                    # Log error but don't fail the response
                                    print(f"Error creating transaction record: {str(e)}")
                            
                            return JsonResponse({
                                'status': 'success',
                                'message': 'UBA checkout test completed successfully',
                                'data': {
                                    'token': checkout_data.get('token'),
                                    'checkout_id': checkout_data.get('_id'),
                                    'payment_url': f"https://checkout-sandbox.paydock.com/pay/{checkout_data.get('_id')}",
                                    'reference': checkout_data.get('reference'),
                                    'amount': checkout_data.get('amount'),
                                    'currency': checkout_data.get('currency'),
                                    'status': checkout_data.get('status', 'active'),
                                    'transaction_id': transaction_id
                                }
                            })
                        elif result.get('success'):
                            # Mock response structure - also create transaction record
                            transaction_id = None
                            if TRANSACTIONS_AVAILABLE:
                                try:
                                    from transactions.models import (
                                        Transaction, TransactionType, PaymentMethod, 
                                        TransactionStatus, PaymentGateway
                                    )
                                    from authentication.models import PreferredCurrency
                                    import uuid
                                    
                                    # Get or create UBA payment gateway
                                    gateway, _ = PaymentGateway.objects.get_or_create(
                                        code='uba_kenya',
                                        defaults={
                                            'name': 'UBA Kenya Pay',
                                            'api_endpoint': 'https://api-sandbox.paydock.com/v1',
                                            'is_sandbox': True,
                                            'supported_currencies': 'USD,KES,EUR,GBP',
                                            'supported_payment_methods': 'bank_transfer,card'
                                        }
                                    )
                                    
                                    # Get currency (default to USD if not found)
                                    try:
                                        currency = PreferredCurrency.objects.get(code='USD')
                                    except PreferredCurrency.DoesNotExist:
                                        currency = PreferredCurrency.objects.create(
                                            code='USD',
                                            name='US Dollar',
                                            symbol='$'
                                        )
                                    
                                    # Create transaction record for mock payment
                                    transaction = Transaction.objects.create(
                                        merchant=merchant,
                                        reference=result.get('reference', f'UBA-MOCK-{uuid.uuid4().hex[:8].upper()}'),
                                        external_reference=f"mock_{uuid.uuid4().hex[:12]}",
                                        transaction_type=TransactionType.PAYMENT,
                                        payment_method=PaymentMethod.BANK_TRANSFER,
                                        gateway=gateway,
                                        currency=currency,
                                        amount=test_payload['amount'],
                                        net_amount=test_payload['amount'],
                                        customer_email=test_payload['customer_email'],
                                        description=test_payload['description'],
                                        status=TransactionStatus.COMPLETED,  # Mock payments are immediately completed
                                        metadata={
                                            'test_payment': True,
                                            'mock_payment': True,
                                            'integration_type': 'uba_bank'
                                        }
                                    )
                                    transaction.mark_as_completed()
                                    transaction_id = str(transaction.id)
                                    
                                except Exception as e:
                                    print(f"Error creating mock transaction record: {str(e)}")
                            
                            return JsonResponse({
                                'status': 'success',
                                'message': 'UBA checkout test completed successfully (mock)',
                                'data': {
                                    'payment_url': result.get('payment_url'),
                                    'reference': result.get('reference'),
                                    'status': 'test_passed',
                                    'transaction_id': transaction_id
                                }
                            })
                        else:
                            return JsonResponse({
                                'status': 'error',
                                'message': result.get('error', 'UBA checkout test failed'),
                                'error': result.get('error', 'UBA checkout test failed'),
                                'details': result
                            })
                    
                    except Exception as e:
                        return JsonResponse({
                            'success': False,
                            'error': f'UBA service error: {str(e)}'
                        })
                
                elif test_type == 'connection':
                    # Test connection
                    try:
                        if hasattr(service, 'test_connection'):
                            result = service.test_connection()
                            return JsonResponse({
                                'success': result.get('success', False),
                                'message': result.get('message', 'Connection test completed'),
                                'data': result
                            })
                        else:
                            return JsonResponse({
                                'success': True,
                                'message': 'UBA service is configured and ready'
                            })
                    except Exception as e:
                        return JsonResponse({
                            'success': False,
                            'error': f'Connection test failed: {str(e)}'
                        })
            
            elif integration_type == 'cybersource':
                service = CyberSourceService(merchant=merchant)
                # Add CyberSource testing logic here
                return JsonResponse({
                    'success': True,
                    'message': 'CyberSource test completed (placeholder)',
                    'data': {'status': 'test_passed'}
                })
            
            elif integration_type == 'corefy':
                service = CorefyService(merchant=merchant)
                # Add Corefy testing logic here
                return JsonResponse({
                    'success': True,
                    'message': 'Corefy test completed (placeholder)',
                    'data': {'status': 'test_passed'}
                })
            
            else:
                return JsonResponse({
                    'success': False,
                    'error': f'Testing not implemented for {integration_type}'
                })
        
        else:
            return JsonResponse({
                'success': False,
                'error': 'Integration module not available'
            })
    
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Unexpected error: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def create_payment_intent_api(request):
    """Public API endpoint to create payment intent for checkout processing"""
    try:
        data = json.loads(request.body)
        integration_type = data.get('integration_type', 'uba_bank')
        test_type = data.get('test_type', 'checkout')
        
        # Validate session_id if provided (for authenticated checkout sessions)
        session_id = data.get('session_id')
        if session_id:
            # Validate that the session_id exists and contains the payment data
            # This ensures the request comes from a valid make-payment API call
            required_session_fields = ['amount', 'currency', 'customer_email', 'description']
            missing_fields = [field for field in required_session_fields if field not in data]
            if missing_fields:
                return JsonResponse({
                    'status': 'error',
                    'message': f'Missing required session fields: {", ".join(missing_fields)}'
                }, status=400)
        
        # For public checkout, we'll use session data or default test merchant configuration
        
        # Import integration services
        if INTEGRATIONS_AVAILABLE:
            from integrations.services import UBABankService
            
            # Create a test service instance without merchant (for demo purposes)
            service = UBABankService()
            
            if test_type == 'checkout':
                # Test checkout intent creation
                test_payload = {
                    'amount': data.get('amount', 100.00),
                    'currency': data.get('currency', 'USD'),
                    'customer_email': data.get('customer_email', 'test@example.com'),
                    'description': data.get('description', 'Test Payment'),
                    'callback_url': data.get('callback_url', ''),
                    'cancel_url': data.get('cancel_url', '')
                }
                
                try:
                    print(f"DEBUG: Creating payment page with payload: {test_payload}")
                    result = service.create_payment_page(
                        amount=test_payload['amount'],
                        currency=test_payload['currency'],
                        customer_email=test_payload['customer_email'],
                        description=test_payload['description'],
                        callback_url=test_payload['callback_url'],
                        redirect_url=test_payload['cancel_url']
                    )
                    print(f"DEBUG: Service result: {result}")
                    
                    if result and (result.get('success') or result.get('status') == 201):
                        # Handle different response structures
                        if 'checkout_data' in result:
                            # Mock response with checkout_data
                            checkout_data = result['checkout_data']
                            token = checkout_data.get('token')
                            checkout_id = checkout_data.get('_id')
                        elif 'resource' in result and result['resource'].get('type') == 'checkout':
                            # Actual PayDock API response
                            checkout_data = result['resource']['data']
                            token = checkout_data.get('token')
                            checkout_id = checkout_data.get('_id')
                        elif result.get('success'):
                            # Mock response structure
                            token = result.get('payment_url', '')  # Use payment_url as token for mock
                            checkout_id = result.get('reference', '')
                            checkout_data = {
                                '_id': checkout_id,
                                'token': token
                            }
                        else:
                            # Fallback
                            token = ''
                            checkout_id = ''
                            checkout_data = {}
                        
                        # Create transaction record if available
                        transaction_id = None
                        print(f"DEBUG: TRANSACTIONS_AVAILABLE = {TRANSACTIONS_AVAILABLE}")
                        if TRANSACTIONS_AVAILABLE:
                            print(f"DEBUG: Importing transaction models...")
                            from transactions.models import Transaction, TransactionType, TransactionStatus, PaymentMethod, PaymentGateway
                            from authentication.models import PreferredCurrency
                            print(f"DEBUG: Transaction models imported successfully")
                            
                            # Get or create PaymentGateway for UBA Kenya Pay
                            print(f"DEBUG: Getting or creating PaymentGateway...")
                            try:
                                gateway = PaymentGateway.objects.get(name='UBA Kenya Pay')
                                print(f"DEBUG: Found existing PaymentGateway: {gateway}")
                            except PaymentGateway.DoesNotExist:
                                print(f"DEBUG: PaymentGateway not found, creating new one...")
                                gateway, created = PaymentGateway.objects.get_or_create(
                                    code='uba_kenya_pay',
                                    defaults={
                                        'name': 'UBA Kenya Pay',
                                        'description': 'UBA Kenya Payment Gateway',
                                        'api_endpoint': 'https://api.paydock.com',
                                        'supported_payment_methods': 'bank_transfer',
                                        'supported_currencies': 'USD,KES,EUR',
                                        'is_sandbox': True
                                    }
                                )
                                print(f"DEBUG: PaymentGateway created: {gateway}, created={created}")
                            
                            # Get currency object
                            print(f"DEBUG: Getting or creating currency for: {test_payload['currency']}")
                            currency_obj, created = PreferredCurrency.objects.get_or_create(
                                code=test_payload['currency'],
                                defaults={'name': test_payload['currency']}
                            )
                            print(f"DEBUG: Currency object: {currency_obj}, created={created}")
                            
                            # Get merchant from session_id if provided
                            print(f"DEBUG: Getting merchant from session_id: {session_id}")
                            from authentication.models import Merchant, WhitelabelPartner
                            
                            merchant = None
                            if session_id:
                                print(f"DEBUG: Session ID provided, creating public merchant...")
                                # For sessions created via make-payment API, we need to extract merchant_id
                                # from the session data. Since session data is passed via URL parameters,
                                # we need to look for a way to get the merchant_id.
                                # For now, we'll try to get it from the request or create a default merchant
                                
                                # Try to get merchant_id from the session data
                                # This would typically be stored when the session was created
                                # For the URL-based session, we can try to extract it from the referrer or other means
                                
                                # For now, let's create a default merchant for public transactions
                                # In a real implementation, you'd want to store session data in a database
                                # or cache to properly track the merchant_id
                                
                                # Create or get a default public merchant
                                # Set is_verified=False initially to avoid triggering email signals
                                print(f"DEBUG: Creating or getting public user...")
                                try:
                                    system_user, created = CustomUser.objects.get_or_create(
                                        email='public@pexilabs.com',
                                        defaults={
                                            'first_name': 'Public',
                                            'last_name': 'Checkout',
                                            'is_verified': False,  # Set to False initially
                                            'role': 'user'
                                        }
                                    )
                                    print(f"DEBUG: Public user: {system_user}, created={created}")
                                    # Update verification status without triggering signals if user was just created
                                    if created:
                                        CustomUser.objects.filter(id=system_user.id).update(is_verified=True)
                                        print(f"DEBUG: Updated user verification status")
                                except Exception as user_error:
                                    print(f"ERROR: Failed to create public user: {user_error}")
                                    import traceback
                                    print(f"ERROR: User creation traceback: {traceback.format_exc()}")
                                    raise user_error
                                
                                print(f"DEBUG: Creating or getting public merchant...")
                                try:
                                    # Use user field for get_or_create since it's a OneToOneField
                                    merchant, created = Merchant.objects.get_or_create(
                                        user=system_user,
                                        defaults={
                                            'business_name': 'Public Checkout System',
                                            'business_email': 'public@pexilabs.com',
                                            'business_phone': '+1234567890',
                                            'business_address': 'Public Checkout Address'
                                        }
                                    )
                                    print(f"DEBUG: Public merchant: {merchant}, created={created}")
                                except Exception as merchant_error:
                                    print(f"ERROR: Failed to create public merchant: {merchant_error}")
                                    import traceback
                                    print(f"ERROR: Merchant creation traceback: {traceback.format_exc()}")
                                    raise merchant_error
                            else:
                                # No session_id provided, create a default system merchant
                                # Set is_verified=False initially to avoid triggering email signals
                                system_user, created = CustomUser.objects.get_or_create(
                                    email='system@pexilabs.com',
                                    defaults={
                                        'first_name': 'System',
                                        'last_name': 'User',
                                        'is_verified': False,  # Set to False initially
                                        'role': 'user'
                                    }
                                )
                                # Update verification status without triggering signals if user was just created
                                if created:
                                    CustomUser.objects.filter(id=system_user.id).update(is_verified=True)
                                
                                # Use user field for get_or_create since it's a OneToOneField
                                merchant, created = Merchant.objects.get_or_create(
                                    user=system_user,
                                    defaults={
                                        'business_name': 'System Public Checkout',
                                        'business_email': 'system@pexilabs.com',
                                        'business_phone': '+1234567890',
                                        'business_address': 'System Address for Public Transactions'
                                    }
                                )
                            
                            try:
                                print(f"DEBUG: Creating transaction with:")
                                ref_value = result.get('reference', f'PUBLIC-{timezone.now().strftime("%Y%m%d%H%M%S")}')
                                print(f"  - reference: {ref_value}") 
                                print(f"  - external_reference: {checkout_id}")
                                print(f"  - merchant: {merchant} (ID: {merchant.id})")
                                print(f"  - gateway: {gateway} (ID: {gateway.id})")
                                print(f"  - currency: {currency_obj} (ID: {currency_obj.id})")
                                print(f"  - amount: {test_payload['amount']}")
                                
                                from decimal import Decimal
                                transaction = Transaction.objects.create(
                                    reference=result.get('reference', f"PUBLIC-{timezone.now().strftime('%Y%m%d%H%M%S')}"),
                                    external_reference=checkout_id,
                                    merchant=merchant,
                                    transaction_type=TransactionType.PAYMENT,
                                    payment_method=PaymentMethod.BANK_TRANSFER,
                                    gateway=gateway,
                                    currency=currency_obj,
                                    amount=Decimal(str(test_payload['amount'])),  # Convert to Decimal
                                    customer_email=test_payload['customer_email'],
                                    description=test_payload['description'],
                                    status=TransactionStatus.PENDING,
                                    metadata={
                                        'paydock_checkout_id': checkout_id,
                                        'paydock_token': token,
                                        'public_checkout': True,
                                        'mock_response': 'checkout_data' not in result
                                    }
                                )
                                transaction_id = str(transaction.id)
                                print(f"DEBUG: Transaction created successfully with ID: {transaction_id}")
                            except Exception as transaction_error:
                                print(f"ERROR: Failed to create transaction: {transaction_error}")
                                print(f"ERROR: Transaction error type: {type(transaction_error)}")
                                import traceback
                                print(f"ERROR: Full traceback: {traceback.format_exc()}")
                                raise transaction_error
                        
                        return JsonResponse({
                            'status': 'success',
                            'message': 'Payment intent created successfully',
                            'data': {
                                'token': token,
                                'checkout_id': checkout_id,
                                'payment_url': result.get('payment_url', ''),
                                'transaction_id': transaction_id
                            }
                        })
                    else:
                        return JsonResponse({
                            'status': 'error',
                            'error': f'Failed to create payment intent: {result}'
                        }, status=400)
                        
                except Exception as e:
                    return JsonResponse({
                        'status': 'error',
                        'error': f'Payment service error: {str(e)}'
                    }, status=500)
            else:
                return JsonResponse({
                    'status': 'error',
                    'error': 'Only checkout test type is supported for public API'
                }, status=400)
        else:
            return JsonResponse({
                'status': 'error',
                'error': 'Integration module not available'
            }, status=503)
            
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'error': f'Unexpected error: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def uba_payment_webhook(request):
    """Handle UBA/PayDock payment webhooks to update transaction status"""
    try:
        # Parse webhook payload
        payload = json.loads(request.body)
        
        # Extract payment information
        event_type = payload.get('type')
        checkout_data = payload.get('data', {})
        checkout_id = checkout_data.get('_id')
        status = checkout_data.get('status')
        
        if not checkout_id:
            return JsonResponse({'error': 'Missing checkout ID'}, status=400)
        
        # Update transaction if transactions app is available
        if TRANSACTIONS_AVAILABLE:
            try:
                from transactions.models import Transaction, TransactionStatus
                
                # Find transaction by external reference (PayDock checkout ID)
                transaction = Transaction.objects.get(external_reference=checkout_id)
                
                # Update transaction status based on webhook event
                if event_type == 'transaction_success' or status == 'complete':
                    transaction.status = TransactionStatus.COMPLETED
                    transaction.mark_as_completed()
                elif event_type == 'transaction_failure' or status == 'failed':
                    transaction.status = TransactionStatus.FAILED
                    transaction.mark_as_failed(
                        reason=checkout_data.get('failure_reason', 'Payment failed'),
                        code=checkout_data.get('failure_code', 'PAYMENT_FAILED')
                    )
                elif status == 'cancelled':
                    transaction.status = TransactionStatus.CANCELLED
                    transaction.save()
                
                # Update metadata with webhook information
                transaction.metadata.update({
                    'webhook_received': True,
                    'webhook_event_type': event_type,
                    'webhook_status': status,
                    'webhook_timestamp': timezone.now().isoformat()
                })
                transaction.save()
                
                return JsonResponse({
                    'success': True,
                    'message': f'Transaction {transaction.reference} updated successfully',
                    'transaction_id': str(transaction.id),
                    'new_status': transaction.status
                })
                
            except Transaction.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'message': f'Transaction with checkout ID {checkout_id} not found'
                }, status=404)
            except Exception as e:
                return JsonResponse({
                    'success': False,
                    'error': f'Error updating transaction: {str(e)}'
                }, status=500)
        else:
            return JsonResponse({
                'success': True,
                'message': 'Webhook received but transactions app not available'
            })
            
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON payload'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def integration_health_check_api(request):
    """API endpoint to check integration health status"""
    if not hasattr(request.user, 'merchant_account') or not request.user.merchant_account:
        return JsonResponse({'error': 'Merchant account required'}, status=403)
    
    merchant = request.user.merchant_account
    
    try:
        if INTEGRATIONS_AVAILABLE:
            from integrations.models import MerchantIntegration
            
            # Get merchant integrations
            integrations = MerchantIntegration.objects.filter(
                merchant=merchant,
                is_enabled=True
            ).select_related('integration')
            
            health_status = []
            for integration in integrations:
                # Calculate success rate
                total_requests = integration.total_requests or 0
                successful_requests = integration.successful_requests or 0
                success_rate = (successful_requests / total_requests * 100) if total_requests > 0 else 0
                
                health_status.append({
                    'id': str(integration.id),
                    'name': integration.integration.name,
                    'provider': integration.integration.provider_name,
                    'type': integration.integration.integration_type,
                    'is_healthy': success_rate >= 95,  # Consider healthy if 95%+ success rate
                    'success_rate': round(success_rate, 2),
                    'total_requests': total_requests,
                    'successful_requests': successful_requests,
                    'last_used': integration.last_used_at.isoformat() if integration.last_used_at else None,
                    'status': integration.status
                })
            
            return JsonResponse({
                'success': True,
                'data': health_status,
                'summary': {
                    'total_integrations': len(health_status),
                    'healthy_integrations': sum(1 for h in health_status if h['is_healthy']),
                    'average_success_rate': sum(h['success_rate'] for h in health_status) / len(health_status) if health_status else 0
                }
            })
        
        else:
            return JsonResponse({
                'success': False,
                'error': 'Integration module not available'
            })
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Health check failed: {str(e)}'
        }, status=500)
