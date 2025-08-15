from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.conf import settings


@require_http_methods(["GET"])
def api_documentation(request):
    """
    Render comprehensive API documentation for the PexiLabs Public API.
    
    This view provides detailed documentation for all available API endpoints
    including authentication, checkout, and transaction management endpoints.
    The documentation includes request/response examples, parameter descriptions,
    and interactive testing capabilities.
    
    Returns:
        Rendered HTML template with complete API documentation
    """
    
    # API endpoint information
    api_endpoints = {
        'authentication': {
            'title': 'Authentication',
            'description': 'API key verification and authentication endpoints',
            'endpoints': [
                {
                    'method': 'POST',
                    'path': '/api/v1/auth/verify/',
                    'name': 'Verify API Key',
                    'description': 'Verify API key authentication and get partner information',
                    'authentication': 'Required - API Key',
                    'parameters': [],
                    'response_example': {
                        'authenticated': True,
                        'message': 'Authentication successful',
                        'data': {
                            'partner': {
                                'id': 'uuid',
                                'name': 'Partner Name',
                                'code': 'partner_code',
                                'is_active': True
                            },
                            'app_key': {
                                'id': 'uuid',
                                'name': 'API Key Name',
                                'key_type': 'merchant',
                                'scopes': ['read', 'write'],
                                'status': 'active'
                            }
                        }
                    }
                }
            ]
        },
        'checkout': {
            'title': 'Checkout & Payments',
            'description': 'Payment processing and checkout session management',
            'endpoints': [
                {
                    'method': 'POST',
                    'path': '/api/v1/checkout/make-payment/',
                    'name': 'Create Payment Session',
                    'description': 'Create a new payment session for processing payments',
                    'authentication': 'Required - API Key with write scope',
                    'parameters': [
                        {'name': 'amount', 'type': 'decimal', 'required': True, 'description': 'Payment amount (positive number)'},
                        {'name': 'currency', 'type': 'string', 'required': True, 'description': 'Currency code (USD, EUR, KES, etc.)'},
                        {'name': 'customer_email', 'type': 'string', 'required': True, 'description': 'Customer email address'},
                        {'name': 'customer_name', 'type': 'string', 'required': True, 'description': 'Customer full name'},
                        {'name': 'customer_phone', 'type': 'string', 'required': True, 'description': 'Customer phone number'},
                        {'name': 'payment_method', 'type': 'string', 'required': True, 'description': 'Payment Method (card, crypto)'},
                        {'name': 'description', 'type': 'string', 'required': False, 'description': 'Payment description'},
                        {'name': 'callback_url', 'type': 'string', 'required': False, 'description': 'Success callback URL'},
                        {'name': 'cancel_url', 'type': 'string', 'required': False, 'description': 'Cancel/failure callback URL'},
                        {'name': 'metadata', 'type': 'object', 'required': False, 'description': 'Additional metadata'}
                    ],
                    'response_example': {
                        'success': True,
                        'message': 'Payment session created successfully',
                        'data': {
                            'session_id': 'uuid',
                            'payment_url': 'https:/app.pexilabs.com/pay/...',
                            'reference': 'TXN-REF-123',
                            'amount': '100.00',
                            'currency': 'USD',
                            'expires_at': '2024-01-01T12:00:00Z'
                        }
                    }
                },
                # {
                #     'method': 'GET',
                #     'path': '/api/v1/checkout/process-payment/',
                #     'name': 'Process Payment',
                #     'description': 'Process payment with session parameters (renders payment interface)',
                #     'authentication': 'Not required (public endpoint)',
                #     'parameters': [
                #         {'name': 'session_id', 'type': 'string', 'required': True, 'description': 'Payment session ID'},
                #         {'name': 'amount', 'type': 'string', 'required': True, 'description': 'Payment amount'},
                #         {'name': 'currency', 'type': 'string', 'required': True, 'description': 'Currency code'},
                #         {'name': 'payment_method', 'type': 'string', 'required': False, 'description': 'Payment method (card, crypto)'}
                #     ],
                #     'response_example': 'Renders payment interface HTML'
                # }
            ]
        },
        'transactions': {
            'title': 'Transaction Management',
            'description': 'Transaction listing, details, and statistics',
            'endpoints': [
                {
                    'method': 'GET',
                    'path': '/api/v1/transactions/',
                    'name': 'List Transactions',
                    'description': 'Get paginated list of transactions with filtering options',
                    'authentication': 'Required - API Key',
                    'parameters': [
                        {'name': 'page', 'type': 'integer', 'required': False, 'description': 'Page number (default: 1)'},
                        {'name': 'page_size', 'type': 'integer', 'required': False, 'description': 'Items per page (default: 20, max: 100)'},
                        {'name': 'status', 'type': 'string', 'required': False, 'description': 'Filter by transaction status'},
                        {'name': 'type', 'type': 'string', 'required': False, 'description': 'Filter by transaction type'},
                        {'name': 'payment_method', 'type': 'string', 'required': False, 'description': 'Filter by payment method'},
                        {'name': 'date_from', 'type': 'string', 'required': False, 'description': 'Start date (YYYY-MM-DD)'},
                        {'name': 'date_to', 'type': 'string', 'required': False, 'description': 'End date (YYYY-MM-DD)'},
                        {'name': 'search', 'type': 'string', 'required': False, 'description': 'Search by reference or email'},
                        {'name': 'amount_min', 'type': 'decimal', 'required': False, 'description': 'Minimum amount filter'},
                        {'name': 'amount_max', 'type': 'decimal', 'required': False, 'description': 'Maximum amount filter'},
                        {'name': 'currency', 'type': 'string', 'required': False, 'description': 'Filter by currency'}
                    ],
                    'response_example': {
                        'success': True,
                        'data': {
                            'transactions': [],
                            'pagination': {
                                'current_page': 1,
                                'total_pages': 5,
                                'total_count': 100,
                                'page_size': 20,
                                'has_next': True,
                                'has_previous': False
                            }
                        }
                    }
                },
                {
                    'method': 'GET',
                    'path': '/api/v1/transactions/stats/',
                    'name': 'Transaction Statistics',
                    'description': 'Get comprehensive transaction statistics and metrics',
                    'authentication': 'Required - API Key',
                    'parameters': [
                        {'name': 'date_from', 'type': 'string', 'required': False, 'description': 'Start date (YYYY-MM-DD)'},
                        {'name': 'date_to', 'type': 'string', 'required': False, 'description': 'End date (YYYY-MM-DD)'},
                        {'name': 'period', 'type': 'string', 'required': False, 'description': 'Predefined period (today, week, month, quarter, year)'}
                    ],
                    'response_example': {
                        'success': True,
                        'data': {
                            'stats': {
                                'total_transactions': 150,
                                'completed_transactions': 142,
                                'failed_transactions': 8,
                                'success_rate': 94.67,
                                'total_volume': '15000.00',
                                'total_fees': '435.00',
                                'net_volume': '14565.00'
                            },
                            'period': {
                                'from': '2023-12-01',
                                'to': '2023-12-31'
                            }
                        }
                    }
                },
                {
                    'method': 'GET',
                    'path': '/api/v1/transactions/choices/',
                    'name': 'Transaction Choices',
                    'description': 'Get available choices for transaction filters',
                    'authentication': 'Required - API Key',
                    'parameters': [],
                    'response_example': {
                        'success': True,
                        'data': {
                            'transaction_statuses': [
                                {'value': 'pending', 'display': 'Pending'},
                                {'value': 'completed', 'display': 'Completed'}
                            ],
                            'transaction_types': [
                                {'value': 'payment', 'display': 'Payment'},
                                {'value': 'refund', 'display': 'Refund'}
                            ],
                            'payment_methods': [
                                {'value': 'card', 'display': 'Card Payment'},
                                {'value': 'crypto', 'display': 'Cryptocurrency'}
                            ]
                        }
                    }
                },
                {
                    'method': 'GET',
                    'path': '/api/v1/transactions/<uuid:transaction_id>/',
                    'name': 'Get Transaction by ID',
                    'description': 'Get detailed information about a specific transaction by ID',
                    'authentication': 'Required - API Key',
                    'parameters': [
                        {'name': 'transaction_id', 'type': 'uuid', 'required': True, 'description': 'Transaction UUID'}
                    ],
                    'response_example': {
                        'success': True,
                        'data': {
                            'transaction': {
                                'id': 'uuid',
                                'reference': 'TXN-REF-123',
                                'amount': '100.00',
                                'currency': 'USD',
                                'status': 'completed',
                                'created_at': '2024-01-01T12:00:00Z'
                            }
                        }
                    }
                },
                {
                    'method': 'GET',
                    'path': '/api/v1/transactions/reference/<str:reference>/',
                    'name': 'Get Transaction by Reference',
                    'description': 'Get detailed information about a specific transaction by reference',
                    'authentication': 'Required - API Key',
                    'parameters': [
                        {'name': 'reference', 'type': 'string', 'required': True, 'description': 'Transaction reference'}
                    ],
                    'response_example': {
                        'success': True,
                        'data': {
                            'transaction': {
                                'id': 'uuid',
                                'reference': 'TXN-REF-123',
                                'amount': '100.00',
                                'currency': 'USD',
                                'status': 'completed',
                                'created_at': '2024-01-01T12:00:00Z'
                            }
                        }
                    }
                }
            ]
        }
    }
    
    # Authentication information
    auth_info = {
        'api_key_format': 'public_key:secret_key',
        'header_options': [
            'Authorization: Bearer {api_key}',
            'X-API-Key: {api_key}'
        ],
        'scopes': [
            {'name': 'read', 'description': 'Read access to transactions and data'},
            {'name': 'write', 'description': 'Write access to create payments and sessions'}
        ]
    }
    
    # Base URLs
    base_urls = {
        'production': 'https://app.pexipay.com',
        'development': 'http://localhost:8000'
    }
    
    context = {
        'api_endpoints': api_endpoints,
        'auth_info': auth_info,
        'base_urls': base_urls,
        'current_domain': request.get_host(),
        'is_development': settings.DEBUG
    }
    
    return render(request, 'public_api/api_docs.html', context)