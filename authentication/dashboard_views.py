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


@login_required
def dashboard_redirect(request):
    """Redirect to appropriate dashboard based on user role and permissions"""
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
    
    # Default to user dashboard
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
