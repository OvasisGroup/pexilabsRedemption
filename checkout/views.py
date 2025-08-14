from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.urls import reverse
import json
import uuid
from decimal import Decimal
from urllib.parse import quote
from datetime import  timedelta
from .models import CheckoutPage, PaymentMethodConfig, CheckoutSession
from authentication.api_auth import APIKeyAuthentication
from authentication.models import AppKey, Merchant, PreferredCurrency
from transactions.models import Transaction, TransactionStatus, TransactionType, PaymentMethod, PaymentGateway
from integrations.uba_usage import UBAUsageService
from integrations.models import Integration, IntegrationStatus, IntegrationType
from integrations.transvoucher.service import TransVoucherService, TransVoucherAPIException
from integrations.transvoucher.usage import TransVoucherUsageService
import logging
from pexilabs import settings
from integrations.uniwire.client import UniwireClient, UniwireAPIException
from integrations.uniwire.utils import format_amount, is_supported_cryptocurrency, get_network_for_token, validate_address
from integrations.uniwire.constants import COIN_BTC, COIN_ETH, TOKEN_ETH_USDT


logger = logging.getLogger('checkout')

def manage_checkout_pages(request):
    """Merchant interface for managing checkout pages"""
    if not request.user.is_authenticated:
        return redirect('login')
    
    # Check if user has merchant account
    if not hasattr(request.user, 'merchant_account'):
        return JsonResponse({'error': 'No merchant account found'}, status=403)
    
    checkout_pages = CheckoutPage.objects.filter(
        merchant=request.user.merchant_account
    ).order_by('-created_at')
    
    context = {
        'checkout_pages': checkout_pages,
        'merchant': request.user.merchant_account
    }
    
    return render(request, 'checkout/manage_checkout_pages.html', context)


def get_currencies(request):
    """Get available currencies for checkout pages"""
    currencies = [
        {'code': 'USD', 'name': 'US Dollar', 'symbol': '$'},
        {'code': 'EUR', 'name': 'Euro', 'symbol': '€'},
        {'code': 'GBP', 'name': 'British Pound', 'symbol': '£'},
        {'code': 'JPY', 'name': 'Japanese Yen', 'symbol': '¥'},
        {'code': 'CAD', 'name': 'Canadian Dollar', 'symbol': 'C$'},
        {'code': 'AUD', 'name': 'Australian Dollar', 'symbol': 'A$'},
        {'code': 'CHF', 'name': 'Swiss Franc', 'symbol': 'CHF'},
        {'code': 'CNY', 'name': 'Chinese Yuan', 'symbol': '¥'},
        {'code': 'SEK', 'name': 'Swedish Krona', 'symbol': 'kr'},
        {'code': 'NZD', 'name': 'New Zealand Dollar', 'symbol': 'NZ$'},
    ]
    
    return JsonResponse({
        'currencies': currencies,
        'default': 'USD'
    })


def checkout_page_view(request, slug):
    """Render the customer-facing checkout page"""
    try:
        checkout_page = get_object_or_404(CheckoutPage, slug=slug, is_active=True)
        
        # Get enabled payment methods for this checkout page
        payment_methods = PaymentMethodConfig.objects.filter(
            checkout_page=checkout_page,
            is_enabled=True
        ).order_by('display_order')
        
        # Create a checkout session if needed
        session_id = request.GET.get('session_id')
        if not session_id:
            session = CheckoutSession.objects.create(
                checkout_page=checkout_page,
                session_id=str(uuid.uuid4()),
                amount=checkout_page.amount,
                currency=checkout_page.currency,
                expires_at=timezone.now() + timezone.timedelta(hours=24)
            )
            session_id = session.session_id
        else:
            session = get_object_or_404(CheckoutSession, session_id=session_id)
        
        context = {
            'checkout_page': checkout_page,
            'session': session,
            'payment_methods': payment_methods,
            'session_id': session_id,
        }
        
        return render(request, 'checkout/checkout_page.html', context)
        
    except CheckoutPage.DoesNotExist:
        return render(request, 'checkout/page_not_found.html', status=404)


