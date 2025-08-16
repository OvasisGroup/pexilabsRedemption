from django.urls import path
from .views import checkout, authenticate, transactions, docs

app_name = 'public_api'

urlpatterns = [
    # Authentication endpoints
    path('auth/verify/', authenticate.auth_verify, name='auth_verify'),
    
    # Checkout endpoints
    path('checkout/make-payment/', checkout.make_payment, name='make_payment'),
    path('checkout/process-payment/', checkout.process_payment, name='process_payment'),
    
    # Transaction endpoints
    path('transactions/', transactions.list_transactions, name='list_transactions'),
    path('transactions/stats/', transactions.get_transaction_stats, name='transaction_stats'),
    path('transactions/choices/', transactions.get_transaction_choices, name='transaction_choices'),
    path('transactions/<uuid:transaction_id>/', transactions.get_transaction_by_id, name='get_transaction_by_id'),
    path('transactions/reference/<str:reference>/', transactions.get_transaction_by_reference, name='get_transaction_by_reference'),
    
    # Documentation endpoint
    path('docs/', docs.api_documentation, name='api_documentation'),
]