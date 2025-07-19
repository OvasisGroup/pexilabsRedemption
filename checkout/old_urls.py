from django.urls import path, include
from . import views

app_name = 'checkout'

urlpatterns = [
    # Management views
    path('manage/', views.manage_checkout_pages, name='manage_pages'),
    
    # API endpoints
    path('api/currencies/', views.get_currencies, name='currencies'),
    path('api/checkout-pages/', views.CheckoutPageListCreateView.as_view(), name='checkout_pages'),
    path('api/checkout-pages/<uuid:pk>/', views.CheckoutPageDetailView.as_view(), name='checkout_page_detail'),
    path('api/checkout-pages/<uuid:checkout_page_id>/payment-methods/', views.PaymentMethodConfigListView.as_view(), name='payment_methods'),
    path('api/payment-methods/<uuid:pk>/', views.PaymentMethodConfigDetailView.as_view(), name='payment_method_detail'),
    
    # Session management
    path('api/sessions/', views.create_checkout_session, name='create_session'),
    path('api/sessions/<str:session_token>/', views.get_checkout_session, name='get_session'),
    path('api/process-payment/', views.process_payment, name='process_payment'),
    
    # Public endpoints
    path('api/pages/<slug:slug>/', views.get_checkout_page_info, name='checkout_page_info'),
    
    # Customer-facing pages
    path('<slug:slug>/', views.checkout_page_view, name='checkout_page'),
]
