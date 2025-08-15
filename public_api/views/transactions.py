from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import datetime, timedelta
import json

from ..utils import api_key_required
from transactions.models import Transaction, TransactionStatus, TransactionType, PaymentMethod
from transactions.serializers import (
    TransactionListSerializer,
    TransactionDetailSerializer,
    TransactionStatsSerializer
)
from authentication.models import Merchant


@api_key_required
@require_http_methods(["GET"])
def list_transactions(request):
    """
    List transactions for the authenticated merchant.
    
    This endpoint returns a paginated list of transactions belonging to the
    authenticated merchant. Supports filtering by status, type, payment method,
    date range, and search by reference or customer email.
    
    Query Parameters:
        page (int): Page number for pagination (default: 1)
        page_size (int): Number of items per page (default: 20, max: 100)
        status (str): Filter by transaction status
        type (str): Filter by transaction type
        payment_method (str): Filter by payment method
        date_from (str): Filter transactions from date (YYYY-MM-DD)
        date_to (str): Filter transactions to date (YYYY-MM-DD)
        search (str): Search by reference or customer email
        amount_min (decimal): Filter by minimum amount
        amount_max (decimal): Filter by maximum amount
        currency (str): Filter by currency code
        gateway (str): Filter by gateway name
        is_settled (bool): Filter by settlement status
        is_flagged (bool): Filter by flagged status
    
    Returns:
        JsonResponse: Paginated list of transactions with metadata
        
    Example Response:
        {
            "success": true,
            "data": {
                "transactions": [...],
                "pagination": {
                    "page": 1,
                    "page_size": 20,
                    "total_pages": 5,
                    "total_count": 95,
                    "has_next": true,
                    "has_previous": false
                },
                "filters_applied": {...},
                "summary": {
                    "total_amount": "1250.00",
                    "total_fees": "36.25",
                    "net_amount": "1213.75"
                }
            }
        }
    """
    try:

        # Get authenticated merchant from the partner relationship
        partner = request.api_partner
        
        # Get merchant associated with this partner
        # Partner codes follow the pattern: merchant_{merchant_id}
        if not partner.code.startswith('merchant_'):
            return JsonResponse({
                'success': False,
                'error': 'Invalid partner',
                'message': 'This API key is not associated with a merchant account'
            }, status=403)
        
        try:
            merchant_id = partner.code.replace('merchant_', '')
            merchant_id = partner.code.replace('merchant_', '')
            merchant = Merchant.objects.get(id=merchant_id)
        except (ValueError, Merchant.DoesNotExist):
            return JsonResponse({
                'success': False,
                'error': 'Merchant not found',
                'message': 'No merchant account associated with this API key'
            }, status=404)
        
        # Start with base queryset for this merchant
        queryset = Transaction.objects.filter(merchant=merchant).select_related(
            'merchant', 'customer', 'currency', 'gateway', 'parent_transaction'
        ).prefetch_related('events', 'webhooks', 'child_transactions')
        
        # Apply filters
        filters_applied = {}
        
        # Status filter
        status = request.GET.get('status')
        try:
            status_choices = [choice[0] for choice in TransactionStatus.choices]
            if status and status in status_choices:
                queryset = queryset.filter(status=status)
                filters_applied['status'] = status
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': 'Configuration error',
                'message': f'Error accessing transaction status choices: {str(e)}'
            }, status=500)
        
        # Type filter
        transaction_type = request.GET.get('type')
        try:
            type_choices = [choice[0] for choice in TransactionType.choices]
            if transaction_type and transaction_type in type_choices:
                queryset = queryset.filter(transaction_type=transaction_type)
                filters_applied['type'] = transaction_type
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': 'Configuration error',
                'message': f'Error accessing transaction type choices: {str(e)}'
            }, status=500)
        
        # Payment method filter
        payment_method = request.GET.get('payment_method')
        try:
            payment_method_choices = [choice[0] for choice in PaymentMethod.choices]
            if payment_method and payment_method in payment_method_choices:
                queryset = queryset.filter(payment_method=payment_method)
                filters_applied['payment_method'] = payment_method
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': 'Configuration error',
                'message': f'Error accessing payment method choices: {str(e)}'
            }, status=500)
        
        # Date range filters
        date_from = request.GET.get('date_from')
        date_to = request.GET.get('date_to')
        
        if date_from:
            try:
                date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
                queryset = queryset.filter(created_at__date__gte=date_from_obj)
                filters_applied['date_from'] = date_from
            except ValueError:
                return JsonResponse({
                    'success': False,
                    'error': 'Invalid date format',
                    'message': 'date_from must be in YYYY-MM-DD format'
                }, status=400)
        
        if date_to:
            try:
                date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
                queryset = queryset.filter(created_at__date__lte=date_to_obj)
                filters_applied['date_to'] = date_to
            except ValueError:
                return JsonResponse({
                    'success': False,
                    'error': 'Invalid date format',
                    'message': 'date_to must be in YYYY-MM-DD format'
                }, status=400)
        
        try:
            # Amount range filters
            amount_min = request.GET.get('amount_min')
            amount_max = request.GET.get('amount_max')
            
            if amount_min:
                try:
                    amount_min_val = float(amount_min)
                    queryset = queryset.filter(amount__gte=amount_min_val)
                    filters_applied['amount_min'] = amount_min
                except ValueError:
                    return JsonResponse({
                        'success': False,
                        'error': 'Invalid amount format',
                        'message': 'amount_min must be a valid number'
                    }, status=400)
            
            if amount_max:
                try:
                    amount_max_val = float(amount_max)
                    queryset = queryset.filter(amount__lte=amount_max_val)
                    filters_applied['amount_max'] = amount_max
                except ValueError:
                    return JsonResponse({
                        'success': False,
                        'error': 'Invalid amount format',
                        'message': 'amount_max must be a valid number'
                    }, status=400)
            
            # Currency filter
            currency = request.GET.get('currency')
            if currency:
                queryset = queryset.filter(currency__code__iexact=currency)
                filters_applied['currency'] = currency
                
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': 'Filter error',
                'message': f'Error applying amount/currency filters: {str(e)}'
            }, status=500)
        
        # Gateway filter
        gateway = request.GET.get('gateway')
        if gateway:
            queryset = queryset.filter(gateway__name__icontains=gateway)
            filters_applied['gateway'] = gateway
        
        # Boolean filters
        is_settled = request.GET.get('is_settled')
        if is_settled is not None:
            is_settled_bool = is_settled.lower() in ['true', '1', 'yes']
            queryset = queryset.filter(is_settled=is_settled_bool)
            filters_applied['is_settled'] = is_settled_bool
        
        is_flagged = request.GET.get('is_flagged')
        if is_flagged is not None:
            is_flagged_bool = is_flagged.lower() in ['true', '1', 'yes']
            queryset = queryset.filter(is_flagged=is_flagged_bool)
            filters_applied['is_flagged'] = is_flagged_bool
        
        # Search filter
        search = request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(reference__icontains=search) |
                Q(external_reference__icontains=search) |
                Q(customer_email__icontains=search) |
                Q(customer__email__icontains=search) |
                Q(description__icontains=search)
            )
            filters_applied['search'] = search
        
        # Calculate summary for filtered results
        summary_queryset = queryset.filter(status__in=['completed', 'partially_refunded'])
        total_amount = sum(t.amount for t in summary_queryset)
        total_fees = sum(t.fee_amount for t in summary_queryset)
        net_amount = total_amount - total_fees
        
        # Pagination
        page = int(request.GET.get('page', 1))
        page_size = min(int(request.GET.get('page_size', 20)), 100)  # Max 100 items per page
        
        paginator = Paginator(queryset, page_size)
        
        if page > paginator.num_pages:
            return JsonResponse({
                'success': False,
                'error': 'Page not found',
                'message': f'Page {page} does not exist. Total pages: {paginator.num_pages}'
            }, status=404)
        
        page_obj = paginator.get_page(page)
        
        # Serialize transactions
        serializer = TransactionListSerializer(page_obj.object_list, many=True)
        
        return JsonResponse({
            'success': True,
            'data': {
                'transactions': serializer.data,
                'pagination': {
                    'page': page,
                    'page_size': page_size,
                    'total_pages': paginator.num_pages,
                    'total_count': paginator.count,
                    'has_next': page_obj.has_next(),
                    'has_previous': page_obj.has_previous()
                },
                'filters_applied': filters_applied,
                'summary': {
                    'total_amount': str(total_amount),
                    'total_fees': str(total_fees),
                    'net_amount': str(net_amount),
                    'currency': merchant.user.preferred_currency.code if merchant.user.preferred_currency else 'USD'
                }
            }
        }, status=200)
        
    except Exception as e:

        return JsonResponse({
            'success': False,
            'error': 'Internal server error',
            'message': 'An error occurred while fetching transactions'
        }, status=500)


