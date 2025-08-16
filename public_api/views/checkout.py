from django.http import JsonResponse
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.urls import reverse
import json
import uuid
from decimal import Decimal
from urllib.parse import quote
from datetime import  timedelta
from authentication.api_auth import APIKeyAuthentication
from authentication.models import Merchant, PreferredCurrency
from transactions.models import Transaction, TransactionStatus, TransactionType, PaymentMethod, PaymentGateway
from integrations.transvoucher.service import TransVoucherAPIException
from integrations.transvoucher.usage import TransVoucherUsageService
import logging
from ..utils import api_key_required
from pexilabs import settings
from integrations.uniwire.client import UniwireClient, UniwireAPIException
from integrations.uniwire.utils import format_amount, is_supported_cryptocurrency, get_network_for_token, validate_address
from integrations.uniwire.constants import COIN_BTC, COIN_ETH, TOKEN_ETH_USDT


logger = logging.getLogger(__name__)
@api_key_required
@require_http_methods(["POST"])
def make_payment(request):
    """
    API endpoint for merchants to initiate payment sessions.
    
    This endpoint allows authenticated merchants to create payment sessions that can be used
    to process payments through various payment methods (card, crypto). The endpoint validates
    the request, creates a payment session, generates a transaction record, and returns a
    payment URL for the customer to complete the payment.
    
    **Authentication:**
    - Requires valid API key with 'write' scope
    - API key can be provided via 'Authorization' header or 'X-API-Key' header
    - Supports both full format (pk_merchant_xxx:secret) and simplified format (public_key:secret)
    
    **HTTP Method:** POST
    **Content-Type:** application/json
    
    **Request Body Parameters:**
    - amount (required): Payment amount as a positive number
    - currency (required): Currency code (e.g., 'USD', 'EUR', 'KES')
    - customer_email (required): Customer's email address
    - customer_name (required): Customer's full name
    - customer_phone (required): Customer's phone number
    - description (required): Payment description
    - payment_method (optional): Payment method ('card' or 'crypto', defaults to 'card')
    - reference_id (optional): Custom reference ID (auto-generated if not provided)
    - metadata (optional): Additional metadata as JSON object
    - callback_url (optional): URL to redirect after successful payment
    - cancel_url (optional): URL to redirect after cancelled payment
    - title (optional): Payment title/subject
    
    **Response Format:**
    Success (201):
    {
        "success": true,
        "transaction_id": "uuid",
        "reference_id": "PEX-REF-XXXXXXXX",
        "expires_at": "2024-01-01T12:00:00Z",
        "amount": 100.00,
        "currency": "USD",
        "payment_url": "https://app.pexpay.com/api/v1/checkout/process-payment?session_id=...",
        "status": "pending",
        "payment_method": "card",
        "message": "Payment session created successfully"
    }
    
    **Error Responses:**
    - 401: Authentication required or invalid API key
    - 403: Insufficient permissions (API key lacks 'write' scope)
    - 400: Invalid request data (missing fields, invalid amount, unsupported payment method)
    - 500: Internal server error
    
    **Payment Methods:**
    - 'card': Credit/debit card payments via TransVoucher integration
    - 'crypto': Cryptocurrency payments via Uniwire integration
    
    **Transaction Creation:**
    - Creates a Transaction record with PENDING status
    - Associates transaction with merchant from API key
    - Records customer information and payment metadata
    - Generates unique session ID for payment tracking
    
    **Session Management:**
    - Payment sessions expire after 5 minutes
    - Session data is passed via URL parameters to payment processing page
    - Includes merchant information, customer details, and payment configuration
    
    **Security Features:**
    - API key scope validation
    - Input sanitization and validation
    - Merchant association verification
    - IP address and user agent logging
    
    **Usage Example:**
    ```bash
    curl -X POST https://app.pexpay.com/api/v1/checkout/make-payment/ \
      -H "Content-Type: application/json" \
      -H "X-API-Key: your_public_key:your_secret" \
      -d '{
        "amount": 100.00,
        "currency": "USD",
        "customer_email": "customer@example.com",
        "customer_name": "John Doe",
        "customer_phone": "+1234567890",
        "description": "Product purchase",
        "payment_method": "card",
        "callback_url": "https://merchant.com/success",
        "cancel_url": "https://merchant.com/cancel"
      }'
    ```
    
    **Dependencies:**
    - authentication.api_auth.APIKeyAuthentication
    - authentication.models.Merchant, PreferredCurrency
    - transactions.models.Transaction, TransactionStatus, etc.
    - Django's timezone, JsonResponse, reverse
    
    **Related Views:**
    - process_payment_page: Handles the actual payment processing
    - Payment gateway integrations (TransVoucher, Uniwire)
    
    **Logging:**
    - Records API key usage
    - Logs transaction creation details
    - Debug information for merchant and gateway resolution
    - Error logging for transaction creation failures
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


def process_payment(request):
    """
    API endpoint for processing payments.
    
    This view function handles the processing of payments for different payment methods
    including card payments (TransVoucher), cryptocurrency payments (Uniwire), and UBA
    bank transfers. It processes session data from query parameters, validates the
    payment information, and renders the appropriate payment interface based on the
    selected payment method.
    
    **URL Pattern:**
        GET /checkout/process-payment/
    
    **Query Parameters:**
        session_id (str): Unique identifier for the payment session
        amount (str): Payment amount (will be converted to float)
        currency (str): Currency code (e.g., 'USD', 'NGN')
        customer_email (str): Customer's email address
        customer_name (str): Customer's full name
        customer_phone (str): Customer's phone number
        description (str): Payment description or purpose
        payment_method (str, optional): Payment method ('card', 'crypto'). Defaults to 'card'
        merchant_id (str): Merchant identifier
        merchant (str): JSON string containing merchant data
        metadata (str, optional): JSON string with additional metadata. Defaults to '{}'
        reference_id (str): Unique reference identifier for the transaction
        multiple_use (str): Whether the payment link can be used multiple times
        customer_commission_percentage (str): Commission percentage for customer
        title (str): Payment title or heading
        created_at (str): Timestamp when the payment session was created
        callback_url (str): URL to redirect after successful payment
        cancel_url (str): URL to redirect after payment cancellation
    
    **Payment Method Integrations:**
    
    1. **Card Payments (TransVoucher):**
       - Creates a checkout session using TransVoucherUsageService
       - Renders 'checkout/card_payment.html' template
       - Handles TransVoucherAPIException for API errors
    
    2. **Cryptocurrency Payments (Uniwire):**
       - Initializes UniwireClient with API credentials
       - Creates an invoice for ETH network payments
       - Generates payment URL and invoice details
       - Renders 'checkout/card_payment.html' template
       - Handles UniwireAPIException for API errors
    
    3. **Default/UBA Payments:**
       - Renders 'checkout/process_payment.html' template
       - Used as fallback for other payment methods
    
    **Template Context Variables:**
        session_id (str): Payment session identifier
        amount (float): Validated payment amount
        merchant (dict): Merchant information (parsed from JSON)
        currency (str): Payment currency
        customer_email (str): Customer email
        customer_name (str): Customer name
        customer_phone (str): Customer phone
        description (str): Payment description
        payment_method (str): Selected payment method
        metadata (dict): Additional metadata (parsed from JSON)
        reference_id (str): Transaction reference
        multiple_use (bool): Multiple use flag
        customer_commission_percentage (float): Commission percentage
        title (str): Payment title
        callback_url (str): Success redirect URL
        cancel_url (str): Cancel redirect URL
        created_at (str): Creation timestamp
        payment_methods (list): Available payment methods with display info
        result (dict): Payment processing result (for successful integrations)
    
    **Returns:**
        HttpResponse: Rendered template response
        
        **Success Cases:**
        - 'checkout/card_payment.html': For card and crypto payments with valid results
        - 'checkout/process_payment.html': For UBA and default payment methods
        
        **Error Cases:**
        - 'checkout/payment_error.html': For validation errors, missing parameters,
          invalid amounts, or payment integration failures
    
    **Error Handling:**
        - Validates all required query parameters
        - Converts and validates amount as float
        - Handles JSON parsing errors for merchant and metadata
        - Catches and logs TransVoucherAPIException
        - Catches and logs UniwireAPIException
        - Provides user-friendly error messages
    
    **Logging:**
        - Logs TransVoucher API errors
        - Logs Uniwire API errors and client configuration
        - Logs unexpected errors during payment creation
    
    **Security Considerations:**
        - No authentication required (public payment page)
        - Validates merchant existence before processing
        - Sanitizes and validates all input parameters
        - Uses secure API clients for payment integrations
    
    **Example Usage:**
        ```
        # URL with required parameters
        /checkout/process-payment/?session_id=abc123&amount=100.00&currency=USD
        &customer_email=user@example.com&customer_name=John+Doe
        &customer_phone=+1234567890&description=Test+Payment
        &merchant_id=merchant_123&merchant={"code":"merchant_123"}
        &reference_id=ref_123&multiple_use=false
        &customer_commission_percentage=0&title=Payment
        &created_at=2024-01-01T00:00:00Z
        &callback_url=https://example.com/success
        &cancel_url=https://example.com/cancel
        ```
    
    **Dependencies:**
        - TransVoucherUsageService: For card payment processing
        - UniwireClient: For cryptocurrency payment processing
        - Merchant model: For merchant validation
        - Django templates: For rendering payment forms
    
    **Related Views:**
        - make_payment_api: API endpoint for creating payments
        - Payment success/cancel handlers (callback_url/cancel_url)
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
    # Handle the usage for the UBA PayDock payment
    return render(request, 'checkout/process_payment.html', context)
