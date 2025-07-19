#!/usr/bin/env python
"""
Simple registration test
"""
import os
import django
import sys

sys.path.append('/Users/asd/Desktop/desktop/pexilabs')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pexilabs.settings')
django.setup()

from django.test import Client
from django.urls import reverse
from authentication.models import CustomUser, Country, PreferredCurrency, MerchantCategory

print("Testing registration...")

# Get first available options
country = Country.objects.first()
currency = PreferredCurrency.objects.first() 
category = MerchantCategory.objects.first()

# Clean test email
test_email = "simple_test@example.com"
CustomUser.objects.filter(email=test_email).delete()

# Test data
data = {
    'first_name': 'Simple',
    'last_name': 'Test',
    'email': test_email,
    'password': 'simpletest123',
    'confirm_password': 'simpletest123',
    'country': str(country.id),
    'currency': str(currency.id),
}

# Submit registration
client = Client()
response = client.post('/auth/register/', data)

# Check result
if CustomUser.objects.filter(email=test_email).exists():
    print("SUCCESS: Registration working!")
    user = CustomUser.objects.get(email=test_email)
    print(f"User: {user}")
else:
    print("FAILED: Registration not working")
    print(f"Response status: {response.status_code}")