@api_key_required
@require_http_methods(["GET"])
def get_transaction_by_id(request, transaction_id):
    """
    Get a specific transaction by its ID.
    
    This endpoint returns detailed information about a specific transaction
    belonging to the authenticated merchant, including events, webhooks,
    and child transactions (refunds).
    
    Path Parameters:
        transaction_id (uuid): The unique ID of the transaction
    
    Returns:
        JsonResponse: Detailed transaction information
        
    Example Response:
        {
            "success": true,
            "data": {
                "transaction": {
                    "id": "123e4567-e89b-12d3-a456-426614174000",
                    "reference": "TXN_20231201_001",
                    "status": "completed",
                    "amount": "100.00",
                    "currency_code": "USD",
                    "events": [...],
                    "webhooks": [...],
                    "child_transactions": [...]
                }
            }
        }
    """
    try:
        # Get authenticated merchant from the partner relationship
        partner = request.api_partner
        
        # Get merchant associated with this partner
        # Partner codes follow the pattern: merchant_{merchant_id}
        if not partner.code.startswith('merchant_'):
            return JsonResponse({
                'success': False,
                'error': 'Invalid partner',
                'message': 'This API key is not associated with a merchant account'
            }, status=403)
        
        try:
            merchant_id = partner.code.replace('merchant_', '')
            merchant = Merchant.objects.get(id=merchant_id)
        except (ValueError, Merchant.DoesNotExist):
            return JsonResponse({
                'success': False,
                'error': 'Merchant not found',
                'message': 'No merchant account associated with this API key'
            }, status=404)
        
        # Get transaction
        transaction = get_object_or_404(
            Transaction.objects.select_related(
                'merchant', 'customer', 'currency', 'gateway', 'parent_transaction'
            ).prefetch_related('events', 'webhooks', 'child_transactions'),
            id=transaction_id,
            merchant=merchant
        )
        
        # Serialize transaction
        serializer = TransactionDetailSerializer(transaction)
        
        return JsonResponse({
            'success': True,
            'data': {
                'transaction': serializer.data
            }
        }, status=200)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': 'Internal server error',
            'message': 'An error occurred while fetching the transaction'
        }, status=500)