@login_required
@require_http_methods(["GET", "POST"])
def create_checkout_page(request):
    """Create a new checkout page"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            checkout_page = CheckoutPage.objects.create(
                merchant=request.user.merchant_account,
                name=data.get('name'),
                description=data.get('description', ''),
                amount=data.get('amount'),
                currency=data.get('currency', 'USD'),
                logo_url=data.get('logo_url', ''),
                primary_color=data.get('primary_color', '#007bff'),
                secondary_color=data.get('secondary_color', '#6c757d'),
                background_color=data.get('background_color', '#ffffff'),
                success_url=data.get('success_url', ''),
                cancel_url=data.get('cancel_url', ''),
                collect_customer_info=data.get('collect_customer_info', True),
                custom_css=data.get('custom_css', ''),
                is_active=data.get('is_active', True)
            )
            
            # Create payment method configurations
            payment_methods = data.get('payment_methods', [])
            for pm in payment_methods:
                PaymentMethodConfig.objects.create(
                    checkout_page=checkout_page,
                    payment_method=pm.get('payment_method'),
                    display_name=pm.get('display_name'),
                    icon_url=pm.get('icon_url', ''),
                    is_enabled=pm.get('is_enabled', True),
                    display_order=pm.get('display_order', 0),
                    config_data=pm.get('config_data', {})
                )
            
            return JsonResponse({
                'success': True,
                'checkout_page_id': str(checkout_page.id),
                'slug': checkout_page.slug,
                'message': 'Checkout page created successfully'
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    # GET request - show form
    return render(request, 'checkout/create_checkout_page.html')


@csrf_exempt
@require_http_methods(["POST"])
def make_payment_api(request):
    """
    API endpoint for merchants to initiate payments.
    Requires API key authentication.
    """
    try:
        # Authenticate using API key
        auth = APIKeyAuthentication()
        auth_result = auth.authenticate(request)
        
        if not auth_result:
            return JsonResponse({
                'error': 'Authentication required',
                'message': 'Please provide a valid API key in Authorization header or X-API-Key header'
            }, status=401)
        
        user, app_key = auth_result
        
        # Validate API key has required permissions
        if not app_key.has_scope('write'):
            return JsonResponse({
                'error': 'Insufficient permissions',
                'message': 'API key requires write scope for payment operations'
            }, status=403)
        
        # Parse request data
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({
                'error': 'Invalid JSON',
                'message': 'Request body must be valid JSON'
            }, status=400)

        # Validate payment method
        payment_method = data.get('payment_method', 'card') # default "card"
        metadata  = data.get('metadata', {}) # to  get more data from the users
        customer_commission_percentage = 0.5 # 0.5%  By default
        multiple_use  = False 
        reference_id = data.get("reference_id",  f'PEX-REF-{uuid.uuid4().hex[:8].upper()}')
        if payment_method not in ['card', 'crypto']: # supports only crupto or card
            return JsonResponse({
                'error': 'Invalid payment method',
                'message': 'Payment method must be either "uba" or "transvoucher"'
            }, status=400)
        # Validate required fields
        required_fields = ['amount', 'currency', 'customer_email', 'customer_name', 'customer_phone', 'description']
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            return JsonResponse({
                'error': 'Missing required fields',
                'message': f'The following fields are required: {", ".join(missing_fields)}'
            }, status=400)
        
        # Validate amount
        try:
            amount = Decimal(str(data['amount']))
            if amount <= 0:
                raise ValueError("Amount must be positive")
        except (ValueError, TypeError):
            return JsonResponse({
                'error': 'Invalid amount',
                'message': 'Amount must be a positive number'
            }, status=400)
        
        # Create payment session
        payment_session = {
            'session_id': str(uuid.uuid4()),
            'amount': float(amount),
            'currency': data['currency'],
            'customer_email': data['customer_email'],
            'description': data['description'],
            'customer_name': data.get('customer_name', ''),
            'customer_phone': data.get('customer_phone', ''),
            'reference_id': reference_id,
            'metadata': metadata,
            'callback_url': data.get('callback_url', ''),
            'cancel_url': data.get('cancel_url', ''),
            'title': data.get('title', ''),
            'payment_method': payment_method,
            'customer_commission_percentage': customer_commission_percentage,
            'multiple_use': multiple_use,
            'merchant_id': str(app_key.partner.id),
            'merchant':  app_key.partner,
            'api_key_id': str(app_key.id),
            'created_at': timezone.now().isoformat()
        }
        
        # Store session data (you might want to use a proper session store or database)
        # For now, we'll pass it as query parameters to the processing page


        print("Payment Session:", payment_session)
        
        # Generate processing URL with session data
        process_url = request.build_absolute_uri(reverse('checkout:process_payment_page'))
        process_url += f"?session_id={payment_session['session_id']}"
        process_url += f"&amount={payment_session['amount']}"
        process_url += f"&currency={payment_session['currency']}"
        process_url += f"&customer_email={quote(payment_session['customer_email'])}"
        process_url += f"&customer_name={quote(payment_session['customer_name'])}"
        process_url += f"&customer_phone={quote(payment_session['customer_phone'])}"
        process_url += f"&metadata={quote(json.dumps(payment_session['metadata']))}"
        process_url += f"&payment_method={quote(payment_session['payment_method'])}"
        process_url += f"&customer_commission_percentage={quote(str(payment_session['customer_commission_percentage']))}"
        process_url += f"&reference_id={quote(str(payment_session['reference_id']))}"
        process_url += f"&created_at={quote(str(payment_session['created_at']))}"
        # Convert merchant object to serializable format
        merchant_data = {
            'id': str(payment_session['merchant'].id),
            'name': str(payment_session['merchant'].name),
            'code': str(payment_session['merchant'].code)
        }
        process_url += f"&merchant_id={quote(str(payment_session['merchant_id']))}"
        process_url += f"&merchant={quote(json.dumps(merchant_data))}"
        process_url += f"&title={quote(str(payment_session['title']))}"
        process_url += f"&multiple_use={quote(str(payment_session['multiple_use']))}"
        process_url += f"&description={quote(str(payment_session['description']))}"
        process_url += f"&callback_url={quote(str(payment_session['callback_url']))}"
        process_url += f"&cancel_url={quote(str(payment_session['cancel_url']))}"
        
        # Log API usage
        app_key.record_usage()
        # Create transaction record in database
        transaction =  None
        try:
            # Get merchant from API key partner
            # The partner code follows format: merchant_{merchant_id}
            partner_code = app_key.partner.code
            print(f"DEBUG: Processing partner code: {partner_code}")
            
            if partner_code.startswith('merchant_'):
                merchant_id = partner_code.replace('merchant_', '')
                print(f"DEBUG: Extracted merchant_id: {merchant_id}")
                try:
                    merchant = Merchant.objects.get(id=merchant_id)
                    print(f"DEBUG: Found merchant: {merchant} (ID: {merchant.id})")
                except Merchant.DoesNotExist:
                    print(f"ERROR: Merchant not found for partner code: {partner_code}")
                    return JsonResponse({
                        'error': 'Merchant account not found',
                        'message': f'No merchant found for partner {partner_code}'
                    }, status=400)
            else:
                print(f"ERROR: Invalid partner code format: {partner_code}")
                return JsonResponse({
                    'error': 'Invalid partner configuration',
                    'message': f'Partner code {partner_code} does not follow expected format'
                }, status=400)
            
            # Get or create PaymentGateway for API transactions
            print(f"DEBUG: Getting or creating PaymentGateway...")
            try:
                gateway = PaymentGateway.objects.get(code='api_gateway')
                print(f"DEBUG: Found existing PaymentGateway: {gateway}")
            except PaymentGateway.DoesNotExist:
                print(f"DEBUG: PaymentGateway not found, creating new one...")
                gateway, created = PaymentGateway.objects.get_or_create(
                    code='api_gateway',
                    defaults={
                        'name': 'API Payment Gateway',
                        'description': 'Default gateway for API-based transactions',
                        'api_endpoint': 'https://api.pexilabs.com',
                        'supported_payment_methods': 'card,bank_transfer,mobile_money,crypto',
                        'supported_currencies': 'USD,EUR,GBP,KES',
                        'is_sandbox': True
                    }
                )
                print(f"DEBUG: PaymentGateway created: {gateway}, created={created}")
            
            # Get or create currency object
            print(f"DEBUG: Getting or creating currency for: {data['currency']}")
            currency_obj, created = PreferredCurrency.objects.get_or_create(
                code=data['currency'],
                defaults={
                    'name': data['currency'],
                    'symbol': '$' if data['currency'] == 'USD' else data['currency'],
                    'is_active': True
                }
            )
            print(f"DEBUG: Currency object: {currency_obj}, created={created}")
            
            # Create transaction with pending status
            print(f"DEBUG: Creating transaction with:")
            print(f"  - title: {data.get('title', '')}")
            print(f"  - reference: {payment_session['session_id']}")
            print(f"  - merchant: {merchant} (ID: {merchant.id})")
            print(f"  - gateway: {gateway} (ID: {gateway.id})")
            print(f"  - currency: {currency_obj} (ID: {currency_obj.id})")
            print(f"  - customer_name: {data.get('customer_name', '')}")
            print(f"  - customer_phone: {data.get('customer_phone', '')}")
            print(f"  - payment_method: {payment_method}")
            print(f"  - customer_commission_percentage: {customer_commission_percentage}")
            print(f"  - multiple_use: {multiple_use}")
            print(f"  - description: {data.get('description', '')}")
            print(f"  - amount: {amount}")


            payment_method_type  = PaymentMethod.CARD
            if payment_method  == 'card':
                payment_method_type  = PaymentMethod.CARD
            elif payment_method == 'crypto':
                payment_method_type  = PaymentMethod.CRYPTO
            elif payment_method == 'mobile_money':
                payment_method_type  = PaymentMethod.MOBILE_MONEY
            elif payment_method == 'bank_transfer':
                payment_method_type  = PaymentMethod.BANK_TRANSFER
            
            transaction = Transaction.objects.create(
                reference=payment_session['session_id'],  # Use session_id as unique reference
                merchant=merchant,
                customer_email=data['customer_email'],
                transaction_type=TransactionType.PAYMENT,
                status=TransactionStatus.PENDING,
                payment_method=payment_method_type,  # Default to card, can be updated later
                gateway=gateway,
                currency=currency_obj,
                amount=Decimal(str(amount)),
                net_amount=Decimal(str(amount)),  # Will be updated when fees are calculated
                description=data['description'],
                metadata={
                    'amount': payment_session['amount'],
                    'api_key_id': str(app_key.id),
                    'partner_code': app_key.partner.code,
                    'merchant_id': str(merchant.id),
                    'customer_name': data.get('customer_name', ''),
                    'customer_phone': data.get('customer_phone', ''),
                    'reference_id': payment_session['reference_id'],
                    'session_id': payment_session['session_id'],
                    'payment_method': payment_session['payment_method'],
                    'customer_commission_percentage': payment_session['customer_commission_percentage'],
                    'multiple_use': payment_session['multiple_use'],
                    'title': payment_session['title'],
                    'callback_url': data.get('callback_url', ''),
                    'cancel_url': data.get('cancel_url', ''),
                    'session_id': payment_session['session_id'],
                    'created_via': 'api'
                },
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            
            print(f"DEBUG: Transaction created successfully with ID: {transaction.id}")
            
            # Update payment session with transaction ID
            payment_session['transaction_id'] = str(transaction.id)
            
        except Exception as e:
            # Log the error but don't fail the payment session creation
            print(f"Error creating transaction record: {str(e)}")
            # Continue with the payment session creation 
            return JsonResponse({
                'error': 'Error creating transaction record',
                'message': str(e)
            }, status=500)
        
        return JsonResponse({
            'success': True,
            'transaction_id': str(transaction.id),
            'reference_id': payment_session['reference_id'],
            'expires_at':  (timezone.now() + timedelta(minutes=5)).isoformat() , # plus 5 minutes
            'amount': amount,
            'currency': data['currency'],
            'payment_url': process_url,
            'status':'pending',
            'payment_method': payment_method_type,
            'message': 'Payment session created successfully'
        }, status=201)
        
    except Exception as e:
        return JsonResponse({
            'error': 'Internal server error',
            'message': str(e)
        }, status=500)


def process_payment_page(request):
    """
    Payment processing page that shows the payment form.
    """
    # Get session data from query parameters
    session_id = request.GET.get('session_id')
    amount = request.GET.get('amount')
    currency = request.GET.get('currency')
    customer_email = request.GET.get('customer_email')
    description = request.GET.get('description')
    payment_method = request.GET.get('payment_method', 'card')
    customer_name = request.GET.get('customer_name', '')
    merchant_id = request.GET.get('merchant_id', '')
    merchant  =  request.GET.get("merchant", {})
    metadata  = request.GET.get('metadata', {})
    customer_phone = request.GET.get('customer_phone', '')
    reference_id = request.GET.get('reference_id', '')
    multiple_use = request.GET.get('multiple_use', False)
    customer_commission_percentage = request.GET.get('customer_commission_percentage', 0)
    title = request.GET.get('title', '')
    created_at = request.GET.get('created_at', '')
    callback_url = request.GET.get('callback_url', '')
    cancel_url = request.GET.get('cancel_url', '')
    
    if not all([
        session_id, 
        amount, 
        currency, 
        customer_email, 
        customer_name, 
        customer_phone, 
        reference_id, 
        created_at, 
        description, 
        multiple_use, 
        customer_commission_percentage, 
        callback_url, 
        cancel_url, 
        payment_method]):
        return render(request, 'checkout/payment_error.html', {
            'error': 'Invalid payment session',
            'message': 'Missing required payment information'
        })
    
    try:
        amount = float(amount)
    except (ValueError, TypeError):
        return render(request, 'checkout/payment_error.html', {
            'error': 'Invalid amount',
            'message': 'Payment amount is not valid'
        })
    merchant_data = json.loads(merchant)

    context = {
        'session_id': session_id,
        'amount': amount,
        "merchant": merchant_data,
        'currency': currency,
        'customer_email': customer_email,
        'description': description,
        'payment_method': payment_method,
        'customer_name': customer_name,
        'metadata': json.loads(metadata),
        'customer_phone': customer_phone,
        'reference_id': reference_id,
        'multiple_use': multiple_use,
        'customer_commission_percentage': customer_commission_percentage,
        'title': title,
        'callback_url': callback_url,
        'cancel_url': cancel_url,
        'created_at': created_at,
    }


    print(context)

    # Extract merchant ID from the code field (format: merchant_{merchant_id})
    merchant_code = merchant_data["code"]
    if merchant_code.startswith('merchant_'):
        actual_merchant_id = merchant_code.replace('merchant_', '')
        context["metadata"]["api_key_id"] =  str(actual_merchant_id)
        merchant_partner = Merchant.objects.get(id=actual_merchant_id)
    else:
        # Fallback to using the id field if code doesn't follow expected format
        merchant_partner = Merchant.objects.get(id=merchant_data["id"])

    payment_methods = []
    payment_methods.append({
        'payment_method': 'uba',
        'display_name': 'United Bank for Africa',
        'icon_url': "https://uba.com/images/logo.svg",
        'display_order': 1
    })
    payment_methods.append({
        'payment_method': 'transvoucher',
        'display_name': 'Trans Voucher',
        'icon_url': "",
        'display_order': 2
    })
    payment_methods.append({
        'payment_method': 'uniwire',
        'display_name': 'Uniwire',
        'icon_url': "https://uniwire.com/images/logo.svg",
        'display_order': 3
    })
    payment_methods.sort(key=lambda x: x['display_order'])
    # 'uba',
    allowed_methods  = {
        'card': {'transvoucher': {'name': 'Trans Voucher', 'icon_url': "https://transvoucher.com/images/logo.svg"}},
        'crypto': {'uniwire': {'name': 'Uniwire', 'icon_url': "https://uniwire.com/images/logo.svg"}},
    }
    context['payment_methods'] = payment_methods

    if allowed_methods['card']:
        context['payment_methods'] = [pm for pm in context['payment_methods'] if pm['payment_method'] in allowed_methods['card'].keys()]            
    if allowed_methods['crypto']:
        context['payment_methods'] = [pm for pm in context['payment_methods'] if pm['payment_method'] in allowed_methods['crypto'].keys()]
    
    # Check if the selected payment method is transvoucher and render different view
    if payment_method == 'card' or (context['payment_methods'] and any(pm['payment_method'] == 'transvoucher' for pm in context['payment_methods'])):
        try:
            transvoucher_service = TransVoucherUsageService(merchant=merchant_partner)
            payment_data = {
                'amount': context['amount'],
                'currency': context.get('currency', 'USD'),
                'title': "PEXI - Process Payment",
                'description': context.get('description', ''),
                'customer_email': context['customer_email'],
                'customer_name': context['customer_name'],
                'customer_phone': context['customer_phone'],
                'reference_id': context['reference_id'],
                'metadata': context.get('metadata', {}),
                'customer_commission_percentage': context['customer_commission_percentage'],
                'multiple_use': context['multiple_use'] if isinstance(context['multiple_use'], bool) else context['multiple_use'] == "True"
            }
            result = transvoucher_service.create_checkout_session(**payment_data)
            if result.get('success'):
                context['result'] = result
                print("Result: ", result)
                return render(request, 'checkout/card_payment.html', context)

            else:
                return render(request, 'checkout/payment_error.html', {
                    'error': 'Payment creation error',
                    'message': 'Payment creation failed'
                })
        except TransVoucherAPIException as e:
            logger.error(f"TransVoucher API error: {e.message}")
            return render(request, 'checkout/payment_error.html', {
                    'error': 'Payment creation error',
                    'message': e.message
            })
        except Exception as e:
            logger.error(f"Unexpected error in TransVoucher payment creation: {str(e)}")
            return render(request, 'checkout/payment_error.html', {
                    'error': 'Internal server error',
                    'message': "Internal server error"
            })

    if payment_method == 'crypto':
        try:
            logger.info("Initializing Uniwire client with credentials from environment variables")
            client = UniwireClient(
                api_key=settings.UNIWIRE_API_KEY,
                api_secret=settings.UNIWIRE_API_SECRET,
                api_url=settings.UNIWIRE_API_URL
            )
            logger.info("Making API call for network invoice creation")
            print(f"Client configured with:")
            print(f"  API Key: {client.api_key}")
            print(f"  API Key: {client.api_secret}")
            print(f"  API URL: {client.api_url}")
            print(f"  Sandbox Mode: {client.sandbox_mode}")
            logger.info(f"Client configured with API URL: {client.api_url}, Sandbox Mode: {client.sandbox_mode}")
            passthrough_data = {
                'amount': context['amount'],
                'currency': context.get('currency', 'USD'),
                'title': "PEXI - Process Payment",
                'description': context.get('description', ''),
                'customer_email': context['customer_email'],
                'customer_name': context['customer_name'],
                'customer_phone': context['customer_phone'],
                'reference_id': context['reference_id'],
                'metadata': context.get('metadata', {}),
                'customer_commission_percentage': context['customer_commission_percentage'],
                'multiple_use': context['multiple_use'] if isinstance(context['multiple_use'], bool) else context['multiple_use'] == "True",
                'callback_url': callback_url,
                'cancel_url': cancel_url,
                'created_at': created_at,
            }
            response = client.create_invoice(
                profile_id=settings.UNIWIRE_PROFILE_ID,
                kind=COIN_ETH,  # Using ETH as the network coin
                passthrough=json.dumps(passthrough_data),
                notes="The resuable wallet",
            )         
            if response.get('result'):
                result  =  {
                    "reference": response.get('result').get('id'),
                    "invoice_number": response.get('result').get('id').replace("-", "").upper(),
                    "payment_url": f"https://uniwire.com/invoice/" + response.get('result').get('id').replace("-", "").upper(),
                    "amount": context["amount"],
                    "currency": context["currency"],
                }
                context['result'] = result
                print(result)
                return render(request, 'checkout/card_payment.html', context)
            else:
                logger.error("Network invoice creation failed")
                return render(request, 'checkout/payment_error.html', {
                    'error': 'Payment Processing Error',
                    'message': 'Payment Processing Error'
                })
        except UniwireAPIException as e:
            logger.error(f"Uniwire API error: {e.message}")
            return render(request, 'checkout/payment_error.html', {
                    'error': 'Payment Processing Error',
                    'message': e.message
            })
        except Exception as e:
            logger.error(f"Unexpected error in Uniwire payment creation: {str(e)}")                
    # UBA
    return render(request, 'checkout/process_payment.html', context)


def get_checkout_page_info(request, slug):
    """Get checkout page information for API"""
    try:
        checkout_page = get_object_or_404(CheckoutPage, slug=slug, is_active=True)
        
        # Get payment methods
        payment_methods = PaymentMethodConfig.objects.filter(
            checkout_page=checkout_page,
            is_enabled=True
        ).order_by('display_order')
        
        payment_methods_data = [
            {
                'payment_method': pm.payment_method,
                'display_name': pm.display_name,
                'icon_url': pm.icon_url,
                'display_order': pm.display_order
            }
            for pm in payment_methods
        ]
        
        return JsonResponse({
            'id': str(checkout_page.id),
            'name': checkout_page.name,
            'description': checkout_page.description,
            'amount': str(checkout_page.amount),
            'currency': checkout_page.currency,
            'logo_url': checkout_page.logo_url,
            'primary_color': checkout_page.primary_color,
            'secondary_color': checkout_page.secondary_color,
            'background_color': checkout_page.background_color,
            'collect_customer_info': checkout_page.collect_customer_info,
            'payment_methods': payment_methods_data
        })
        
    except CheckoutPage.DoesNotExist:
        return JsonResponse({'error': 'Checkout page not found'}, status=404)


def get_checkout_session(request, session_token):
    """Get checkout session details"""
    try:
        session = get_object_or_404(CheckoutSession, session_id=session_token)
        
        return JsonResponse({
            'session_id': session.session_id,
            'checkout_page': {
                'name': session.checkout_page.name,
                'slug': session.checkout_page.slug
            },
            'amount': str(session.amount),
            'currency': session.currency,
            'status': session.status,
            'customer_email': session.customer_email,
            'expires_at': session.expires_at.isoformat(),
            'created_at': session.created_at.isoformat()
        })
        
    except CheckoutSession.DoesNotExist:
        return JsonResponse({'error': 'Session not found'}, status=404)


@login_required
def create_checkout_session(request):
    """Create a checkout session for a customer"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        checkout_page_id = data.get('checkout_page_id')
        
        if not checkout_page_id:
            return JsonResponse({'error': 'Checkout page ID is required'}, status=400)
            
        checkout_page = get_object_or_404(CheckoutPage, id=checkout_page_id)
        
        # Verify the merchant owns this checkout page
        if hasattr(request.user, 'merchant_account') and checkout_page.merchant != request.user.merchant_account:
            return JsonResponse({'error': 'Permission denied'}, status=403)
        
        # Create the checkout session
        session = CheckoutSession.objects.create(
            checkout_page=checkout_page,
            session_id=str(uuid.uuid4()),
            amount=data.get('amount', checkout_page.amount),
            currency=data.get('currency', checkout_page.currency),
            customer_email=data.get('customer_email'),
            customer_data=data.get('customer_data', {}),
            expires_at=timezone.now() + timezone.timedelta(hours=24)
        )
        
        return JsonResponse({
            'session_id': session.session_id,
            'checkout_url': f'/checkout/{checkout_page.slug}/?session_id={session.session_id}',
            'expires_at': session.expires_at.isoformat()
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
def process_payment(request):
    """Process payment for a checkout session"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        session_id = data.get('session_id')
        
        if not session_id:
            return JsonResponse({'error': 'Session ID is required'}, status=400)
            
        session = get_object_or_404(CheckoutSession, session_id=session_id)
        
        # Check if session has expired
        if session.expires_at < timezone.now():
            return JsonResponse({'error': 'Checkout session has expired'}, status=400)
        
        # Check if session is already completed
        if session.status == 'completed':
            return JsonResponse({'error': 'Payment has already been processed'}, status=400)
        
        # Simulate payment processing
        session.status = 'completed'
        session.payment_method_used = data.get('payment_method', 'card')
        session.payment_data = {
            'transaction_id': str(uuid.uuid4()),
            'payment_method': data.get('payment_method', 'card'),
            'processed_at': timezone.now().isoformat(),
        }
        session.save()
        
        return JsonResponse({
            'success': True,
            'transaction_id': session.payment_data['transaction_id'],
            'message': 'Payment processed successfully'
        })
        
    except CheckoutSession.DoesNotExist:
        return JsonResponse({'error': 'Invalid session ID'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
