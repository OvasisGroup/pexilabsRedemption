from django.urls import path
from . import views

app_name = 'checkout'

urlpatterns = [
    # Management views
    path('manage/', views.manage_checkout_pages, name='manage_pages'),
    path('create/', views.create_checkout_page, name='create_page'),
    
    # API endpoints
    path('api/currencies/', views.get_currencies, name='currencies'),
    path('api/sessions/', views.create_checkout_session, name='create_session'),
    path('api/sessions/<str:session_token>/', views.get_checkout_session, name='get_session'),
    # path('api/process-payment/', views.process_payment, name='process_payment'),  # Commented out - function doesn't exist
    
    # New API endpoint for merchant payments
    path('make-payment/', views.make_payment_api, name='make_payment_api'),
    path('process-payment/', views.process_payment_page, name='process_payment_page'),
    
    # Public endpoints
    path('api/pages/<slug:slug>/', views.get_checkout_page_info, name='checkout_page_info'),
    
    # Customer-facing pages
    path('<slug:slug>/', views.checkout_page_view, name='checkout_page'),
]