@api_key_required
@require_http_methods(["GET"])
def get_transaction_by_reference(request, reference):
    """
    Get a specific transaction by its reference.
    
    This endpoint returns detailed information about a specific transaction
    belonging to the authenticated merchant using the transaction reference,
    including events, webhooks, and child transactions (refunds).
    
    Path Parameters:
        reference (str): The unique reference of the transaction
    
    Returns:
        JsonResponse: Detailed transaction information
        
    Example Response:
        {
            "success": true,
            "data": {
                "transaction": {
                    "id": "123e4567-e89b-12d3-a456-426614174000",
                    "reference": "TXN_20231201_001",
                    "status": "completed",
                    "amount": "100.00",
                    "currency_code": "USD",
                    "events": [...],
                    "webhooks": [...],
                    "child_transactions": [...]
                }
            }
        }
    """
    try:
        # Get authenticated merchant from the partner relationship
        partner = request.api_partner
        
        # Get merchant associated with this partner
        # Partner codes follow the pattern: merchant_{merchant_id}
        if not partner.code.startswith('merchant_'):
            return JsonResponse({
                'success': False,
                'error': 'Invalid partner',
                'message': 'This API key is not associated with a merchant account'
            }, status=403)
        
        try:
            merchant_id = partner.code.replace('merchant_', '')
            merchant = Merchant.objects.get(id=merchant_id)
        except (ValueError, Merchant.DoesNotExist):
            return JsonResponse({
                'success': False,
                'error': 'Merchant not found',
                'message': 'No merchant account associated with this API key'
            }, status=404)
        
        # Get transaction by reference
        transaction = get_object_or_404(
            Transaction.objects.select_related(
                'merchant', 'customer', 'currency', 'gateway', 'parent_transaction'
            ).prefetch_related('events', 'webhooks', 'child_transactions'),
            reference=reference,
            merchant=merchant
        )
        
        # Serialize transaction
        serializer = TransactionDetailSerializer(transaction)
        
        return JsonResponse({
            'success': True,
            'data': {
                'transaction': serializer.data
            }
        }, status=200)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': 'Internal server error',
            'message': 'An error occurred while fetching the transaction'
        }, status=500)


