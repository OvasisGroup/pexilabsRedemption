from django.urls import path
from . import landing_views

app_name = 'landing'

urlpatterns = [
    # Landing pages
    path('', landing_views.landing_page, name='home'),
    path('features/', landing_views.features_page, name='features'),
    path('pricing/', landing_views.pricing_page, name='pricing'),
    path('contact/', landing_views.contact_page, name='contact'),
    
    # AJAX endpoints
    path('contact/submit/', landing_views.contact_form_submit, name='contact_submit'),
]
