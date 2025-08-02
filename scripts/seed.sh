#!/bin/bash

# Seed all reference data
python manage.py create_countries
python manage.py create_currencies
python manage.py create_merchant_categories
python manage.py setup_role_groups

# Create demo data for testing
python manage.py demo_merchant_signals --create-test-user
python create_demo_transactions.py