@api_key_required
@require_http_methods(["GET"])
def get_transaction_stats(request):
    """
    Get transaction statistics for the authenticated merchant.
    
    This endpoint returns comprehensive statistics about transactions
    for the authenticated merchant, including totals, success rates,
    and volume metrics.
    
    Query Parameters:
        date_from (str): Start date for statistics (YYYY-MM-DD)
        date_to (str): End date for statistics (YYYY-MM-DD)
        period (str): Predefined period (today, week, month, quarter, year)
    
    Returns:
        JsonResponse: Transaction statistics
        
    Example Response:
        {
            "success": true,
            "data": {
                "stats": {
                    "total_transactions": 150,
                    "completed_transactions": 142,
                    "failed_transactions": 8,
                    "success_rate": 94.67,
                    "total_volume": "15000.00",
                    "total_fees": "435.00",
                    "net_volume": "14565.00"
                },
                "period": {
                    "from": "2023-12-01",
                    "to": "2023-12-31"
                }
            }
        }
    """
    try:
        # Get authenticated merchant from the partner relationship
        partner = request.api_partner
        
        # Get merchant associated with this partner
        # Partner codes follow the pattern: merchant_{merchant_id}
        if not partner.code.startswith('merchant_'):
            return JsonResponse({
                'success': False,
                'error': 'Invalid partner',
                'message': 'This API key is not associated with a merchant account'
            }, status=403)
        
        try:
            merchant_id = partner.code.replace('merchant_', '')
            merchant = Merchant.objects.get(id=merchant_id)
        except (ValueError, Merchant.DoesNotExist):
            return JsonResponse({
                'success': False,
                'error': 'Merchant not found',
                'message': 'No merchant account associated with this API key'
            }, status=404)
        
        # Determine date range
        period = request.GET.get('period')
        date_from = request.GET.get('date_from')
        date_to = request.GET.get('date_to')
        
        # Handle predefined periods
        if period:
            now = timezone.now()
            if period == 'today':
                start_date = now.date()
                end_date = now.date()
            elif period == 'week':
                start_date = (now - timedelta(days=7)).date()
                end_date = now.date()
            elif period == 'month':
                start_date = (now - timedelta(days=30)).date()
                end_date = now.date()
            elif period == 'quarter':
                start_date = (now - timedelta(days=90)).date()
                end_date = now.date()
            elif period == 'year':
                start_date = (now - timedelta(days=365)).date()
                end_date = now.date()
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'Invalid period',
                    'message': 'Period must be one of: today, week, month, quarter, year'
                }, status=400)
        else:
            # Handle custom date range
            if date_from:
                try:
                    start_date = datetime.strptime(date_from, '%Y-%m-%d').date()
                except ValueError:
                    return JsonResponse({
                        'success': False,
                        'error': 'Invalid date format',
                        'message': 'date_from must be in YYYY-MM-DD format'
                    }, status=400)
            else:
                start_date = (timezone.now() - timedelta(days=30)).date()
            
            if date_to:
                try:
                    end_date = datetime.strptime(date_to, '%Y-%m-%d').date()
                except ValueError:
                    return JsonResponse({
                        'success': False,
                        'error': 'Invalid date format',
                        'message': 'date_to must be in YYYY-MM-DD format'
                    }, status=400)
            else:
                end_date = timezone.now().date()
        
        # Get statistics using the model method
        stats = Transaction.get_merchant_stats(merchant, start_date, end_date)
        
        # Serialize statistics
        serializer = TransactionStatsSerializer(stats)
        
        return JsonResponse({
            'success': True,
            'data': {
                'stats': serializer.data,
                'period': {
                    'from': start_date.strftime('%Y-%m-%d'),
                    'to': end_date.strftime('%Y-%m-%d')
                }
            }
        }, status=200)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': 'Internal server error',
            'message': 'An error occurred while fetching transaction statistics'
        }, status=500)


@api_key_required
@require_http_methods(["GET"])
def get_transaction_choices(request):
    """
    Get available choices for transaction fields.
    
    This endpoint returns the available choices for transaction status,
    type, and payment method fields. Useful for building forms and filters.
    
    Returns:
        JsonResponse: Available choices for transaction fields
        
    Example Response:
        {
            "success": true,
            "data": {
                "transaction_statuses": [
                    {"value": "pending", "display": "Pending"},
                    {"value": "completed", "display": "Completed"}
                ],
                "transaction_types": [
                    {"value": "payment", "display": "Payment"},
                    {"value": "refund", "display": "Refund"}
                ],
                "payment_methods": [
                    {"value": "card", "display": "Card Payment"},
                    {"value": "bank_transfer", "display": "Bank Transfer"}
                ]
            }
        }
    """
    try:
        return JsonResponse({
            'success': True,
            'data': {
                'transaction_statuses': [
                    {'value': choice[0], 'display': choice[1]}
                    for choice in TransactionStatus.choices
                ],
                'transaction_types': [
                    {'value': choice[0], 'display': choice[1]}
                    for choice in TransactionType.choices
                ],
                'payment_methods': [
                    {'value': choice[0], 'display': choice[1]}
                    for choice in PaymentMethod.choices
                ]
            }
        }, status=200)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': 'Internal server error',
            'message': 'An error occurred while fetching transaction choices'
        }, status=500)